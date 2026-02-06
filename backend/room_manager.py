import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from game_meta import GameMetadata
import requests
import api_wrapper as api
from app_logging import AppLogger


app = Flask(__name__)
CORS(app)
games_api_url = os.environ.get("GAMES_API_URL", "http://localhost:5001")


# In-memory storage for games

games : dict[str, GameMetadata] = {}

logger = AppLogger(name='lobby_server', color='cyan')


@app.route("/games", methods=["GET"])
def get_games():
    #Get all games
    logger.info("Client requested all games", console=True)
    games_list = [game.to_dict() for game in games.values()]
    return jsonify(games_list), 200

        

@app.route("/games", methods=["POST"])
def create_lobby():
    #Create new game
    #TODO make process aswell
    data = request.get_json()

    if not data or "name" not in data or "owner" not in data:
        logger.error("Client tried to create game with invalid request body", console=True)
        return jsonify({"error": "Missing required fields: name, owner"}), 400

    game = GameMetadata( name=data["name"], owner=data["owner"], max_players=data.get("max_players", 4) )
    
    response = requests.post(
        f'{games_api_url}/internal/{game.id}',
        json=game.to_setup(),
        headers={"Content-Type": "application/json"}
    )

    if response.status_code != 201:
        logger.error("Failed to connect to game server", console=True)
        return jsonify({"error": "Could not create game"}), 500
    
    games[game.id] = game

    logger.info(f'New game: "{game.id}"', console=True)

    return jsonify({"id": game.id}), 201


@app.route("/games/<game_id>", methods=["GET"])
def get_game(game_id):
    """Get details of a specific game"""
    game = games.get(game_id)

    if not game:
        logger.info("Client requested game that does not exist", console=True)
        return jsonify({"error": "game not found"}), 404

    return jsonify(game.to_dict()), 200

@app.route("/games/<game_id>", methods=["PUT"])
def update_game(game_id):
    """Update player count and status of game, only used internally"""
    game = games.get(game_id)

    if not game:
        logger.error("Server requested game that does not exist", console=True)
        return jsonify({"error": "game not found"}), 404
    
    data = request.get_json()
    if not data or "num_players" not in data or "status" not in data:
        logger.error("Server tried to update game with invalid request body", console=True)
        return jsonify({"error": "missing required fields"})

    game.num_players = data["num_players"]
    game.status = api.GameStatus[data["status"]]

    if game.status == api.GameStatus.ENDED:
        logger.info(f'Deleting game: "{games[game.id].name}"', console=True)
        del games[game.id]
    else:
        logger.info(f'Updated game: "{games[game.id].name}"', console=True)

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
    app.run(debug=True,host="0.0.0.0", port=5000, use_reloader=False)


