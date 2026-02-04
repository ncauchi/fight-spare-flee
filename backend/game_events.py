import eventlet
eventlet.monkey_patch()

from enum import Enum, auto
from typing import Literal, get_args, Callable, NoReturn, Optional, Union
from api_wrapper import Animation
import api_wrapper
from pydantic import BaseModel

#type EventTdype = Literal["combat", "coins", "shop", "flip", "fight", "spare", "flee", "turn", "animation"]

class CoinsEvent(BaseModel):
    type: Literal["coins"] = "coins"
    game_id: str
    player: str
    amount: int

class HealthEvent(BaseModel):
    type: Literal["health"] = "health"
    game_id: str
    player: str
    health_amount: int

class ShopEvent(BaseModel):
    type: Literal["shop"] = "shop"
    game_id: str
    item_id: str
    item_uid: int
    player_name: str

class CombatEvent(BaseModel):
    type: Literal["combat"] = "combat"
    game_id: str
    monster_ids: list[str]
    info: list[api_wrapper.MonsterInfo]

class PlayerDamageEvent(BaseModel):
    type: Literal["player_dmg"] = "player_dmg"
    game_id: str
    player: str
    health_loss: int
    star_index: Optional[int]

type Event = Union[CoinsEvent, ShopEvent]

type EventType = Literal["coins", "shop", "combat"]


class EventBus:

    listeners: dict[str, list[Callable]]

    def __init__(self):
        self.listeners = {}

    def subscribe(self, event_type: EventType, callback: Callable[[Event], NoReturn]) -> Callable:
        '''
        Used to subscribe a function to a specific return type, returns an unsubscribe function that can be called to delink the function.
        The function will be called and passed the event whenever an event of that type happens.
        '''
        if event_type in self.listeners:
            self.listeners[event_type].append(callback)
        else:
            self.listeners[event_type] = [callback]

    def emit(self, event: Event):
        if not event:
            raise ValueError("Tried to emit non-valid event")

        if event.type not in self.listeners:
            return
        for callback in self.listeners[event.type]:
            eventlet.spawn(callback, event)

