import os
import asyncio
import socketio
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from gamestate import GameState, Item, Monster
from game_events import *
from test import get_local_ip
from api_wrapper import *
from app_logging import AppLogger
from db_utils import init_db, teardown_db
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print("Database initialized")
    yield
    await teardown_db()
    print("Database connections closed")


sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
fast_app = FastAPI(lifespan=lifespan)
app = socketio.ASGIApp(sio, other_asgi_app=fast_app)

fsf_api = FsfApi(sio)

logger = AppLogger(name='game_server', color='blue')

ROOMS_API_URL = os.environ.get("LOBBY_API_URL", "http://localhost:5000")
SERVER_NAME = "SERVER123"

connections : dict[str, tuple[str, str]] = {} # player_name, game_id
games : dict[str, GameState] = {}
game_locks : dict[str, asyncio.Lock] = {}
games_lock = asyncio.Lock()
connections_lock = asyncio.Lock()

class GameSnapshot:
    """Captures a snapshot of game state for differential comparison"""
    def __init__(self, game: GameState):
        self.players = {name: player.get_status_public() for name, player in game.players.items()}
        self.turn = game.get_active_player()
        self.turn_phase = game.turn_phase
        self.board = game.get_status_board()
        self.player_hands = {name: player.get_status_hand() for name, player in game.players.items()}
        self.player_selected_items = {name: game.get_selected_fight_items(name).copy() for name in game.players.keys()}

def differential_update(game_id: str, before: GameSnapshot, after: GameSnapshot):
    """
    Compares before and after snapshots and emits only the necessary updates
    """
    changed_players = False

    for player_name in after.players:
        if not changed_players and player_name not in before.players or before.players[player_name] != after.players[player_name]:
            changed_players = True

    for player_name in before.players:
        if not changed_players and player_name not in after.players:
            changed_players = True

    if changed_players:
        asyncio.create_task(update_game_players(game_id))
    if before.turn != after.turn or before.turn_phase != after.turn_phase:
        asyncio.create_task(update_game_turn(game_id))
    if before.board != after.board:
        asyncio.create_task(update_game_board(game_id))
    for player_name in after.player_hands:
        if (player_name not in before.player_hands) or (before.player_hands[player_name] != after.player_hands[player_name]) or (before.player_selected_items[player_name] != after.player_selected_items[player_name]):
            asyncio.create_task(update_game_player_hand(game_id, player_name))

def with_differential_update(handler_func):
    """
    Decorator that wraps action handlers to perform differential updates
    Usage: @with_differential_update on any handler function

    Apply BEFORE @fsf_api.event_handler decorator:
        @with_differential_update
        @fsf_api.event_handler(SomeRequest)
        def HANDLER(data, sid):
            ...
    """
    async def wrapper(data, sid):
        _, game_id = await player_from_sid(sid)

        async with game_locks[game_id]:
            before = GameSnapshot(games[game_id])

        result = await handler_func(data, sid)

        async with game_locks[game_id]:
            after = GameSnapshot(games[game_id])

        differential_update(game_id, before, after)
        return result

    # Preserve function name for event_handler decorator
    wrapper.__name__ = handler_func.__name__
    return wrapper

@sio.on('connect')
async def test_connect(sid, environ):
    logger.info("client connected")

@sio.on('disconnect')
async def test_disconnect(sid):
    await cleanup_disconnect(sid)
    logger.info("client disconnected")

@fsf_api.event_handler(JoinRequest)
async def JOIN(request_data: JoinRequest, sid):
    player_name, game_id = request_data.player_name, request_data.game_id

    if game_id not in games:
        await sio.disconnect(sid)
        logger.error(f'player: "{player_name}" tried to game that does not exist', console=True)
        return

    lock = game_locks[game_id]
    players_snapshot = []
    new_join = True
    async with lock:
        game = games[game_id]

        # full
        if len(game.players) == game._max_players:
            await sio.disconnect(sid)
            logger.info(f'player: "{player_name}" tried to join full game', console=True)
            return

        # player already in game
        if player_name in game.players:
            old_sid = game.players[player_name]
            await sio.disconnect(old_sid)
            async with connections_lock:
                if old_sid in connections:
                    del connections[old_sid]
            new_join = False

        async with connections_lock:
            connections[sid] = (player_name, game_id)
        game.add_player(player_name=player_name, sid=sid)
        players_snapshot = game.get_status_players()

        init_package = {
            "game_name": game._name,
            "game_owner": game._owner,
            "max_players": game._max_players,
            "players": players_snapshot,
            "messages": [Message(player_name = SERVER_NAME, text= "Welcome to the game")],
            "status": game.status.name,
            "active_player": game.get_active_player(),
        }

        if new_join:
            logger.info(f'player: "{player_name}" joined game "{game._name}"', console=True)
        else:
            logger.info(f'player: "{player_name}" rejoined game "{game._name}"', console=True)


    await sio.enter_room(sid, game_id)
    if new_join:
        message = Message(player_name=SERVER_NAME, text=f'{player_name} joined.')
        fsf_api.emit_chat_event(game_id, message=message, include_self=False)
        fsf_api.emit_players_event(game_id, players_snapshot)
        asyncio.create_task(update_lobby_service(game_id))
        fsf_api.emit_init_response(sid, **init_package)

        

