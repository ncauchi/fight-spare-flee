from typing import Literal, get_args, Callable, Any
import warnings
from enum import Enum, auto
import random
import os
import api_wrapper
from warnings import deprecated
import yaml
from item_effects import EFFECT_REGISTRY
from app_logging import AppLogger


class Item:
    name: str
    text: str
    target_type: api_wrapper.ItemTarget = api_wrapper.ItemTarget.NONE
    effect: Callable[[Any], Any] = None
    params: dict[str, Any] = None


    def __init__(self, name: str = "", data: dict = None):
        self.name = name
        if not data:
            self.text = ""
        else:
            self.text = data["text"]
            
            if "effect" in data:
                target, effect = EFFECT_REGISTRY[data["effect"]["id"]]
                self.effect = effect
                self.params = data["effect"]["params"]
                self.target_type = target

    def activate(self, target: Player | Monster | Item | None = None):
        type_mapping = {
            api_wrapper.ItemTarget.PLAYER: Player,
            api_wrapper.ItemTarget.MONSTER: Monster,
            api_wrapper.ItemTarget.ITEM: Item,
            api_wrapper.ItemTarget.NONE: type(None)
        }

        if not isinstance(target, type_mapping[self.target_type]):
            raise TypeError(
                f"Item '{self.name}' requires target of type {self.target_type.value}, "
                f"but got {type(target).__name__}"
            )
        if self.effect:
            self.effect(target, **self.params)

    def get_api_status(self):
        return api_wrapper.ItemInfo(name=self.name, text=self.text, target_type=self.target_type)


class Monster:
    stars: int
    name: str
    health: int
    spare: int
    visible: bool
    flee_coins: int
    fight_coins: int
    max_health: int

    def __init__(self, name: str = "", data: dict = None):
        if not data:
            return
        req = ["stars", "health", "spare", "flee_coins", "fight_coins"]
        if not all(field in data for field in req):
            raise ValueError("Tried to initialize monster without all required fields")
        self.name = name
        self.stars = data["stars"]
        self.visible = False
        self.health = data["health"]
        self.spare = data["spare"]
        self.flee_coins = data["flee_coins"]
        self.fight_coins = data["fight_coins"]
        self.max_health = data["health"]

    def get_api_status(self):
        if self.visible:
            return api_wrapper.MonsterInfo(
                name = self.name,
                stars=self.stars,
                max_health=self.max_health,
                health=self.health,
                spare=self.spare,
                flee_coins=self.flee_coins,
                fight_coins=self.fight_coins,
            )
        else:
            return api_wrapper.MonsterInfo(
                stars=self.stars
            )




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
        self.items = []
        self.captured_stars = []
        self.health = 4

    def use_item(self, item_pos: int, target: Player | Monster | Item | None = None):
        item = self.items.pop(item_pos)
        item.activate(target=target)

    def get_status_hand(self):
        return [item.get_api_status() for item in self.items]
    
    def get_status_public(self):
        return api_wrapper.PlayerInfo(
            name = self.name,
            ready=self.lobby_ready,
            coins=self.coins,
            num_items=len(self.items),
            captured_stars=self.captured_stars,
            health=self.health
        )


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






