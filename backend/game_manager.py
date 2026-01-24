import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, join_room, leave_room, emit, disconnect
from gamestate import GameState
from game_events import EventType, EventBus, Event
import threading
import requests
from test import get_local_ip
from api_wrapper import *
import warnings
from app_logging import AppLogger

app = Flask(__name__)
CORS(app)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet'
)

fsf_api = Fsf_api(socketio)

logger = AppLogger(name='game_server', color='blue')

ROOMS_API_URL = "http://127.0.0.1:5000"
SERVER_NAME = "SERVER123"

connections : dict[str, tuple[str, str]] = {} # player_name, game_id
games : dict[str, GameState] = {}
game_locks : dict[str, threading.Lock] = {}
games_lock = threading.Lock()
connections_lock = threading.Lock()

@socketio.on('connect')
def test_connect(auth):
    logger.info("client connected")

@socketio.on('disconnect')
def test_disconnect():
    sid = request.sid
    cleanup_disconnect(sid)
    logger.info("client disconnected")

@fsf_api.event_handler(JoinRequest)
def JOIN(request_data: JoinRequest, sid):
    player_name, game_id = request_data.player_name, request_data.game_id

    if game_id not in games:
        disconnect()
        logger.error(f'player: "{player_name}" tried to game that does not exist', console=True)
        return

    lock = game_locks[game_id]
    players_snapshot = []
    new_join = True
    with lock:
        game = games[game_id]

        # full
        if len(game.players) == game._max_players:
            disconnect()
            logger.info(f'player: "{player_name}" tried to join full game', console=True)
            return

        # player already in game
        if player_name in game.players:
            old_sid = game.players[player_name]
            disconnect(sid = old_sid)
            with connections_lock:
                if old_sid in connections:
                    del connections[old_sid]
            new_join = False

        with connections_lock:
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


    join_room(game_id)
    if new_join:
        message = Message(player_name=SERVER_NAME, text=f'{player_name} joined.')
        fsf_api.emit_chat_event(game_id, message=message, include_self=False)
        fsf_api.emit_players_event(game_id, players_snapshot)
        eventlet.spawn(update_lobby_service, game_id)
        eventlet.sleep(0.2)
        fsf_api.emit_init_response(sid, **init_package)

        

@fsf_api.event_handler(LobbyReadyRequest)
def LOBBY_READY(request_data: LobbyReadyRequest, sid):
    player_name, game_id = player_from_sid(sid)

    ready = request_data.ready
    lock = game_locks[game_id]
    with lock:
        player = games[game_id].players[player_name]
        player.lobby_ready = ready
        players_snapshot = games[game_id].get_status_players() 
        logger.info(f'player "{player.name}" became {"ready" if ready else "unready"} in game "{games[game_id]._name}"', console=True)
    
    fsf_api.emit_players_event(game_id, players_snapshot)

@fsf_api.event_handler(StartGameRequest)
def START_GAME(data: StartGameRequest, sid):
    player_name, game_id = player_from_sid(sid)

    with game_locks[game_id]:
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
    eventlet.spawn(start_game, game_id)
    

@fsf_api.event_handler(ChatRequest)
def CHAT(data: ChatRequest, sid):
    player_name, game_id = player_from_sid(sid)
    fsf_api.emit_chat_event(game_id, Message(player_name=player_name, text=data.text))
    logger.info(f'player "{player_name}" sent a message "{data.text}"')

     
@fsf_api.event_handler(ActionRequest)
def ACTION(data: ActionRequest, sid):
    player_name, game_id = player_from_sid(sid)
    logger.info(f'recieved action request from game {player_name}')
    with game_locks[game_id]:
        game = games[game_id]
        game.player_action(player=player_name, action=data.choice)

@fsf_api.event_handler(CombatRequest)
def COMBAT(data: CombatRequest, sid):
    player_name, game_id = player_from_sid(sid)
    logger.info(f'recieved combat action from game {player_name}')
    with game_locks[game_id]:
        game = games[game_id]
        game.player_select_monster(player=player_name, choice=data.target, combat_action=data.combat)

@fsf_api.event_handler(ItemChoiceRequest)
def ITEM_CHOICE(data: ItemChoiceRequest, sid):
    player_name, game_id = player_from_sid(sid)
    logger.info(f'recieved item selection from game {player_name}')
    with game_locks[game_id]:
        game = games[game_id]
        game.player_select_item(player=player_name, choice=data.item)

@fsf_api.event_handler(PlayerChoiceRequest)
def PLAYER_CHOICE(data: PlayerChoiceRequest, sid):
    player_name, game_id = player_from_sid(sid)
    logger.info(f'recieved player selection from game {player_name}')
    with game_locks[game_id]:
        game = games[game_id]
        game.player_select_player(player=player_name, choice=data.player)
    

