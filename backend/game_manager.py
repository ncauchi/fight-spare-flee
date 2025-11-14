import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, join_room, leave_room, emit, disconnect
from gamestate import GameState, Player
import threading
import requests

app = Flask(__name__)
CORS(app)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet'
)

ROOMS_API_URL = "http://localhost:5000"
SERVER_NAME = "SERVER123"

connections : dict[str, (str, str)] = {} # player_name, game_id
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

@socketio.event
def JOIN(game_id: str, player_name: str):
    sid = request.sid
    lock = game_locks[game_id]
    game = games[game_id]
    players_snapshot = []
    new_join = True
    with lock:
        if len(game.players) == game._max_players:
            disconnect()
            print(f'Player: "{player_name}" tried to join full game: "{game._name}"')
            return

        if player_name in game.players:
            old_sid = game.players[player_name]
            disconnect(sid = old_sid)
            del connections[old_sid]
            new_join = False
        
        connections[sid] = (player_name, game_id)
        game.players[player_name] = Player(name=player_name, sid=sid)
        players_snapshot = game.players

    if new_join:
        print("Player: ",player_name, " joined game: ", game_id)
        emit('CHAT', {'player': SERVER_NAME, 'text': f'{player_name} joined.'}, to=game_id, include_self=False)
        emit('PLAYERS', {'players': [{"name": player.name, "ready": player.lobby_ready} for player in players_snapshot.values()]}, to=game_id, include_self=False)
        eventlet.spawn(notify_new_join, sid, game_id)
        eventlet.spawn(update_lobby_service, game_id)
    else:
        print("Player: ",player_name, " rejoined game: ", game_id)
    
    join_room(game_id)

@socketio.event
def LOBBY_READY(ready: bool):
    sid = request.sid
    with connections_lock:
        player_name, game_id = connections[sid]
    
    lock = game_locks[game_id]
    with lock:
        player = games[game_id].players[player_name]
        player.lobby_ready = ready
        players_snapshot = games[game_id].players
    
    emit('PLAYERS', {'players': [{"name": player.name, "ready": player.lobby_ready} for player in players_snapshot.values()]}, to=game_id)

@socketio.event
def START_GAME():
    sid = request.sid
    with connections_lock:
        player_name, game_id = connections[sid]

    with game_locks[game_id]:
        game_snapshot = games[game_id]
    
    if game_snapshot._owner != player_name:
        print(f'Player {player_name} tried to start game: {game_snapshot._name} but they are not the owner.')
        emit('CHAT', {'player': SERVER_NAME, 'text': f'{player_name} tried to hack.'}, to=game_id, include_self=False)
        return
    
    if not all([player.lobby_ready for player in game_snapshot.players.values()]):
        print(f'Game: {game_snapshot._name} but not all players are ready.')
        emit('CHAT', {'player': SERVER_NAME, 'text': f'Not all players are ready'}, broadcast=False)
        return
    
    print(f'Game: {game_snapshot._name} starting.')
    emit('CHAT', {'player': SERVER_NAME, 'text': f'Starting game...'}, to=game_id)
    eventlet.spawn(start_game(game_id))
    

@socketio.event
def CHAT(player: str, text: str):
    _, room = connections[request.sid]
    emit('CHAT', {'player': player, 'text': text}, to=room)

def notify_new_join(sid, game_id):
    eventlet.sleep(0.2)
    with game_locks[game_id]:
        game = games[game_id]
        data = {
            "game_name": game._name,
            "game_owner": game._owner,
            "max_players": game._max_players,
            "players": [{"name": player.name, "ready": player.lobby_ready} for player in game.players.values()],
            "messages": [{"player": SERVER_NAME, "text": "Welcome to the game"}],
        }
    socketio.emit("INIT", data, to=sid)
    

def cleanup_disconnect(sid):
    player_leave = False
    player_name, game_id = "LOCK_WARNING", "LOCK_WARNING"
    players_snapshot = []
    
    with connections_lock:
        sid = request.sid
        if sid in connections:
            player_name, game_id = connections[sid]
            del connections[sid]
            player_leave = True
            if game_id in games:
                with game_locks[game_id]:
                    game = games[game_id]
                    if player_name in game.players:
                        del game.players[player_name]
                    players_snapshot = game.players

    if player_leave:
        update_lobby_service(game_id)
        socketio.emit('CHAT', {'player': SERVER_NAME, 'text': f'{player_name} left.'}, to=game_id)
        socketio.emit('PLAYERS', {'players': [player_name for player_name in players_snapshot.keys()]}, to=game_id)
        print("Player: ",player_name, " left game: ", game_id)


def start_game(game_id):
    with game_locks[game_id]:
        game = games[game_id]
        game.start()
    eventlet.sleep(0.1)
    socketio.emit("START_GAME", to=game_id)

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

def update_lobby_service(id):

    if id not in game_locks or id not in games:
        raise ValueError("Tried to send update to lobby for game that does not exist")

    lock = game_locks[id]

    with lock:
        status = games[id].to_status()
        name = games[id]._name
    response = requests.put(
            f"{ROOMS_API_URL}/games/{id}",
            json=status,
            headers={"Content-Type": "application/json"},
        )
    if response.status_code != 200:
        print(f"Failed to update game {name}: {response.status_code}")
    #else:
        #print(f"Updated game: {name}")

if __name__ == "__main__":
    #socketio.start_background_task(poll_lobby_service)
    socketio.run(app, debug=True, host="0.0.0.0", port=5001, use_reloader=False)