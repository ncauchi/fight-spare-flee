import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, join_room, leave_room, emit, disconnect
from gamestate import GameState, Player, EventType
import threading
import requests
from test import get_local_ip
from api_wrapper import *
import warnings

app = Flask(__name__)
CORS(app)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet'
)

fsf_api = Fsf_api(socketio)

ROOMS_API_URL = "http://127.0.0.1:5000"
SERVER_NAME = "SERVER123"

connections : dict[str, tuple[str, str]] = {} # player_name, game_id
games : dict[str, GameState] = {}
game_locks : dict[str, threading.Lock] = {}
games_lock = threading.Lock()
connections_lock = threading.Lock()

@socketio.on('connect')
def test_connect(auth):
    print("Client connected.")

@socketio.on('disconnect')
def test_disconnect():
    sid = request.sid
    cleanup_disconnect(sid)
    print("Client disconnected.")

@fsf_api.event_handler(JoinRequest)
def JOIN(request_data: JoinRequest, sid):
    player_name, game_id = request_data.player_name, request_data.game_id

    if game_id not in games:
        disconnect()
        print(f'Player: "{player_name}" tried to game that does not exist')
        return

    lock = game_locks[game_id]
    players_snapshot = []
    new_join = True
    with lock:
        game = games[game_id]

        # full
        if len(game.players) == game._max_players:
            disconnect()
            print(f'Player: "{player_name}" tried to join full game: "{game._name}"')
            return

        # player already in game
        if player_name in game.players:
            old_sid = game.players[player_name]
            disconnect(sid = old_sid)
            with connections_lock:
                if old_sid in connections:
                    del connections[old_sid]
            new_join = False

        print("Player: ",player_name, " joined game: ", game_id)
        with connections_lock:
            connections[sid] = (player_name, game_id)
        game.players[player_name] = Player(name=player_name, sid=sid)
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

    join_room(game_id)
    if new_join:
        message = Message(player_name=SERVER_NAME, text=f'{player_name} joined.')
        fsf_api.emit_chat_event(game_id, message=message, include_self=False)
        fsf_api.emit_players_event(game_id, players_snapshot)
        eventlet.spawn(update_lobby_service, game_id)
        eventlet.sleep(0.2)
        fsf_api.emit_init_response(sid, **init_package)

    else:
        print("Player: ",player_name, " rejoined game: ", game_id)

@fsf_api.event_handler(LobbyReadyRequest)
def LOBBY_READY(request_data: LobbyReadyRequest, sid):
    player_name, game_id = player_from_sid(sid)

    ready = request_data.ready
    lock = game_locks[game_id]
    with lock:
        player = games[game_id].players[player_name]
        player.lobby_ready = ready
        players_snapshot = games[game_id].get_status_players() 
        print(f'Player "{player.name}" became {"ready" if ready else "unready"} in game "{games[game_id]._name}"')
    
    fsf_api.emit_players_event(game_id, players_snapshot)

@fsf_api.event_handler(StartGameRequest)
def START_GAME(data: StartGameRequest, sid):
    player_name, game_id = player_from_sid(sid)

    with game_locks[game_id]:
        game_snapshot = games[game_id]
    
        if game_snapshot._owner != player_name:
            print(f'Player {player_name} tried to start game: {game_snapshot._name} but they are not the owner.')
            fsf_api.emit_chat_event(game_id, Message(player_name=SERVER_NAME, text=f'{player_name} tried to hack.'),include_self=False) 
            return

        if not all([player.lobby_ready for player in game_snapshot.players.values()]):
            print(f'Game: "{game_snapshot._name}" tried to start but not all players are ready.')
            fsf_api.emit_chat_event(game_id, Message(player_name=SERVER_NAME, text=f'Not all players are ready'),include_self=False) 
            return
    
    print(f'Game: {game_snapshot._name} starting.')
    fsf_api.emit_chat_event(game_id, Message(player_name=SERVER_NAME, text=f'Starting game...'),include_self=False) 
    eventlet.spawn(start_game, game_id)


@fsf_api.event_handler(EndTurnRequest)
def END_TURN(data: EndTurnRequest, sid):
    player_name, game_id = player_from_sid(sid)

    with game_locks[game_id]:
        game = games[game_id]
        game.advance_active_player()
        new_active_name = game.get_active_player()
    
    fsf_api.emit_turn_event(game_id, new_active_name, phase=TurnPhase.CHOOSING_ACTION)
    

@fsf_api.event_handler(ChatRequest)
def CHAT(data: ChatRequest, sid):
    player_name, game_id = player_from_sid(sid)
    fsf_api.emit_chat_event(game_id, Message(player_name=player_name, text=data.text))

