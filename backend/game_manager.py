from multiprocessing import Process, Queue, Manager
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sock import Sock, Server
from gamestate import GameState
import json
import requests
import threading


app = Flask(__name__)
CORS(app)
#manager = Manager()
#active_games = manager.dict()

sock = Sock(app)
connections = {}
games : dict[str, GameState] = {}
game_locks : dict[str, threading.Lock] = {} 
games_lock = threading.Lock()

@sock.route('/ws/<game_id>/<player_name>')
def websocket(ws : Server, game_id: str, player_name: str):

    if game_id not in games:
        ws.send(json.dumps({"type": "ERROR", "message": "Game does not exist."}))
        return

    # Get or create lock for this game
    if game_id not in game_locks:
        with games_lock:
            if game_id not in game_locks:
                game_locks[game_id] = threading.Lock()

    game_lock = game_locks[game_id]

    # Thread-safe player connection handling
    with game_lock:
        # If player is already connected, close the old connection and replace it
        if player_name in games[game_id].players:
            print(f"Player {player_name} rejoining game {game_id}")

        games[game_id].players[player_name] = ws
        print("Player: ", player_name, " joined game ", game_id)

    broadcast(game_id, {"type": "CHAT", "player": "Server", "message": f"{player_name} has joined."})

    try:
        while True:
            message = ws.receive()

            data = json.loads(message)

            if data["type"] == "CHAT":
                broadcast(game_id, {"type": "CHAT", "player": data["player"], "message": data["message"]})
    finally:
        # Thread-safe player disconnection handling
        with game_lock:
            game = games[game_id]
            if player_name in game.players:
                del game.players[player_name]
                print(f"Player {player_name} disconnected from game {game_id}")

        broadcast(game_id, {'type': 'CHAT', 'player': "Server", "message": f"{player_name} left."})


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
    #tmp
    new_game.ws = "LALALALA"

    return jsonify({"ws": new_game.ws}), 201

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
    app.run(debug=True, host="0.0.0.0", port=5001)