import os
from typing import Optional
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from game_meta import GameMetadata
import api_wrapper as api
from app_logging import AppLogger
from pydantic import BaseModel
from db_utils import init_db, teardown_db
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print("Database initialized")
    yield
    await teardown_db()
    print("Database connections closed")


app = FastAPI(lifespan=lifespan)
games_api_url = os.environ.get("GAMES_API_URL", "http://localhost:5001")


# In-memory storage for games

games : dict[str, GameMetadata] = {}

logger = AppLogger(name='lobby_server', color='cyan')

@app.get("/games", status_code=200)
def get_games():
    #Get all games
    logger.info("Client requested all games", console=True)
    games_list = [game.to_dict() for game in games.values()]
    return JSONResponse(games_list)

class CreateGameRequest(BaseModel):
    name: str
    owner: str
    max_players: int = 4

@app.post("/games")
async def create_lobby(data: CreateGameRequest):
    #Create new game
    #TODO make process aswell

    game = GameMetadata( name=data.name, owner=data.owner, max_players=data.max_players )
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f'{games_api_url}/internal/{game.id}',
            json=game.to_setup(),
        )

    if response.status_code != 201:
        logger.error("Failed to connect to game server", console=True)
        return JSONResponse({"error": "Could not create game"}, 500)
    
    games[game.id] = game

    logger.info(f'New game: "{game.id}"', console=True)

    return {"id": game.id}


@app.get("/games/{game_id}")
def get_game(game_id):
    """Get details of a specific game"""
    game = games.get(game_id)

    if not game:
        logger.info("Client requested game that does not exist", console=True)
        return JSONResponse({"error": "game not found"}, status_code=404)

    return game.to_dict()

class GameUpdate(BaseModel):
    num_players: int
    status: str

@app.put("/games/{game_id}")
async def update_game(game_id, data: GameUpdate):
    """Update player count and status of game, only used internally"""
    game = games.get(game_id)

    if not game:
        logger.error("Server requested game that does not exist", console=True)
        return JSONResponse({"error": "game not found"}, status_code=404)

    game.num_players = data.num_players
    game.status = api.GameStatus[data.status]

    if game.status == api.GameStatus.ENDED:
        logger.info(f'Deleting game: "{games[game.id].name}"', console=True)
        del games[game.id]
    else:
        logger.info(f'Updated game: "{games[game.id].name}"', console=True)

    return {"response": "ok"}


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



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)