class GameState:
    '''
    represents all the data and logic in a game of fight spare flee
    '''
    #Config
    _id: str
    _name: str
    _owner: str
    _max_players: int
    _allowed_items : list[str]
    _allowed_monsters: list[str]
    _logger: AppLogger


    _turn_order: list[str]
    _event_bus = EventBus
    players: dict[str, Player] #player_name -> Player
    status: api_wrapper.GameStatus

    #Turn
    _active_player: int
    turn_phase: api_wrapper.TurnPhase

    #Board
    deck: list[Monster]
    shop: list[Item]
    fsf_monsters: list[Monster]

    def __init__(self, id : str, name : str, owner : str, max_players: int, allowed_items: Literal["*"] | list[str] = "*", allowed_monsters: Literal["*"] | list[str] = "*"):
        self._id = id
        self._name = name
        self._owner = owner
        self._max_players = max_players
        self.players = {}
        self.status = api_wrapper.GameStatus.LOBBY
        self._logger = AppLogger(name=f"game_{name}")

        self._allowed_items = allowed_items
        self._allowed_monsters = allowed_monsters



    
    def get_status_lobby(self):
        """
        Returns high level game status in JSON format
        """
        return {
            "num_players": len(self.players.keys()),
            "status": self.status.name
        }
    
    def get_status_players(self):
        """
        Returns api public players info in JSON format
        """
        return [player.get_status_public() for player in self.players.values()]

    def get_status_board(self):
        """
        Returns api board status in JSON format
        """
        return {
            "deck_size": len(self.deck),
            "shop_size": len(self.shop),
            "monsters": self.get_status_fsf(),
            "items": []
        }
    
    def get_status_fsf(self) -> list[api_wrapper.MonsterInfo]:
        if self.turn_phase != api_wrapper.TurnPhase.IN_COMBAT:
            return None
        return [mon.get_api_status() for mon in self.fsf_monsters]
    
    def add_player(self, player_name, sid) -> None:
        self.players[player_name] = Player(name=player_name, sid=sid)

    def set_player_lobby_ready(self, player_name, ready) -> None:
        player = self.players[player_name]
        player.lobby_ready = ready

    def start(self) -> None:
        '''
        starts the game
        '''
        self.status = api_wrapper.GameStatus.GAME
        order = [p for p in self.players.keys()]
        self._turn_order = order
        self._active_player = 0
        self._event_bus = EventBus()
        self.turn_phase = api_wrapper.TurnPhase.CHOOSING_ACTION
        self.__init_shop()
        self.__init_deck()

    def active_player_take_coins(self) -> int:
        '''
        returns the amount of coins gained
        '''
        if self.turn_phase != api_wrapper.TurnPhase.CHOOSING_ACTION:
            self._logger.error("tried to take coins on invalid turn phase")
            return
        
        coins_event = TakeCoinEvent()
        self._event_bus.emit(event=coins_event)

        self.get_active_player_obj().coins += coins_event.amount_to_take
        self.turn_phase = api_wrapper.TurnPhase.TURN_ENDED
        self._logger.info(f'player {self.get_active_player()} took coins')
        return coins_event.amount_to_take

    
    def active_player_buy_item(self) -> Item:
        if self.turn_phase != api_wrapper.TurnPhase.CHOOSING_ACTION and self.turn_phase != api_wrapper.TurnPhase.SHOPPING:
            self._logger.error("tried to buy an item on invalid turn phase")
            return None
        player = self.get_active_player_obj()
        if player.coins < 2:
            self._logger.info(f'player {player.name} tried to buy an item but does not have enough coins')
            return None

        if len(player.items) > 4:
            self._logger.info(f'player {player.name} tried to buy an item but is holding too many')
            return None
        
        shop_event = BuyItemEvent(self.shop)
        player.coins -= 2
        self._event_bus.emit(shop_event)
        self.turn_phase = api_wrapper.TurnPhase.TURN_ENDED if player.coins < 2 else api_wrapper.TurnPhase.SHOPPING
        player.items.append(shop_event.item)
        self._logger.info(f'player {player.name} bought item {shop_event.item.name}')

        return shop_event.item

    def active_player_fsf(self) -> None:
        if self.turn_phase != api_wrapper.TurnPhase.CHOOSING_ACTION:
            self._logger.error(f'tried to fsf on invalid turn phase')
            return
        
        fsf_event = FsfEvent(self.deck)
        self._event_bus.emit(fsf_event)
        self.fsf_monsters = fsf_event.monster_results
        
        self.turn_phase = api_wrapper.TurnPhase.IN_COMBAT
        self._logger.info(f'player {self.get_active_player()} entered combat')
        return
    
    def fsf_select(self, choice: int):
        if choice < 0 or choice >= len(self.fsf_monsters):
            raise ValueError("Invalid target for fsf")
        mon_choice = self.fsf_monsters[choice]
        if mon_choice.visible:
            raise Warning("Selected already visible monster for fsf")
        mon_choice.visible = True
        self._logger.info(f'player {self.get_active_player()} flipped monster {mon_choice.name}')
        
    def fsf_fight(self, target: int, item: int) -> None:
        """
        use item on selected monster to try and lower its heatlh
        """
        if self.turn_phase != api_wrapper.TurnPhase.IN_COMBAT:
            self._logger.error("tried to fight in invalid turn phase")
        
        player = self.get_active_player_obj()
        tar_mon = self.fsf_monsters[target]
        if not tar_mon.visible:
            warnings.warn("Fighting monster thats not flipped over")
        if item < 0:
            player.health -= 1
            self.turn_phase = api_wrapper.TurnPhase.TURN_ENDED
            self.fsf_monsters = []
            return

        player.use_item(item_pos=item, target=tar_mon)
        
        
        if tar_mon.health < 1:
            player.captured_stars.append(tar_mon.stars)
            player.coins += tar_mon.fight_coins
            self.turn_phase = api_wrapper.TurnPhase.TURN_ENDED
            self.fsf_monsters = []
            self._logger.info(f'player {player.name} used item {player.items[item].name} on {tar_mon.name} and reduced its health to 0')
        else:
            self._logger.info(f'player {player.name} used item {player.items[item].name} on {tar_mon.name}')
            pass


    def fsf_spare(self, target: int):
        if self.turn_phase != api_wrapper.TurnPhase.IN_COMBAT:
            self._logger.error("tried to spare in invalid turn phase")
        player = self.get_active_player_obj()
        tar_mon = self.fsf_monsters[target]
        if not tar_mon.visible:
            self._logger.error("tried to spare monster that is not flipped over")
            return
        
        if random.randint(1, 6) >= tar_mon.spare:
            player.captured_stars.append(tar_mon.stars)
            self._logger.info(f'player {player.name} spared monster {tar_mon.name}')
        else:
            player.health -= 1
            self._logger.info(f'player {player.name} failed spare on {tar_mon.name}')
        self.turn_phase = api_wrapper.TurnPhase.TURN_ENDED
        self.fsf_monsters = []
        
    def fsf_flee(self, target: int):
        if self.turn_phase != api_wrapper.TurnPhase.IN_COMBAT:
            self._logger.error("tried to spare in invalid turn phase")
        player = self.get_active_player_obj()
        tar_mon = self.fsf_monsters[target]
        if not tar_mon.visible:
            self._logger.error("tried to spare monster that is not flipped over")
            return
        
        if tar_mon.flee_coins > 0:
            player.coins += tar_mon.flee_coins
            self._logger.info(f'player {player.name} fleed from {tar_mon.name}')
        else:
            player.health -= 1
            self._logger.info(f'player {player.name} flee spare on {tar_mon.name}')
        self.turn_phase = api_wrapper.TurnPhase.TURN_ENDED
        self.fsf_monsters = []

    def advance_active_player(self) -> None:
        '''
        advances to next turn
        '''
        curr = self._active_player
        new_player = (curr + 1)%len(self._turn_order)
        self._active_player = new_player
        if self.turn_phase != api_wrapper.TurnPhase.TURN_ENDED:
            self._logger.warning("advancing turn before all actions taken")
        self.turn_phase = api_wrapper.TurnPhase.CHOOSING_ACTION
        self._logger.info(f'{self._turn_order[curr]} ended turn, started {self._turn_order[new_player]} turn')

    def _advance_turn_phase(self) -> None:
        pass

    def get_active_player(self) -> str | None:
        return self._turn_order[self._active_player] if self.status == api_wrapper.GameStatus.GAME else None
    
    def get_active_player_obj(self) -> Player:
        return self.players[self._turn_order[self._active_player]] if self.status == api_wrapper.GameStatus.GAME else None
    
    def __init_deck(self):
        library_path = os.path.join(os.path.dirname(__file__), 'library.yaml')
        with open(library_path, 'r') as file:
            try:
                data = yaml.load(file, yaml.Loader)
                self.deck = [Monster()]*40
                for i in range(40):
                    if self._allowed_monsters == "*":
                        mon_name = random.choice(list(data["monsters"].keys()))
                    else:
                        mon_name = random.choice(self._allowed_monsters)
                    cur_mon: dict = data["monsters"][mon_name]
                    self.deck[i] = Monster(name=mon_name, data=cur_mon)
                self._logger.info("intialized monster deck")

            except yaml.YAMLError as exc:
                print(exc)
        
    def __init_shop(self):
        library_path = os.path.join(os.path.dirname(__file__), 'library.yaml')
        with open(library_path, 'r') as file:
            try:
                data = yaml.load(file, yaml.Loader)
                self.shop = [Item()]*40
                for i in range(40):
                    if self._allowed_items == "*":
                        item_name = random.choice(list(data["items"].keys()))
                    else:
                        item_name = random.choice(self._allowed_items)
                    cur_item = data["items"][item_name]
                    self.shop[i] = Item(name=item_name, data=cur_item)
                self._logger.info("intialized item shop")

            except yaml.YAMLError as exc:
                print(exc)
    

    

