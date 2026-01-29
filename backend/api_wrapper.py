from enum import Enum
from typing import List, Optional, Dict, Any
from flask_socketio import SocketIO, join_room, leave_room, emit, disconnect
from pydantic import BaseModel, field_validator


# Enums

class PlayerActionChoice(Enum):
    COINS = "COINS"
    SHOP = "SHOP"
    COMBAT = "COMBAT"
    END = "END"
    CANCEL = "CANCEL"

class PlayerCombatChoice(Enum):
    FIGHT = "FIGHT"
    SPARE = "SPARE"
    FLEE = "FLEE"
    SELECT = "SELECT"

class GameStatus(Enum):
    LOBBY = "LOBBY"
    GAME = "GAME"
    ENDED = "END"

class TurnPhase(Enum):
    CHOOSING_ACTION = "CHOOSING_ACTION"
    COMBAT_SELECT = "COMBAT_SELECT"
    COMBAT_ACTION = "COMBAT_ACTION"
    COMBAT_FIGHT = "COMBAT_FIGHT"
    SHOPPING = "SHOPPING"
    FLED = "FLED"
    PVP = "PVP"
    TURN_ENDED = "TURN_ENDED"


class ItemTarget(Enum):
    MONSTER = "MONSTER"
    PLAYER = "PLAYER"
    ITEM = "ITEM"
    NONE = "NONE"

# Shared Object Models

class ItemInfo(BaseModel):
    name: str
    text: str
    target_type: ItemTarget

class Message(BaseModel):
    player_name: str
    text: str

class MonsterInfo(BaseModel):
    name: Optional[str] = None
    stars: int
    max_health: Optional[int] = None
    health: Optional[int] = None
    spare: Optional[int] = None
    flee_coins: Optional[int] = None
    spare_coins: Optional[int] = None
    fight_coins: Optional[int] = None


    @field_validator('stars')
    @classmethod
    def validate_stars(cls, v):
        if not 1 <= v <= 3:
            raise ValueError('stars must be between 1 and 3')
        return v

class PlayerInfo(BaseModel):
    name: str
    ready: bool
    coins: int
    captured_stars: list[int]
    num_items: int
    health: int


# Client Request Models (Client → Server)

class JoinRequest(BaseModel):
    game_id: str
    player_name: str

class LobbyReadyRequest(BaseModel):
    ready: bool

class StartGameRequest(BaseModel):
    pass

class ChatRequest(BaseModel):
    text: str

class ActionRequest(BaseModel):
    choice: PlayerActionChoice

class CombatRequest(BaseModel):
    combat: Optional[PlayerCombatChoice] = None
    target: Optional[int] = -1

class ItemChoiceRequest(BaseModel):
    item: int

class PlayerChoiceRequest(BaseModel):
    player: str


# Server Sent Events

class Fsf_api():
    def __init__(self, server: SocketIO):
        self.server = server

    def event_handler(self, request_model=None):
        """
        Decorator to register SocketIO event handlers with automatic request parsing.

        Usage:
            @api.event_handler(JoinRequest)
            def JOIN(request_data, sid):
                player_name = request_data.player_name
                game_id = request_data.game_id
                ...your logic here

        Args:
            request_model: Pydantic model class for parsing incoming data
        """
        def decorator(handler_func):  # Level 2: Takes the function being decorated
            from flask import request
            event_name = handler_func.__name__

            def wrapper(data):  # Level 3: Called when event fires
                sid = request.sid

                if request_model:
                    try:
                        request_data = request_model(**data) if data else request_model()
                    except Exception as e:
                        print(f"Error parsing {event_name} request: {e}")
                        return
                else:
                    request_data = data

                return handler_func(request_data, sid)

            wrapper.__name__ = event_name
            self.server.on_event(event_name, wrapper)
            return wrapper

        return decorator  # Level 1: Returns the decorator

    def emit_init_response(self, to: str, game_name: str, game_owner: str, max_players: int, players: List[PlayerInfo], messages: List[Message], status: GameStatus, active_player: Optional[str] = None):
        """Emit INIT event to initialize game state for a joining player."""
        init_data = {
            "game_name": game_name,
            "game_owner": game_owner,
            "max_players": max_players,
            "players": [player.model_dump() for player in players],
            "messages": [message.model_dump() for message in messages],
            "status": status,
            "active_player": active_player,
        }
        self.server.emit("INIT", init_data, to=to)


    def emit_start_game_event(self, to: str, first_player: str):
        """Emit START_GAME event to signal game start."""
        self.server.emit("START_GAME", first_player, to=to)

    def emit_players_event(self, to: str, players: List[PlayerInfo], include_self: bool = True):
        """Emit PLAYERS event to broadcast updated player information."""
        event_data = [player.model_dump(mode='json') for player in players]
        self.server.emit("PLAYERS", event_data, to=to, include_self=include_self)

    def emit_chat_event(self, to: str, message: Message, include_self: bool = True):
        """Emit CHAT event to broadcast a chat message."""
        self.server.emit("CHAT", message.model_dump(mode='json'), to=to, include_self=include_self)

    def emit_turn_event(self, to: str, active: str, phase: TurnPhase):
        """Emit CHANGE_TURN event to signal active player change."""
        self.server.emit("CHANGE_TURN", {"active": active, "phase": phase.name}, to=to)

    def emit_board_event(self, to: str, deck_size: int, shop_size: int, monsters : List[MonsterInfo] = [], selected_monster: int = None, items : list[ItemInfo] = []):
        item_i = [item.model_dump(mode='json') for item in items] if items else []
        mon_i = [mon.model_dump(mode='json') for mon in monsters] if monsters else []
        self.server.emit("BOARD", {"deck_size": deck_size, "shop_size": shop_size, "monsters": mon_i, "selected_monster": selected_monster, "items": item_i}, to=to)

    def emit_hand_event(self, to: str, items: List[ItemInfo], selected_items: List[bool] = None):
        item_i = [item.model_dump(mode='json') for item in items] if items else []
        
        self.server.emit("ITEMS", {"items": item_i, "selected_items": selected_items}, to=to)