from multiprocessing import Process, Queue, Manager
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, join_room, leave_room, emit, disconnect
from gamestate import GameState
import json
import threading


app = Flask(__name__)
CORS(app)
#manager = Manager()
#active_games = manager.dict()

socketio = SocketIO(app, cors_allowed_origins="*")

connections : dict[str, (str, str)]= {}
games : dict[str, GameState] = {}
game_locks : dict[str, threading.Lock] = {} 
games_lock = threading.Lock()

@socketio.on('connect')
def test_connect(auth):
    print("Client connected.")

@socketio.on('disconnect')
def test_disconnect():
    sid = request.sid
    if sid in connections:
        player_name, game_id = connections[sid]

        # Clean up connections
        del connections[sid]

        # Clean up game state if game exists
        if game_id in games and game_id in game_locks:
            with game_locks[game_id]:
                game = games[game_id]
                if player_name in game.players and game.players[player_name] == sid:
                    del game.players[player_name]
                    print(f"Player {player_name} disconnected from game {game_id}")

        # Leave the room
        leave_room(game_id)
    else:
        print(f"Client {sid} disconnected (not in a game)")

@socketio.event
def JOIN(game_id: str, player_name: str):
    sid = request.sid
    lock = game_locks[game_id]
    game = games[game_id]
    new_join = True
    with lock:
        if player_name in game.players:
            old_sid = game.players[player_name]
            #disconnect(sid = old_sid)
            del connections[old_sid]
            new_join = False
        
        connections[sid] = (player_name, game_id)
        game.players[player_name] = sid

    if new_join:
        print("Player: ",player_name, " joined game: ", game_id)
    else:
        print("Player: ",player_name, " rejoined game: ", game_id)
    
    join_room(game_id)
    

@socketio.event
def CHAT(player: str, text: str):
    _, room = connections[request.sid]
    print(player, text)
    emit('CHAT', {'player': player, 'text': text}, to=room)


@app.route("/internal", methods = ["POST"])
def create_process():
    data = request.get_json()

    if not data or "id" not in data or "name" not in data or "owner" not in data or "max_players" not in data:
        return jsonify({"error": "no data"}), 400

    game_id = data["id"]
    new_game = GameState(game_id, data["name"], data["owner"], data["max_players"])

    # Thread-safe game creation
    with games_lock:
        games[game_id] = new_game
        game_locks[game_id] = threading.Lock()

    print("Created new game with id: ", new_game._id)

    return jsonify("response", "Sucess"), 201

def broadcast(game_id : str, data : dict):
    if not game_id or game_id not in games:
        print("Tried to broadcast to invalid room")
        return

    game = games[game_id]
    game_lock = game_locks.get(game_id)

    if not game_lock:
        print(f"No lock found for game {game_id}")
        return

    with game_lock:
        players_snapshot = list(game.players.items())

    for player_name, ws in players_snapshot:
        ws.send(json.dumps(data))



if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5001, allow_unsafe_werkzeug=True)