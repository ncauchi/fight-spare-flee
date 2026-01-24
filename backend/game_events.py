import eventlet
eventlet.monkey_patch()

from enum import Enum, auto
from typing import Literal, get_args, Callable, NoReturn

class EventType(Enum):
    COMBAT = auto()
    COINS = auto()
    SHOP = auto()
    FLIP = auto()
    FIGHT = auto()
    SPARE = auto()
    FLEE = auto()
    TURN = auto()


class Event:

    type: EventType
    player: str

    def __init__(self, type: EventType, player: str = None):
        self.type = type
        self.player = player
        


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