def cleanup_disconnect(sid):
    player_leave = False
    player_name, game_id = "LOCK_WARNING", "LOCK_WARNING"
    players_snapshot = []
    
    with connections_lock:
        if sid in connections:
            player_name, game_id = connections[sid]
            del connections[sid]
            player_leave = True
        else: 
            player_leave = False
    
    if player_leave and game_id in games:
        with game_locks[game_id]:
            game = games[game_id]
            if player_name in game.players:
                del game.players[player_name]
            players_snapshot = game.get_status_players()
            game_name = game._name

        eventlet.spawn(update_lobby_service, game_id)
        fsf_api.emit_chat_event(game_id, Message(player_name=SERVER_NAME, text=f'{player_name} left.'))
        fsf_api.emit_players_event(game_id, players_snapshot)
        logger.info(f'player "{player_name}" left game "{game_name}"')


def start_game(game_id):
    with game_locks[game_id]:
        game = games[game_id]
        game.start()
        first_player = game.get_active_player()
    eventlet.sleep(0.1)
    fsf_api.emit_start_game_event(game_id, first_player)

def update_game_players(game_id: str):
    with game_locks[game_id]:
        game = games[game_id]
        game_name = game._name
        player_snapshot = game.get_status_players()
    
    fsf_api.emit_players_event(game_id, players=player_snapshot)
    logger.info(f'updating players in game {game_name}')

def update_game_board(game_id: str):
    with game_locks[game_id]:
        game = games[game_id]
        game_name = game._name
        board_snapshot = game.get_status_fsf()
        deck_size = len(game.deck)
        shop_size = len(game.shop)
    
    fsf_api.emit_board_event(game_id, deck_size=deck_size, shop_size=shop_size, monsters=board_snapshot)
    logger.info(f'updating board in game {game_name}')

def update_game_player_hand(game_id: str, player: str):
    with game_locks[game_id]:
        game = games[game_id]
        game_name = game._name
        player_sid = game.players[player].sid
        hand_snapshot = game.players[player].get_status_hand()
    
    fsf_api.emit_hand_event(player_sid, hand_snapshot)
    logger.info(f'updating {player}\'s hand in game {game_name}')



@app.route("/internal/<game_id>", methods = ["POST"])
def create_game(game_id):

    data = request.get_json()

    if not data or "name" not in data or "owner" not in data or "max_players" not in data:
        return jsonify({"error": "no data"}), 400

    new_game = GameState(game_id, data["name"], data["owner"], data["max_players"])
    hand_change_events = [EventType.SHOP, EventType.FIGHT]
    board_change_events = [EventType.COMBAT, EventType.FLEE, EventType.FLIP, EventType.SPARE]
    player_change_events = [EventType.SHOP, EventType.FIGHT, EventType.FLEE, EventType.SPARE, EventType.TURN, EventType.COINS]
    update_hand_func = lambda e : update_game_player_hand(game_id, e.player)
    update_board_func = lambda e : update_game_board(game_id)
    update_players_func = lambda e : update_game_players(game_id)
    
    for e in hand_change_events:
        new_game._event_bus.subscribe(event_type=e, callback=update_hand_func)
    for e in board_change_events:
        print(f'binding {update_board_func.__name__}, {update_board_func} to {e}')
        new_game._event_bus.subscribe(event_type=e, callback=update_board_func)
    for e in player_change_events:
        print(f'binding {update_players_func.__name__}, {update_players_func} to {e}')
        new_game._event_bus.subscribe(event_type=e, callback=update_players_func)

    with games_lock:
        games[game_id] = new_game
        game_locks[game_id] = threading.Lock()

    logger.info(f'"{new_game._owner}" created game: "{new_game._name}" with id: "{new_game._id}"')
    return jsonify("response", "Sucess"), 201

def player_from_sid(sid: Any):
    with connections_lock:
        if sid not in connections:
            logger.warning("tried to decode invalid sid")
            return
        player_name, game_id = connections[sid]

    with games_lock:
        if game_id not in games:
            raise IndexError("Game associated with sid does not exist or was deleted")
        
    with game_locks[game_id]:
        if player_name not in games[game_id].players:
            raise IndexError("Player name associated with sid does not exist or was deleted")

    return player_name, game_id

def update_lobby_service(id):

    if id not in game_locks or id not in games:
        logger.error("tried to send update to lobby for game that does not exist", console=True)
        return

    lock = game_locks[id]

    with lock:
        status = games[id].get_status_lobby()
        name = games[id]._name
    response = requests.put(
            f"{ROOMS_API_URL}/games/{id}",
            json=status,
            headers={"Content-Type": "application/json"},
        )
    if response.status_code != 200:
        logger.error(f'failed to update game "{name}": {response.status_code}')
    else:
        logger.info(f'updated game "{name}" to {status}', console=True)


if __name__ == "__main__":
    #socketio.start_background_task(poll_lobby_service)
    print("Running at: ", get_local_ip())
    socketio.run(app, debug=True, host="0.0.0.0", port=5001, use_reloader=False)
    