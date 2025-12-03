from typing import Literal, get_args
from enum import Enum
import random


class Player:
    name: str
    lobby_ready: bool
    session: str

    def __init__(self, name: str, sid: str):
        self.name = name
        self.sid = sid
        self.lobby_ready = False

class Monster:

    def __init__(self):
        pass


class EventType(Enum):
    DAMAGE = "dmg"
    FSF = "fsf"

class Event:

    type: EventType
    active: bool

    def __init__(self, type: EventType):
        self.active = True
        self.type = type

class FsfEvent(Event):

    monster_results: list[Monster]

    def __init__(self, deck: list[Monster]):
        super().__init__(type=EventType.FSF)
        self.monster_results = random.sample(deck, 3)
        for monster in self.monster_results:
            deck.remove(monster)

    


class EventBus:

    listeners: dict[str, list[function]]

    def __init__(self):
        self.listeners = {}

    def subscribe(self, event_type: str, callback: function) -> function:
        '''
        Used to subscribe a function to a specific return type, returns an unsubscribe function that can be called to delink the function.
        The function will be called and passed the event whenever an event of that type happens.
        '''
        if event_type not in get_args(Event.__annotations__['type']):
            raise ValueError(f"Invalid event type: '{event_type}'.")
        
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
            callback(event)
            if not event.active:
                return




class GameState:
    '''
    represents all the data and logic in a game of fight spare flee
    '''
    _id: str
    _name: str
    _owner: str
    _max_players: int
    players: dict[str, Player] #player_name -> Player
    status: Literal["in_lobby", "in_game", "ended"]
    active_player: int
    _turn_order: list[str]
    _event_bus = EventBus


    def __init__(self, id : str, name : str, owner : str, max_players: int):
        self._id = id
        self._name = name
        self._owner = owner
        self._max_players = max_players
        self.players = {}
        self.status = "in_lobby"
        self._event_bus = EventBus()

    def to_status(self):
        return {
            "num_players": len(self.players.keys()),
            "status": self.status
        }
    
    def start(self) -> None:
        '''
        starts the game
        '''
        self.status = "in_game"
        order = [p for p in self.players.keys()]
        self._turn_order = order
        self.active_player = 0

    def advance_active_player(self) -> None:
        curr = self.active_player
        new_player = (curr + 1)%len(self._turn_order)
        self.active_player = new_player

    def get_active_player(self) -> str:
        return self._turn_order[self.active_player]
    

    

