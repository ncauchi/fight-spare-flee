from typing import Literal, get_args
from enum import Enum, auto
import random


class Item:

    def __init__(self):
        pass

class Player:
    name: str
    lobby_ready: bool
    session: str
    coins: int
    itmes: list[Item]

    def __init__(self, name: str, sid: str):
        self.name = name
        self.sid = sid
        self.lobby_ready = False
        self.coins = 0
        self.itmes = []

class Monster:

    def __init__(self):
        pass


class EventType(Enum):
    DAMAGE = auto()
    FSF = auto()
    COINS = auto()
    SHOP = auto()
    FIGHT = auto()
    SPARE = auto()
    FLEE = auto()


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

class TakeCoinEvent(Event):

    amount_to_take: int

    def __init__(self):
        super().__init__(type=EventType.COINS)
        self.amount_to_take = 2


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




class TurnPhase(Enum):
    CHOOSING_ACTION = auto()
    IN_COMBAT = auto()
    SHOPPING = auto()
    USING_SPECIAL = auto()
    TURN_ENDED = auto()

class GameState:
    '''
    represents all the data and logic in a game of fight spare flee
    '''
    #
    _id: str
    _name: str
    _owner: str
    _max_players: int
    _turn_order: list[str]
    _event_bus = EventBus
    players: dict[str, Player] #player_name -> Player
    status: Literal["in_lobby", "in_game", "ended"]

    #Turn
    _active_player: int
    turn_phase: TurnPhase

    #Board
    deck: list[Monster]
    shop: list[Item]

    def __init__(self, id : str, name : str, owner : str, max_players: int):
        self._id = id
        self._name = name
        self._owner = owner
        self._max_players = max_players
        self.players = {}
        self.status = "in_lobby"

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
        self._active_player = 0
        self._event_bus = EventBus()
        self.turn_phase = TurnPhase.CHOOSING_ACTION
        self.__init_shop()
        self.__init_deck()

    def handle_player_action(self, player: str, action: EventType) -> bool:
        if player not in self.players.keys():
            raise KeyError(f"Player {player} is not in the game.")
        
        if self.get_active_player() != player:
            print("Player tried to act out of turn")
            return False
        
    def _take_coins(self) -> int:
        '''
        returns the amount of coins gained
        '''
        if self.turn_phase != TurnPhase.CHOOSING_ACTION:
            print("Tried to take coins on invalid turn step")
            return
        
        coins_event = TakeCoinEvent()
        self._event_bus.emit(event=coins_event)

        self.players[self.get_active_player()].coins += coins_event.amount_to_take
        self.turn_phase = TurnPhase.TURN_ENDED
        return coins_event.amount_to_take

    def _shop(self):
        if self.turn_phase != TurnPhase.CHOOSING_ACTION:
            print("Tried to take shop for items on invalid turn step")
            return
        
        shop_event = Event()
        self._event_bus.emit(shop_event)

    def _fsf(self):
        if self.turn_phase != TurnPhase.CHOOSING_ACTION:
            print("Tried to fsf on invalid turn step")
            return
        
        self.players[self.get_active_player()].coins += 2
        self.turn_phase = TurnPhase.TURN_ENDED
        


        

    def advance_active_player(self) -> None:
        curr = self._active_player
        new_player = (curr + 1)%len(self._turn_order)
        self._active_player = new_player

    def get_active_player(self) -> str:
        return self._turn_order[self._active_player]
    
    def __init_deck(self):
        #TODO update
        self.deck = []
        
    def __init_shop(self):
        #TODO update
        self.shop = []
    

    