@fsf_api.event_handler(ActionRequest)
def ACTION(data: ActionRequest, sid):
    player_name, game_id = player_from_sid(sid)
    choice = data.choice
    res = []
    players_change = False
    board_change = False
    with game_locks[game_id]:
        game = games[game_id]
        if player_name != game.get_active_player():
            print(f"Player {player_name} tried to go out of turn")
            return
        
        if choice not in [member.name for member in EventType]:
            print(f"Player {player_name} tried to do invalid action {choice}")
            return

        action = EventType[choice]

        if game.turn_phase != TurnPhase.CHOOSING_ACTION and not (game.turn_phase == TurnPhase.SHOPPING and action == EventType.SHOP):
            print(f"Player {player_name} tried to do action in wrong order")
            return

        if action == EventType.COINS:
            gain = game.take_coins()
            res.append(lambda: fsf_api.emit_action_response(sid, PlayerActionChoice.COINS, gain, []))
            players_change = True
            
        elif action == EventType.SHOP:
            item_gain = game.shop_items()
            res.append(lambda: fsf_api.emit_action_response(sid, PlayerActionChoice.SHOP, -2, []))
            res.append(lambda: fsf_api.emit_hand_event(sid, item_gain))
            players_change = True

        elif action == EventType.FSF:
            monsters = game.fsf()
            board_change = True


        else:
            print(f"Player {player_name} tried to do action {choice} which is invalid")
            return
        
        players_snapshot = game.get_status_players()
        board_snapshot = game.get_status_board()

        
    for r in res:
        r()

    if players_change:
        emit('PLAYERS', players_snapshot, to=game_id)

    if board_change:
        emit('BOARD', board_snapshot )

     
@fsf_api.event_handler(ActionRequest)
def ACTION(data: ActionRequest, sid):
    player_name, game_id = player_from_sid(sid)
    choice = data.choice
    with game_locks[game_id]:
        game = games[game_id]
        if player_name != game.get_active_player():
            warnings.warn(f'Player "{player_name}" tried to take an action out of turn.')
            return
        match choice:
            case PlayerActionChoice.COINS:
                game.active_player_take_coins()
            case PlayerActionChoice.SHOP:
                game.active_player_buy_item()
            case PlayerActionChoice.FSF:
                game.active_player_fsf()
            case PlayerActionChoice.END:
                game.advance_active_player()
            case PlayerActionChoice.COMBAT:
                if not data.combat:
                    print("Tried to do invalid combat action")
                match data.combat:
                    case PlayerCombatChoice.SELECT:
                        game.fsf_select(data.target)
                    case PlayerCombatChoice.FIGHT:
                        game.fsf_fight(data.target, data.item)
                    case PlayerCombatChoice.SPARE:
                        game.fsf_spare(data.target)
                    case PlayerCombatChoice.FLEE:
                        game.fsf_flee(data.target)

        # Capture state before releasing lock
        players_snapshot = game.get_status_players()
        board_snapshot = game.get_status_board()
        hand_snapshot = game.get_active_player_obj().get_status_hand()
        active_player = game.get_active_player()
        turn_phase = game.turn_phase

    # Emit events outside the lock
    fsf_api.emit_players_event(game_id, players=players_snapshot)
    fsf_api.emit_board_event(game_id, **board_snapshot)
    fsf_api.emit_hand_event(sid, items=hand_snapshot)
    fsf_api.emit_turn_event(game_id, active=active_player, phase=turn_phase)
                


    

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

        eventlet.spawn(update_lobby_service, game_id)
        fsf_api.emit_chat_event(game_id, Message(player_name=SERVER_NAME, text=f'{player_name} left.'))
        fsf_api.emit_players_event(game_id, players_snapshot)
        print("Player: ",player_name, " left game: ", game_id)


def start_game(game_id):
    with game_locks[game_id]:
        game = games[game_id]
        game.start()
        first_player = game.get_active_player()
    eventlet.sleep(0.1)
    fsf_api.emit_start_game_event(game_id, first_player)

@app.route("/internal/<game_id>", methods = ["POST"])
def create_game(game_id):

    data = request.get_json()

    if not data or "name" not in data or "owner" not in data or "max_players" not in data:
        return jsonify({"error": "no data"}), 400

    new_game = GameState(game_id, data["name"], data["owner"], data["max_players"])

    with games_lock:
        games[game_id] = new_game
        game_locks[game_id] = threading.Lock()

    print(f'"{new_game._owner}" created game: "{new_game._name}" with id: "{new_game._id}"')
    return jsonify("response", "Sucess"), 201

def player_from_sid(sid: Any):
    with connections_lock:
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
        raise ValueError("Tried to send update to lobby for game that does not exist")

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
        print(f"Failed to update game {name}: {response.status_code}")
    else:
        print(f'Updated game "{name}" to {status}.')


if __name__ == "__main__":
    #socketio.start_background_task(poll_lobby_service)
    print("Running at: ", get_local_ip())
    socketio.run(app, debug=True, host="0.0.0.0", port=5001, use_reloader=False)
    