@fsf_api.event_handler(LobbyReadyRequest)
async def LOBBY_READY(request_data: LobbyReadyRequest, sid):
    player_name, game_id = await player_from_sid(sid)

    ready = request_data.ready
    lock = game_locks[game_id]
    async with lock:
        player = games[game_id].players[player_name]
        player.lobby_ready = ready
        players_snapshot = games[game_id].get_status_players() 
        logger.info(f'player "{player.name}" became {"ready" if ready else "unready"} in game "{games[game_id]._name}"', console=True)
    
    fsf_api.emit_players_event(game_id, players_snapshot)

@fsf_api.event_handler(StartGameRequest)
async def START_GAME(data: StartGameRequest, sid):
    player_name, game_id = await player_from_sid(sid)

    async with game_locks[game_id]:
        game_snapshot = games[game_id]
    
        if game_snapshot._owner != player_name:
            logger.error(f'player {player_name} tried to start game: {game_snapshot._name} but they are not the owner.', console=True)
            fsf_api.emit_chat_event(game_id, Message(player_name=SERVER_NAME, text=f'{player_name} tried to hack.'),include_self=False) 
            return

        if not all([player.lobby_ready for player in game_snapshot.players.values()]):
            logger.info(f'player {player_name} tried to start game: {game_snapshot._name} but not all players are ready.', console=True)
            fsf_api.emit_chat_event(game_id, Message(player_name=SERVER_NAME, text=f'Not all players are ready'),include_self=False) 
            return
    
    logger.info(f'game "{game_snapshot._name}" starting')
    fsf_api.emit_chat_event(game_id, Message(player_name=SERVER_NAME, text=f'Starting game...'),include_self=False)
    asyncio.create_task(start_game(game_id))
    

@fsf_api.event_handler(ChatRequest)
async def CHAT(data: ChatRequest, sid):
    player_name, game_id = await player_from_sid(sid)
    fsf_api.emit_chat_event(game_id, Message(player_name=player_name, text=data.text))
    logger.info(f'player "{player_name}" sent a message "{data.text}"')

     

@fsf_api.event_handler(ActionRequest)
@with_differential_update
async def ACTION(data: ActionRequest, sid):
    player_name, game_id = await player_from_sid(sid)
    logger.info(f'recieved action request from game {player_name}')
    async with game_locks[game_id]:
        game = games[game_id]
        game.player_action(player=player_name, action=data.choice)


@fsf_api.event_handler(CombatRequest)
@with_differential_update
async def COMBAT(data: CombatRequest, sid):
    player_name, game_id = await player_from_sid(sid)
    logger.info(f'recieved combat action from game {player_name}: {data}')
    async with game_locks[game_id]:
        game = games[game_id]
        game.player_select_monster(player=player_name, choice=data.target, combat_action=data.combat)


@fsf_api.event_handler(ItemChoiceRequest)
@with_differential_update
async def ITEM_CHOICE(data: ItemChoiceRequest, sid):
    player_name, game_id = await player_from_sid(sid)
    logger.info(f'recieved item selection from game {player_name}: {data}')
    async with game_locks[game_id]:
        game = games[game_id]
        game.player_select_item(player=player_name, choice=data.item)


@fsf_api.event_handler(PlayerChoiceRequest)
@with_differential_update
async def PLAYER_CHOICE(data: PlayerChoiceRequest, sid):
    player_name, game_id = await player_from_sid(sid)
    logger.info(f'recieved player selection from game {player_name}')
    async with game_locks[game_id]:
        game = games[game_id]
        game.player_select_player(player=player_name, choice=data.player)
    

async def cleanup_disconnect(sid):
    player_leave = False
    player_name, game_id = "LOCK_WARNING", "LOCK_WARNING"
    players_snapshot = []
    
    async with connections_lock:
        if sid in connections:
            player_name, game_id = connections[sid]
            del connections[sid]
            player_leave = True
        else: 
            player_leave = False
    
    if player_leave and game_id in games:
        async with game_locks[game_id]:
            game = games[game_id]
            if player_name in game.players:
                game.remove_player(player_name)
            players_snapshot = game.get_status_players()
            game_name = game._name
        asyncio.create_task(update_lobby_service(game_id))
        fsf_api.emit_chat_event(game_id, Message(player_name=SERVER_NAME, text=f'{player_name} left.'))
        fsf_api.emit_players_event(game_id, players_snapshot)
        logger.info(f'player "{player_name}" left game "{game_name}"')


