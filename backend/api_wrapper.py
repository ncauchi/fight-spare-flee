from enum import Enum
from typing import List, Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, field_validator
import socketio as sio_lib
import asyncio

# Enums

class PlayerActionChoice(Enum):
    COINS = "COINS"
    HEALTH = "HEALTH"
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
    id: int
    name: str
    text: str
    target_type: ItemTarget

class Message(BaseModel):
    player_name: str
    text: str

class MonsterInfo(BaseModel):
    id: int
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


# Cosmetic Event Types

type SimpleLocation = Literal["shop", "deck", "coins", "health", "player"]

class HandLocation(BaseModel):
    object: Literal["hand"] = "hand"
    id: int

class MonsterLocation(BaseModel):
    object: Literal["monster"] = "monster"
    id: int

type Location = Union[SimpleLocation, HandLocation, MonsterLocation]


class StarAnimContent(BaseModel):
    type: Literal["star"] = "star"

class CoinAnimContent(BaseModel):
    type: Literal["coin"] = "coin"

class ItemAnimContent(BaseModel):
    type: Literal["item"] = "item"
    item: ItemInfo
    style: Literal["draw", "attack"]

class MonsterAnimContent(BaseModel):
    type: Literal["monster"] = "monster"
    monster: MonsterInfo
    style: Literal["appear", "kill", "spare", "flee", "return", "fail"]

type AnimContent = Union[StarAnimContent, CoinAnimContent, ItemAnimContent, MonsterAnimContent]

class Animation(BaseModel):
    content: AnimContent
    source: Location
    destination:  Optional[Location]

class FsfApi():
    def __init__(self, server: sio_lib.AsyncServer):
        self.server = server
        

    def event_handler(self, request_model=None):
        def decorator(handler_func):
            event_name = handler_func.__name__

            async def wrapper(sid, data=None):
                if request_model:
                    try:
                        request_data = request_model(**data) if data else request_model()
                    except Exception as e:
                        print(f"Error parsing {event_name} request: {e}")
                        return
                else:
                    request_data = data
                return await handler_func(request_data, sid)

            wrapper.__name__ = event_name
            self.server.on(event_name, wrapper)
            return wrapper
        return decorator

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
        asyncio.create_task(self.server.emit("INIT", init_data, to=to))


    def emit_start_game_event(self, to: str, first_player: str):
        """Emit START_GAME event to signal game start."""
        asyncio.create_task(self.server.emit("START_GAME", first_player, to=to))

    def emit_players_event(self, to: str, players: List[PlayerInfo], include_self: bool = True):
        """Emit PLAYERS event to broadcast updated player information."""
        event_data = [player.model_dump(mode='json') for player in players]
        asyncio.create_task(self.server.emit("PLAYERS", event_data, to=to, skip_sid=None))

    def emit_chat_event(self, to: str, message: Message, include_self: bool = True):
        """Emit CHAT event to broadcast a chat message."""
        asyncio.create_task(self.server.emit("CHAT", message.model_dump(mode='json'), to=to, skip_sid=None))

    def emit_turn_event(self, to: str, active: str, phase: TurnPhase):
        """Emit CHANGE_TURN event to signal active player change."""
        asyncio.create_task(self.server.emit("CHANGE_TURN", {"active": active, "phase": phase.name}, to=to))

    def emit_board_event(self, to: str, deck_size: int, shop_size: int, monsters : List[MonsterInfo] = [], selected_monster: int = None, items : list[ItemInfo] = []):
        item_i = [item.model_dump(mode='json') for item in items] if items else []
        mon_i = [mon.model_dump(mode='json') for mon in monsters] if monsters else []
        asyncio.create_task(self.server.emit("BOARD", {"deck_size": deck_size, "shop_size": shop_size, "monsters": mon_i, "selected_monster": selected_monster, "items": item_i}, to=to))

    def emit_hand_event(self, to: str, items: List[ItemInfo], selected_items: List[bool] = None):
        item_i = [item.model_dump(mode='json') for item in items] if items else []
        
        asyncio.create_task(self.server.emit("ITEMS", {"items": item_i, "selected_items": selected_items}, to=to))


    #Animation/Cosmetic events

    def emit_anim_event(self, to: str, animation: Animation):     
        asyncio.create_task(self.server.emit("ANIMATION", animation.model_dump(mode='json'), to=to))
