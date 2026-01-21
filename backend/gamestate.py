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
    spare_coins: int
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
        self.spare_coins = data["spare_coins"]
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
                spare_coins = self.spare_coins,
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
    _combat_sbs: CombatSubState
    _pvp_sbs: PvpSubState
    _flee_combat_sbs: FleeCombatSubState

    class CombatSubState:
        monsters: list[Monster]
        leftover_queue: list[str]
        state : str # "selecting" | "fled" | "fighting" | "deciding" | "ended"
        flipped_idx: int | None

        def __init__(self, monsters: list[Monster]):
            self.monsters = monsters
            self.leftover_queue = []
            self.state = "selecting"
            self.flipped_idx = None

        def kill_spare_monster(self, monster_idx: int):
            self.monsters.pop(monster_idx)
            self.flipped_idx = None

        def flee_monster(self, monster_idx: int):
            mon = self.monsters.pop(monster_idx)
            self.leftover_queue.append(mon)
            self.flipped_idx = None
            

        def has_leftover_monsters(self) -> bool:
            """Check if any monsters are revealed but still alive"""
            return len(self.leftover_queue) > 0


    class PvpSubState:
        true_active: str
        target_items: list[Item]

    class FleeCombatSubState:
        monsters: list[Monster]
        original_player: str
        order: list[str]
        state: str # "selecting" | "fighting"
        selected_idx: int | None

        def __init__(self, monsters: list[Monster], original_player: str, order: list[str]):
            self.monsters = monsters
            self.original_player = original_player
            self.state = "selecting"
            self.order = order
            self.selected_idx = None

        def kill_spare_monster(self, monster_idx: int):
            self.monsters.pop(monster_idx)
            self.selected_idx = None
            self.state = "selecting"

        def pass_monster(self):
            self.selected_idx = None
            self.state = "selecting"

        def is_finished(self):
            return len(self.order) == 0 or len(self.monsters) == 0

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
        if self.turn_phase not in [api_wrapper.TurnPhase.IN_COMBAT,
                                    api_wrapper.TurnPhase.IN_LEFTOVER_COMBAT]:
            return None
        return [mon.get_api_status() for mon in self._combat_sbs.monsters]
    
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

    def _state_choosing_action(self, action: api_wrapper.PlayerActionChoice = None, item: int = None):
        if item != None:
            self._logger.info("pvp item placeholder")
            self.turn_phase = api_wrapper.TurnPhase.TURN_ENDED
            return
        player = self.get_active_player_obj()
        match action:
            case api_wrapper.PlayerActionChoice.COINS:
                coins_event = TakeCoinEvent()
                self._event_bus.emit(event=coins_event)
                player.coins += coins_event.amount_to_take
                self.turn_phase = api_wrapper.TurnPhase.TURN_ENDED
                self._logger.info(f'player {self.get_active_player()} took coins')
            case api_wrapper.PlayerActionChoice.SHOP:
                self._buy_item(player=player)
            case api_wrapper.PlayerActionChoice.COMBAT:
                self.turn_phase = api_wrapper.TurnPhase.IN_COMBAT
            case api_wrapper.PlayerActionChoice.END:
                self.turn_phase = api_wrapper.TurnPhase.TURN_ENDED
            case _:
                pass
        return

    def _state_shopping(self, action: api_wrapper.PlayerActionChoice = None):
        player = self.get_active_player_obj()
        if action != api_wrapper.PlayerActionChoice.SHOP:
            self._logger.warning(f'player {player.name} tried to do something other than buy an item after buying an item')
            return
        
        if len(player.items) > 4:
            self._logger.info(f'player {player.name} tried to buy an item but is holding too many')
            self.turn_phase = api_wrapper.TurnPhase.TURN_ENDED
            return            
        self._buy_item(player=player)

    def _state_combat(self, player: str, action: api_wrapper.PlayerActionChoice = None, combat_action: api_wrapper.PlayerCombatChoice = None, item: int = None, monster_idx: int = None):
        player_obj = self.players[player]

        if not hasattr(self, '_combat_sbs') or not self._combat_sbs:
            self._logger.error("combat state accessed without combat substate")
            return
        
        if monster_idx is None or monster_idx < 0 or monster_idx >= len(self._combat_sbs.monsters):
            self._logger.warning(f'invalid monster index {monster_idx}')
            return
        
        if item and self._combat_sbs and self._combat_sbs.flipped_idx:
            self._combat_fight(player_obj, self._combat_sbs.flipped_idx, item)
            return
        
        if action and action == api_wrapper.PlayerActionChoice.CANCEL:

            return

        if combat_action == api_wrapper.PlayerCombatChoice.SELECT:
            self._combat_select(player_obj, monster_idx)
        elif combat_action == api_wrapper.PlayerCombatChoice.FIGHT:
            self._combat_fight(player_obj, monster_idx, item)
        elif combat_action == api_wrapper.PlayerCombatChoice.SPARE:
            self._combat_spare(player_obj, monster_idx)
        elif combat_action == api_wrapper.PlayerCombatChoice.FLEE:
            self._combat_flee(player_obj, monster_idx)
        elif action == api_wrapper.PlayerActionChoice.SHOP:
            self._transition_to_shopping(player_obj)
        elif action == api_wrapper.PlayerActionChoice.END:
            self._end_combat()

    def _state_fled(self, player, action: api_wrapper.PlayerActionChoice = None, combat_action: api_wrapper.PlayerCombatChoice = None, monster_idx: int = None):
        player_obj = self.players[player]

        if not hasattr(self, '_combat_sbs') or not self._combat_sbs:
            self._logger.error("fled state accessed without combat substate")
            return
        
        if action == api_wrapper.PlayerActionChoice.SHOP:
            self._buy_item(player=player_obj)
        elif monster_idx and combat_action == api_wrapper.PlayerCombatChoice.SELECT:
            self._combat_select(player=player_obj, monster_idx=monster_idx)
        elif action == api_wrapper.PlayerActionChoice.END:
            self._end_combat()

    def _state_end_turn(self):
        if self.turn_phase != api_wrapper.TurnPhase.TURN_ENDED:
            self._logger.warning("tried to go to next turn but not in correct state")
            return
        if self._combat_sbs or self._combat_sbs.has_leftover_monsters():
            self._logger.info("tried to go to next turn but leftover monsters remain, entering leftover combat")
            self._end_combat()
            return
        self.advance_active_player()
        self.turn_phase = api_wrapper.TurnPhase.CHOOSING_ACTION
        

    def _buy_item(self, player: Player):
        if player.coins < 2:
            self._logger.info(f'player {player.name} tried to buy an item but does not have enough coins')
            return
        if len(player.items) > 4:
            self._logger.info(f'player {player.name} tried to buy an item but is holding too many')
            return            
        shop_event = BuyItemEvent(self.shop)
        player.coins -= 2
        self._event_bus.emit(shop_event)
        self.turn_phase = api_wrapper.TurnPhase.TURN_ENDED if player.coins < 2 else api_wrapper.TurnPhase.SHOPPING
        player.items.append(shop_event.item)
        self._logger.info(f'player {player.name} bought item {shop_event.item.name}')

    def _combat_select(self, player: Player, monster_idx: int):
        """SELECT: Reveal a face-down monster"""
        monster = self._combat_sbs.monsters[monster_idx]

        if monster.visible:
            self._logger.warning(f'{player.name} tried to select already visible monster')
            return
        if self._combat_sbs.state != "selecting":
            self._logger.warning(f'{player.name} tried to select in wrong phase')

        monster.visible = True
        self._logger.info(f'{player.name} revealed {monster.name}')
        self._combat_sbs.state = "deciding"
        self._combat_sbs.flipped_idx = monster_idx

    def _combat_fight(self, player: Player, monster_idx: int, item_idx: int):
        """FIGHT: Use item on monster"""
        monster = self._combat_sbs.monsters[monster_idx]

        if not monster.visible:
            self._logger.warning(f'{player.name} tried to fight hidden monster')
            return
        if item_idx is None or item_idx < 0 or item_idx >= len(player.items):
            self._logger.warning(f'invalid item index {item_idx}')
            return
        if self._combat_sbs.state != "deciding" or self._combat_sbs.state != "fighting":
            self._logger.warning(f'{player.name} tried to fight in wrong phase')
            return

        player.use_item(item_idx, target=monster)
        self._logger.info(f'{player.name} used item on {monster.name}')
        
        if monster.health <= 0:
            player.captured_stars.append(monster.stars)
            player.coins += monster.fight_coins
            self._logger.info(f'{player.name} killed {monster.name}')
            self._combat_sbs.kill_spare_monster(monster_idx)
            if len(self._combat_sbs.monsters) > 0:
                self._combat_sbs.state = "selecting"
            else:
                self._end_combat()
        elif len([1 for item in player.items if item.target_type == api_wrapper.ItemTarget.MONSTER]) == 0:   
            self._logger.info(f'{player.name} failed to kill {monster.name}')
            player.health -= 1
            self._end_combat()
        else:
            self._combat_sbs.state = "fighting"

    def _combat_spare(self, player: Player, monster_idx: int):
        """SPARE: Roll dice to spare monster"""
        monster = self._combat_sbs.monsters[monster_idx]

        if not monster.visible:
            self._logger.error(f'{player.name} tried to spare hidden monster')
            return
        if self._combat_sbs.state != "deciding":
            self._logger.warning(f'{player.name} tried to fight in wrong phase')
            return

        roll = random.randint(1, 6)

        if roll >= monster.spare:
            player.captured_stars.append(monster.stars)
            player.coins += monster.spare_coins
            self._combat_sbs.kill_spare_monster(monster_idx)
            self._logger.info(f'{player.name} spared {monster.name} (rolled {roll})')
            if len(self._combat_sbs.monsters) > 0:
                self._combat_sbs.state = "selecting"
            else:
                self._end_combat()
        else:
            player.health -= 1
            self._logger.info(f'{player.name} failed to spare {monster.name} (rolled {roll})')
            self._end_combat()

        
    def _combat_flee(self, player: Player, monster_idx: int):
        """FLEE: Flee from monster"""
        monster = self._combat_sbs.monsters[monster_idx]

        if not monster.visible:
            self._logger.error(f'{player.name} tried to flee from hidden monster')
            return

        if monster.flee_coins > 0:
            player.coins += monster.flee_coins
            self._combat_sbs.flee_monster(monster_idx)
            self._combat_sbs.state = "selecting"
            self.turn_phase = api_wrapper.TurnPhase.FLED
            self._logger.info(f'{player.name} fled from {monster.name}, gained {monster.flee_coins} coins')
        else:
            self._logger.warning(f'{player.name} tried to flee from a monster they can\'t escape')


    def _end_combat(self):
        """End combat and check for leftover monsters"""
        if not self._combat_sbs:
            return
        
        if self._combat_sbs.has_leftover_monsters():
            self.turn_phase = api_wrapper.TurnPhase.IN_LEFTOVER_COMBAT
            self._flee_combat_sbs = self.FleeCombatSubState(monsters=self._combat_sbs.leftover_queue, 
                                                            original_player=self.get_active_player(), 
                                                            order=[p for p in self._turn_order if p != self.get_active_player()])
            self._logger.info(f'leftover monsters remain, entering leftover combat')
        else:
            self._combat_sbs = None
            self.turn_phase = api_wrapper.TurnPhase.TURN_ENDED

    def _state_pvp(self, player: str, action: api_wrapper.PlayerActionChoice = None, item_choice: int = None, player_target: str = None):
        pass

    def _state_leftover_combat(self, player: str, combat_action: api_wrapper.PlayerCombatChoice = None, item: int = None, monster_choice: int = None):
        """Handle leftover combat - each player gets one chance to fight or pass"""

        if not self._flee_combat_sbs:
            self._logger.error("leftover combat state accessed without combat substate")
            return
        if self._flee_combat_sbs.order[0] != player:
            self._logger.warning(f'{player} tried to act in leftover combat out of turn')
            return
        
        player_obj = self.players[player]

        if item and self._flee_combat_sbs and self._flee_combat_sbs.selected_idx:
            self._leftover_fight(player_obj, self._combat_sbs.flipped_idx, item)
        elif combat_action == api_wrapper.PlayerCombatChoice.SPARE:
            self._leftover_spare(player, monster_choice)
        elif combat_action == api_wrapper.PlayerActionChoice.END:
            self._leftover_pass(player)
        else:
            self._logger.warning(f'{player} tried invalid action in leftover combat')



    def _leftover_fight(self, player_name: str, monster_idx: int, item_idx: int):
        """Player attempts to fight a leftover monster"""
        monster = self._combat_sbs.monsters[monster_idx]
        if self._flee_combat_sbs.order[0] != player_name:
            self._logger.warning(f'{player_name} tried to act in leftover combat out of turn')
            return

        player = self.players[player_name]

        if item_idx is None or item_idx < 0 or item_idx >= len(player.items):
            self._logger.warning(f'invalid item index {item_idx}')
            return

        player.use_item(item_idx, target=monster)
        self._logger.info(f'{player.name} used item on {monster.name}')
        
        if monster.health <= 0:
            player.captured_stars.append(monster.stars)
            player.coins += monster.fight_coins
            self._logger.info(f'{player.name} killed {monster.name}')
            self._flee_combat_sbs.kill_spare_monster(monster_idx)
            if self._flee_combat_sbs.is_finished():
                self._advance_leftover_queue()
        elif len([1 for item in player.items if item.target_type == api_wrapper.ItemTarget.MONSTER]) == 0:   
            self._logger.info(f'{player.name} failed to kill {monster.name}')
            player.health -= 1
            self._advance_leftover_queue()
        else:
            self._flee_combat_sbs.state = "fighting"
        
    def _leftover_spare(self, player: str, monster_idx: int):
        monster = self._combat_sbs.monsters[monster_idx]

        if self._flee_combat_sbs.state != "selecting":
            self._logger.warning(f'{player.name} tried to fight in wrong phase')
            return

        roll = random.randint(1, 6)
        if roll >= monster.spare:
            player.captured_stars.append(monster.stars)
            player.coins += monster.spare_coins
            self._flee_combat_sbs.kill_spare_monster(monster_idx)
            self._logger.info(f'{player.name} spared {monster.name} (rolled {roll})')
            if self._flee_combat_sbs.is_finished():
                self._advance_leftover_queue()
        else:
            player.health -= 1
            self._logger.info(f'{player.name} failed to spare {monster.name} (rolled {roll})')
            self._advance_leftover_queue

    def _leftover_pass(self, player_name: str):
        """Player passes on leftover combat"""
        self._logger.info(f'{player_name} passed on leftover combat')
        self._advance_leftover_queue()

    def _advance_leftover_queue(self):
        """Move to next player in leftover queue or end leftover combat"""

        if self._flee_combat_sbs.is_finished():
            self._logger.info('leftover combat complete')
            self._combat_sbs = None
            self.turn_phase = api_wrapper.TurnPhase.TURN_ENDED
        else:
            self._flee_combat_sbs.order.pop(0)
            self._logger.info(f'next leftover player: {self._flee_combat_sbs.order[0]}')


    def player_action(self, player: str, action: api_wrapper.PlayerActionChoice):

        if player not in self.players:
            self._logger.error(f'unregistered player {player} tried to take an action')
            return
        
        if player != self.get_active_player():
            self._logger.warning(f'player {player} tried to take action out of turn')
            return

        valid_states : dict[api_wrapper.TurnPhase, Callable[Any]]= {
            api_wrapper.TurnPhase.CHOOSING_ACTION: self._state_choosing_action,
            api_wrapper.TurnPhase.IN_COMBAT: self._state_combat,
            api_wrapper.TurnPhase.SHOPPING: self._state_shopping,
            api_wrapper.TurnPhase.FLED: self._state_fled,
        }

        if self.turn_phase not in valid_states:
            self._logger.warning(f'tried to do action {action.name} while in state {self.turn_phase.name}')

        valid_states[self.turn_phase](action=action)

        if self.turn_phase == api_wrapper.TurnPhase.TURN_ENDED:
            self._state_end_turn()

    def player_select_item(self, player: str, choice: int):
        if player not in self.players:
            self._logger.error(f'unregistered player {player} tried to take an action')
            return
        if self.turn_phase != api_wrapper.TurnPhase.IN_LEFTOVER_COMBAT and player != self.get_active_player():
            self._logger.warning(f'player {player} tried to take action out of turn')
            return

        valid_states = {
            api_wrapper.TurnPhase.CHOOSING_ACTION: self._state_choosing_action,
            api_wrapper.TurnPhase.IN_COMBAT: self._state_combat,
            api_wrapper.TurnPhase.IN_LEFTOVER_COMBAT: self._state_leftover_combat,
            api_wrapper.TurnPhase.PVP: self._state_pvp,
        }

        if self.turn_phase not in valid_states:
            self._logger.warning(f'tried to use item while in state {self.turn_phase.name}')
            return

        # Call appropriate state handler with item parameter
        valid_states[self.turn_phase](player=player, item=choice)

        if self.turn_phase == api_wrapper.TurnPhase.TURN_ENDED:
            self._state_end_turn()

    def player_select_monster(self, player: str, choice: int, combat_action: api_wrapper.PlayerCombatChoice):
        if player not in self.players:
            self._logger.error(f'unregistered player {player} tried to take an action')
            return
        if self.turn_phase != api_wrapper.TurnPhase.IN_LEFTOVER_COMBAT and player != self.get_active_player():
            self._logger.warning(f'player {player} tried to take action out of turn')
            return

        valid_states = {
            api_wrapper.TurnPhase.PVP: self._state_pvp,
            api_wrapper.TurnPhase.IN_COMBAT: self._state_combat,
            api_wrapper.TurnPhase.FLED: self._state_fled,
            api_wrapper.TurnPhase.IN_LEFTOVER_COMBAT: self._state_leftover_combat,
        }

        if self.turn_phase not in valid_states:
            self._logger.warning(f'tried to select monster while in state {self.turn_phase.name}')
            return

        # Call appropriate state handler with monster_choice parameter
        valid_states[self.turn_phase](player=player, monster_choice=choice, combat_action=combat_action)

        if self.turn_phase == api_wrapper.TurnPhase.TURN_ENDED:
            self._state_end_turn()

    def player_select_player(self, player: str, choice: str):
        if player not in self.players:
            self._logger.error(f'unregistered player {player} tried to take an action')
            return
        
        valid_states = {
            api_wrapper.TurnPhase.PVP: self._state_pvp,
        }

        if self.turn_phase not in valid_states:
            self._logger.warning(f'tried to select {choice} while in state {self.turn_phase.name}')

        if self.turn_phase == api_wrapper.TurnPhase.TURN_ENDED:
            self._state_end_turn()

    def advance_active_player(self) -> None:
        '''advances to next turn'''
        curr = self._active_player
        new_player = (curr + 1)%len(self._turn_order)
        self._active_player = new_player
        self._logger.info(f'{self._turn_order[curr]} ended turn, started {self._turn_order[new_player]} turn')

    def get_active_player(self) -> str | None:
        if self.status != api_wrapper.GameStatus.GAME:
            return None

        return self._turn_order[self._active_player]
    
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
    

    

