from typing import Literal, get_args, Callable
from enum import Enum, auto
import random


class Item:
    name: str

    def __init__(self):
        pass

class Monster:
    stars: int
    name: str

    def __init__(self):
        self.stars = 1
        self.name = "tmp"


class Player:
    name: str
    lobby_ready: bool
    sid: str
    coins: int
    items: list[Item]
    captured_stars: list[int]
    health: int

    def __init__(self, name: str, sid: str):
        self.name = name
        self.sid = sid
        self.lobby_ready = False
        self.coins = 0
        self.itmes = []
        self.captured_stars = []
        self.health = 4

    def get_status_hand(self):
        return {
            "items": [{'name': item.name} for item in self.itmes],
        }
    
    def get_status_public(self):
        return {
            "name": self.name, 
            "ready": self.lobby_ready,
            "coins": self.coins,
            "num_items": len(self.itmes),
            "health": self.health,
        }


class EventType(Enum):
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

class BuyItemEvent(Event):
    item: Item
    def __init__(self, shop: list[Item]):
        super().__init__(type=EventType.SHOP)
        self.item = shop.pop()
        


class EventBus:

    listeners: dict[str, list[Callable]]

    def __init__(self):
        self.listeners = {}

    def subscribe(self, event_type: str, callback: Callable) -> Callable:
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
    fsf_monsters: list[tuple[Monster, bool]] # Monster, is_flipped

    def __init__(self, id : str, name : str, owner : str, max_players: int):
        self._id = id
        self._name = name
        self._owner = owner
        self._max_players = max_players
        self.players = {}
        self.status = "in_lobby"
    
    def get_status_lobby(self):
        """
        Returns high level game status in JSON format
        """
        return {
            "num_players": len(self.players.keys()),
            "status": self.status
        }
    
    def get_status_players(self):
        """
        Returns public players info in JSON format
        """
        return [player.get_status_public() for player in self.players.values()]

    def get_status_board(self):
        """
        Returns board status in JSON format
        """

        ret = {
            'deck': {
                'size': len(self.deck),
                'top_card_stars': self.deck[0].stars,
            },
            'shop': {
                'size': len(self.shop),
            },
        }

        if self.turn_phase == TurnPhase.IN_COMBAT:
            visible_monsters = [{'name': monster.name, 'stars': monster.stars} for monster, visible in self.fsf_monsters if visible]
            flipped_monsters = [{'stars': monster.stars} for monster, visible in self.fsf_monsters if not visible]

            ret["monsters"] = {'visible': visible_monsters, 'flipped': flipped_monsters}

        return ret
    
    
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

        
    def take_coins(self) -> int:
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

    def shop_items(self) -> Item:
        if self.turn_phase != TurnPhase.CHOOSING_ACTION or self.turn_phase != TurnPhase.SHOPPING:
            print("Tried to take shop for items on invalid turn step")
            return None
        player = self.get_active_player_obj()
        if player.coins < 2:
            print("Player does not have enough coins to buy")
            return None

        if player.itmes > 4:
            print("Player has too many items to buy")
            return None
        
        shop_event = BuyItemEvent(self.shop)
        player.coins -= 2
        self._event_bus.emit(shop_event)
        self.turn_phase = TurnPhase.TURN_ENDED if player.coins < 2 else TurnPhase.SHOPPING

        return shop_event.item

    def fsf(self) -> None:
        if self.turn_phase != TurnPhase.CHOOSING_ACTION:
            print("Tried to fsf on invalid turn step")
            return
        
        fsf_event = FsfEvent()
        self._event_bus.emit(fsf_event)
        self.fsf_monsters = [(monster, False) for monster in fsf_event.monster_results]
        
        self.turn_phase = TurnPhase.IN_COMBAT
        return
        
    def fsf_fight(self):
        if self.turn_phase != TurnPhase.IN_COMBAT:
            print("Tried to fight but turn phase is not 'in combat' ")
        self.turn_phase = TurnPhase.TURN_ENDED
        pass

    def fsf_spare(self):
        if self.turn_phase != TurnPhase.IN_COMBAT:
            print("Tried to fight but turn phase is not 'in combat' ")
        self.turn_phase = TurnPhase.TURN_ENDED
        pass
        
    def fsf_flee(self):
        if self.turn_phase != TurnPhase.IN_COMBAT:
            print("Tried to fight but turn phase is not 'in combat' ")
        self.turn_phase = TurnPhase.TURN_ENDED
        pass

    def advance_active_player(self) -> None:
        curr = self._active_player
        new_player = (curr + 1)%len(self._turn_order)
        self._active_player = new_player

        self.turn_phase = TurnPhase.CHOOSING_ACTION

    def get_active_player(self) -> str:
        return self._turn_order[self._active_player]
    
    def get_active_player_obj(self) -> Player:
        return self.players[self._turn_order[self._active_player]]
    
    def __init_deck(self):
        #TODO update
        m = Monster()
        m.name = "dev_monster"
        m.stars = 2
        self.deck = [m]*99
        
    def __init_shop(self):
        #TODO update
        
        self.shop = []
    

    

