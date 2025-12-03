from flask import Flask, request, jsonify
from flask_cors import CORS
from game_meta import GameMetadata
import requests


app = Flask(__name__)
CORS(app)
games_api_url = "http://localhost:5001"


# In-memory storage for games

games : dict[str, GameMetadata] = {}


@app.route("/games", methods=["GET"])
def get_games():
    #Get all games
    games_list = [game.to_dict() for game in games.values()]
    return jsonify(games_list), 200

        

@app.route("/games", methods=["POST"])
def create_lobby():
    #Create new game
    #TODO make process aswell
    data = request.get_json()

    if not data or "name" not in data or "owner" not in data:
        return jsonify({"error": "Missing required fields: name, owner"}), 400

    game = GameMetadata( name=data["name"], owner=data["owner"], max_players=data.get("max_players", 4) )
    
    response = requests.post(
        f'{games_api_url}/internal/{game.id}',
        json=game.to_setup(),
        headers={"Content-Type": "application/json"}
    )

    if response.status_code != 201:
        return jsonify({"error": "Could not create game"}), 500
    
    games[game.id] = game

    print(f'New game: "{game.id}"')

    return jsonify({"id": game.id}), 201


@app.route("/games/<game_id>", methods=["GET"])
def get_game(game_id):
    """Get details of a specific game"""
    game = games.get(game_id)

    if not game:
        return jsonify({"error": "game not found"}), 404

    return jsonify(game.to_dict()), 200

@app.route("/games/<game_id>", methods=["PUT"])
def update_game(game_id):
    """Update player count and status of game, only used internally"""
    game = games.get(game_id)

    if not game:
        return jsonify({"error": "game not found"}), 404
    
    data = request.get_json()
    if not data or "num_players" not in data or "status" not in data:
        return jsonify({"error": "missing required fields"})

    game.num_players = data["num_players"]
    game.status = data["status"]

    if game.status == "ended":
        print(f'Deleting game: "{games[game.id].name}"')
        del games[game.id]
    else:
        print(f'Updated game: "{games[game.id].name}"')

    return jsonify({"response": "ok"}), 200


"""@app.route("/games/<game_id>/join", methods=["POST"])
#TODO remove, move to WS, reimplement if auth needed
def join_game(game_id):
    game = games.get(game_id)

    if not game:
        return jsonify({"error": f"game {game_id} not found"}), 404

    data = request.get_json()
    if not data or "playerName" not in data:
        return jsonify({"error": "Missing required field: playerName"}), 400

    success, message = game.add_player(data["playerName"])

    if not success:
        return jsonify({"error": message}), 400

    return jsonify({"message": message, "game": game.to_dict()}), 200"""


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "games": len(games)}), 200


if __name__ == "__main__":
    dev_game = GameMetadata("dev_game", "God")
    dev_game.id = "development"
    response = requests.post(
        f'{games_api_url}/internal/{dev_game.id}',
        json=dev_game.to_setup(),
        headers={"Content-Type": "application/json"}
    )

    if response.status_code != 201:
        print(f"Could not connect to game service: {response.json()}")
    else:
        print("Added dev game to game service")

    games[dev_game.id] = dev_game

    app.run(debug=True,host="0.0.0.0", port=5000, use_reloader=False)