async def start_game(game_id):
    async with game_locks[game_id]:
        game = games[game_id]
        game.start()
        first_player = game.get_active_player()
    fsf_api.emit_start_game_event(game_id, first_player)

async def update_game_players(game_id: str):
    async with game_locks[game_id]:
        game = games[game_id]
        game_name = game._name
        player_snapshot = game.get_status_players()
    
    fsf_api.emit_players_event(game_id, players=player_snapshot)
    logger.info(f'updating players in game {game_name}, {player_snapshot}')

async def update_game_board(game_id: str):
    async with game_locks[game_id]:
        game = games[game_id]
        game_name = game._name
        board_snapshot = game.get_status_board()
    
    fsf_api.emit_board_event(game_id, **board_snapshot)
    logger.info(f'updating board in game {game_name}, {board_snapshot}')

async def update_game_player_hand(game_id: str, player: str):
    async with game_locks[game_id]:
        game = games[game_id]
        game_name = game._name
        player_sid = game.players[player].sid
        hand_snapshot = game.players[player].get_status_hand()
        selected_items = game.get_selected_fight_items(player)

    
    fsf_api.emit_hand_event(player_sid, hand_snapshot, selected_items)
    logger.info(f'updating {player}\'s hand in game {game_name}, {hand_snapshot}, {selected_items}')

async def update_game_turn(game_id: str):
    async with game_locks[game_id]:
        game = games[game_id]
        game_name = game._name
        active = game.get_active_player()
        phase = game.turn_phase
    
    fsf_api.emit_turn_event(game_id, active=active, phase=phase)
    logger.info(f'updating turn info in game {game_name}, {active} {phase}')

async def on_coins_event(event: CoinsEvent):
    logger.info("sending coins animation")
    game_id = event.game_id
    async with game_locks[game_id]:
        game = games[game_id]
        player_sid = game.players[event.player].sid
    anim = Animation(content=CoinAnimContent(), source="coins", destination="player")
    fsf_api.emit_anim_event(to=player_sid, animation=anim)

async def on_shop_event(event: ShopEvent):
    logger.info("sending item shop animation")
    game_id = event.game_id
    async with game_locks[game_id]:
        game = games[game_id]
        destination_id = event.item_uid
        player_sid = game.players[event.player_name].sid
    item_info = Item.info_from_id(event.item_id)
    anim = Animation(content=ItemAnimContent(item=item_info, style="draw"), source="shop", destination=HandLocation(id=destination_id))
    fsf_api.emit_anim_event(to=player_sid, animation=anim)

async def on_combat_event(event: CombatEvent):
    logger.info("sending combat start animation")
    game_id = event.game_id
    mon_infos = [m for m in event.info]
    for mon_info in mon_infos:
        anim = Animation(content=MonsterAnimContent(monster=mon_info, style="appear"), source="deck", destination=MonsterLocation(id=mon_info.id))
        fsf_api.emit_anim_event(to=game_id, animation=anim)


# REST Api Endpoints
class CreateGameRequest(BaseModel):
    name: str
    owner: str
    max_players: int

@fast_app.post("/internal/{game_id}", status_code=201)
async def create_game(game_id, data: CreateGameRequest):

    new_game = GameState(game_id, data.name, data.owner, data.max_players)

    new_game._event_bus.subscribe(event_type="shop", callback=on_shop_event)
    new_game._event_bus.subscribe(event_type="coins", callback=on_coins_event)
    new_game._event_bus.subscribe(event_type="combat", callback=on_combat_event)

    async with games_lock:
        games[game_id] = new_game
        game_locks[game_id] = asyncio.Lock()

    logger.info(f'"{new_game._owner}" created game: "{new_game._name}" with id: "{new_game._id}"')
    return {"response": "Success"}

async def player_from_sid(sid: Any):
    async with connections_lock:
        if sid not in connections:
            logger.warning("tried to decode invalid sid")
            return
        player_name, game_id = connections[sid]

    async with games_lock:
        if game_id not in games:
            raise IndexError("Game associated with sid does not exist or was deleted")
        
    async with game_locks[game_id]:
        if player_name not in games[game_id].players:
            raise IndexError("Player name associated with sid does not exist or was deleted")

    return player_name, game_id

async def update_lobby_service(id):

    if id not in game_locks or id not in games:
        logger.error("tried to send update to lobby for game that does not exist", console=True)
        return

    async with game_locks[id]:
        status = games[id].get_status_lobby()
        name = games[id]._name

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{ROOMS_API_URL}/games/{id}",
            json=status,
        )

    if response.status_code != 200:
        logger.error(f'failed to update game "{name}": {response.status_code}')
    else:
        logger.info(f'updated game "{name}" to {status}', console=True)


if __name__ == "__main__":
    #socketio.start_background_task(poll_lobby_service)
    print("Running at: ", get_local_ip())
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
    