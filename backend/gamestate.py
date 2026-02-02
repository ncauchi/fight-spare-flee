from typing import Literal, get_args, Callable, Any
import warnings
from enum import Enum, auto
import random
import os
import api_wrapper
from warnings import deprecated
import yaml
from item_effects import EFFECT_REGISTRY, ITEM_REGISTRY, MONSTER_REGISTRY
from app_logging import AppLogger
from game_events import *
import uuid


class Item:
    id: int
    name: str
    text: str
    target_type: api_wrapper.ItemTarget = api_wrapper.ItemTarget.NONE
    effect: Callable[[Any], Any] = None
    params: dict[str, Any] = None

    next_id = 0


    def __init__(self, name: str = "", data: dict = None):
        self.name = name
        self.id = Item.next_id
        Item.next_id += 1
        if not data:
            self.text = ""
        else:
            self.text = data["text"]
            
            if "effect" in data:
                target, effect = EFFECT_REGISTRY[data["effect"]["id"]]
                self.effect = effect
                self.params = data["effect"]["params"]
                self.target_type = target
    
    @staticmethod
    def construct_from_id(id: str) -> Item:
        if id not in ITEM_REGISTRY.keys():
            raise KeyError(f"Item {id} does not exit")
        cur_item: dict = ITEM_REGISTRY[id]
        return Item(name=id, data=cur_item)
    
    @staticmethod
    def info_from_id(id: str) -> api_wrapper.ItemInfo:
        if id not in ITEM_REGISTRY.keys():
            raise KeyError(f"Item {id} does not exit")
        data: dict = ITEM_REGISTRY[id]
        if "effect" in data:
            target, _ = EFFECT_REGISTRY[data["effect"]["id"]]
        else:
            target = api_wrapper.ItemTarget.NONE
            
        return api_wrapper.ItemInfo(id=-1, name=id, text=data["text"], target_type=target)


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
        return api_wrapper.ItemInfo(id= self.id, name=self.name, text=self.text, target_type=self.target_type)


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
    id: int

    next_id = 0

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
        self.id = Monster.next_id
        Monster.next_id += 1

    @staticmethod
    def construct_from_id(id: str) -> Monster:
        if id not in MONSTER_REGISTRY.keys():
            raise KeyError(f"monster {id} does not exit")
        cur_mon: dict = MONSTER_REGISTRY[id]
        return Monster(name=id, data=cur_mon)

    def get_api_status(self):
        if self.visible:
            return api_wrapper.MonsterInfo(
                id = self.id,
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
                id = self.id,
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

    def use_items(self, items: list[int], target: Player | Monster | Item | None = None):
        for i in items:
            self.items[i].activate(target=target)
        for i in sorted(items, reverse=True):
            del self.items[i]

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
    _combat_substate: CombatSubstate

    class CombatSubstate:
        monsters: list[Monster]
        selected_items: list[bool]
        state: str # "selecting" | "deciding" | "fighting"
        player: Player
        selected_idx : int | None

        def __init__(self, monsters: list[Monster], player: Player):
            self.monsters = monsters
            self.player = player
            self.state = "selecting"
            self.selected_items = [False]*len(player.items)
            self.selected_idx = None

        def kill_monster(self):
            pass

        def spare_monster(self) -> tuple[int, bool]:
            mon : Monster = self.monsters[self.selected_idx]
            roll = random.randint(1, 6)

            if roll >= mon.spare:
                self.player.captured_stars.append(mon.stars)
                self.player.coins += mon.spare_coins
                self.monsters.pop(0)        
            else:
                self.player.health -= 1
            return (roll, roll >= mon.spare)
            

        def pass_monster(self) -> api_wrapper.TurnPhase:
            pass

        def select_monster(self, idx: int):
            pass

        def is_valid_player(self, player: Player):
            return player == self.player


    class NCombatSubstate(CombatSubstate):
        leftover_queue: list[Monster]

        def __init__(self, monsters, player):
            super().__init__(monsters, player)
            self.leftover_queue = []

        def kill_monster(self):
            self.monsters.pop(self.selected_idx)

        def pass_monster(self) -> api_wrapper.TurnPhase:
            mon = self.monsters.pop(self.selected_idx)
            self.leftover_queue.append(mon)
            self.player.coins += mon.flee_coins
            self.selected_idx = None
            self.state = "selecting"
            return api_wrapper.TurnPhase.FLED   
            
        def select_monster(self, idx: int):
            self.selected_idx = idx
            self.state = "deciding"
            if not self.monsters[idx].visible:
                self.monsters[idx].visible = True

        def has_leftover_monsters(self) -> bool:
            """Check if any monsters are revealed but still alive"""
            return len(self.leftover_queue) > 0
        
    class LCombatSubstate(CombatSubstate):
        original_player: str
        order: list[Player]

        def __init__(self, monsters: list[Monster], player: Player, order: list[str]):
            super().__init__(monsters, player)
            self.original_player = player.name
            self.order = order
            self.player = self.order[0]
            self.selected_items = [False]*len(player.items)

        def kill_monster(self):
            self.monsters.pop(self.selected_idx)
            self.selected_idx = None
            self.state = "selecting"
            self.player = self.order.pop(0)
            self.selected_items = [False]*len(self.player.items)

        def spare_monster(self) -> tuple[int, bool]:
            self.state = "selecting"
            self.player = self.order.pop(0)
            self.selected_items = [False]*len(self.player.items)
            return super().spare_monster()
            

        def pass_monster(self) -> api_wrapper.TurnPhase:
            self.selected_idx = None
            self.state = "selecting"
            self.player = self.order.pop(0)
            self.selected_items = [False]*len(self.player.items)
            if len(self.order) == 0:
                return api_wrapper.TurnPhase.TURN_ENDED
            else:
                return api_wrapper.TurnPhase.COMBAT_SELECT

        def select_monster(self, idx: int):
            self.selected_idx = idx
            self.state = "deciding"

        def is_finished(self):
            return len(self.order) == 0 or len(self.monsters) == 0


    class PvpSubState:
        true_active: str
        target_items: list[Item]


    def __init__(self, id : str, name : str, owner : str, max_players: int, allowed_items: Literal["*"] | list[str] = "*", allowed_monsters: Literal["*"] | list[str] = "*"):
        self._id = id
        self._name = name
        self._owner = owner
        self._max_players = max_players
        self.players = {}
        self.status = api_wrapper.GameStatus.LOBBY
        self._logger = AppLogger(name=f"game_{name}")
        self._event_bus = EventBus()

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
        if self._combat_substate:
            monsters = [mon.get_api_status() for mon in self._combat_substate.monsters]
            selected_monster = self._combat_substate.selected_idx
        else:
            monsters = []
            selected_monster = None

        return {
            "deck_size": len(self.deck),
            "shop_size": len(self.shop),
            "monsters": monsters,
            "selected_monster": selected_monster,
            "items": []
        }
        
    
    def add_player(self, player_name, sid) -> None:
        self.players[player_name] = Player(name=player_name, sid=sid)
        self._logger.info(f'player {player_name} joined game')

    def set_player_lobby_ready(self, player_name, ready) -> None:
        player = self.players[player_name]
        player.lobby_ready = ready
        self._logger.info(f'player {player_name} became {ready} in lobby')

    def start(self) -> None:
        '''starts the game'''
        self._logger.info("GAME START")
        self.status = api_wrapper.GameStatus.GAME
        order = [p for p in self.players.keys()]
        self._turn_order = order
        self._active_player = 0
        self.turn_phase = api_wrapper.TurnPhase.CHOOSING_ACTION
        self._combat_substate = None
        self._pvp_sbs = None
        self.__init_shop()
        self.__init_deck()

    def _state_choosing_action(self, player: str, action: api_wrapper.PlayerActionChoice = None, item: int = None):
        if item != None:
            self._logger.info("pvp item placeholder")
            return
        player_obj = self.players[player]
        if action == api_wrapper.PlayerActionChoice.COINS:
            coins_event = CoinsEvent(game_id=self._id, player=player, amount=2)
            self._event_bus.emit(event=coins_event)
            player_obj.coins += coins_event.amount
            self._change_turn_phase(api_wrapper.TurnPhase.TURN_ENDED)
            self._logger.info(f'player {player} took coins')
        elif action == api_wrapper.PlayerActionChoice.SHOP:
            self._buy_item(player=player_obj)
        elif action == api_wrapper.PlayerActionChoice.COMBAT:
            if self._combat_substate:
                self._logger.error("tried to start combat but combat substate already exists")
                return
            if len(self.deck) < 3:
                self.__init_deck()
            monster_results = [self.deck[i] for i in range(3)]
            del self.deck[:3]
            combat_event = CombatEvent(game_id=self._id, monster_ids=[mon.name for mon in monster_results], info=[mon.get_api_status() for mon in monster_results])
            self._event_bus.emit(combat_event)
            self._combat_substate = self.NCombatSubstate(monsters=monster_results, player=player_obj)
            self._logger.info(f"combat started against {len(monster_results)} monsters")
            self._change_turn_phase(api_wrapper.TurnPhase.COMBAT_SELECT)
        else:
            self._logger.warning(f"invalid action {action}")

        return

    def _state_shopping(self, player: str, action: api_wrapper.PlayerActionChoice = None):
        player_obj = self.players[player]

        if action != api_wrapper.PlayerActionChoice.SHOP:
            self._logger.warning(f'player {player_obj.name} tried to do something other than buy an item after buying an item')
            return
        
        if len(player_obj.items) > 4:
            self._logger.info(f'player {player_obj.name} tried to buy an item but is holding too many')
            self._change_turn_phase(api_wrapper.TurnPhase.TURN_ENDED)
            return            
        self._buy_item(player=player_obj)

    def _state_combat_select(self, player: str, combat_action: api_wrapper.PlayerCombatChoice = None, monster_idx: int = None):
        if self._combat_substate == None:
            self._logger.error("combat state accessed without combat substate")
            return
        player_obj = self.players[player]
        if not (self._combat_substate.is_valid_player(player_obj)):
            self._logger.error(f"player {player} tried to take action out of turn")
            return
        if self._combat_substate.state != "selecting" or combat_action != api_wrapper.PlayerCombatChoice.SELECT:
            self._logger.error("player tried to select monster in wrong phase")
            return
    
        #TODO emit event
        monster = self._combat_substate.monsters[monster_idx]
        self._combat_substate.select_monster(monster_idx)
        self._change_turn_phase(api_wrapper.TurnPhase.COMBAT_ACTION)
        self._logger.info(f'{player} selected {monster.name}')


    def _state_combat_action(self, player: str, combat_action: api_wrapper.PlayerCombatChoice = None, monster_idx: int = None):
        if self._combat_substate == None:
            self._logger.error("combat state accessed without combat substate")
            return
        player_obj = self.players[player]
        if not (self._combat_substate.is_valid_player(player_obj)):
            self._logger.error(f"player {player} tried to take action out of turn")
            return
        if self._combat_substate.state != "deciding":
            self._logger.error("player tried to do combat action in wrong phase")
            return
        monster = self._combat_substate.monsters[monster_idx]

        if combat_action == api_wrapper.PlayerCombatChoice.FIGHT:
            self._change_turn_phase(api_wrapper.TurnPhase.COMBAT_FIGHT)
            self._combat_substate.state = "fighting"
            self._logger.info(f'player {player} chose to fight monster')
        elif combat_action == api_wrapper.PlayerCombatChoice.SPARE:
            roll, success = self._combat_substate.spare_monster()
            if success:
                self._logger.info(f'{player_obj.name} spared (rolled {roll})')
            else:
                self._logger.info(f'{player_obj.name} failed to spare (rolled {roll})')
            self._end_combat()
        elif combat_action == api_wrapper.PlayerCombatChoice.FLEE:
            new_phase = self._combat_substate.pass_monster()
            self._change_turn_phase(new_phase)
            self._logger.info(f'player {player} chose to flee/pass monster')
        else:
            self._logger.warning("player tried to do invalid combat action")
            return


    def _state_combat_fight(self, player: str, combat_action: api_wrapper.PlayerCombatChoice = None, monster_idx: int = None, item: int = None):
        if self._combat_substate == None:
            self._logger.error("combat state accessed without combat substate")
            return
        player_obj = self.players[player]
        if not (self._combat_substate.is_valid_player(player_obj)):
            self._logger.error(f"player {player} tried to take action out of turn")
            return
        
        if item != None:
            if item >= len(self._combat_substate.selected_items):
                self._logger.error(f'invalid item selection, combat state {self._combat_substate.selected_items}, {self._combat_substate.player.name}, {self._combat_substate.__class__.__name__}')
            self._combat_substate.selected_items[item] = not self._combat_substate.selected_items[item]
            self._logger.info(f'player {player} {"selected" if self._combat_substate.selected_items[item] else "unselected"} item {item}')
            return
        elif combat_action != api_wrapper.PlayerCombatChoice.FIGHT or self._combat_substate.selected_idx != monster_idx:
            self._logger.warning(f"player {player} tried to do invalid combat fight action")
            return

        mon = self._combat_substate.monsters[monster_idx]
        items = []
        for item_idx, selected in enumerate(self._combat_substate.selected_items):
            if not selected:
                continue
            items.append(item_idx)
            self._logger.info(f'{player_obj.name} used item on {mon.name}')
        player_obj.use_items(items, target=mon)
        
        if mon.health <= 0:
            player_obj.captured_stars.append(mon.stars)
            player_obj.coins += mon.fight_coins
            self._logger.info(f'{player_obj.name} killed {mon.name}')
            self._combat_substate.kill_monster()
        else:   
            self._logger.info(f'{player_obj.name} failed to kill {mon.name}')
            player_obj.health -= 1

        self._end_combat()



    def _state_fled(self, player: str, action: api_wrapper.PlayerActionChoice = None, combat_action: api_wrapper.PlayerCombatChoice = None, monster_idx: int = None):
        player_obj = self.players[player]

        if not self._combat_substate:
            self._logger.error("fled state accessed without combat substate")
            return
        

        if action == api_wrapper.PlayerActionChoice.SHOP:
            self._buy_item(player=player_obj)
        elif combat_action == api_wrapper.PlayerCombatChoice.SELECT:
            self._change_turn_phase(api_wrapper.TurnPhase.COMBAT_SELECT)
            self._state_combat_select(player, api_wrapper.PlayerCombatChoice.SELECT, monster_idx)
        else:
            self._logger.warning(f'player {player} tried to take invalid post-flee action')

    def _state_end_turn(self):
        if self.turn_phase != api_wrapper.TurnPhase.TURN_ENDED:
            self._logger.warning("tried to go to next turn but not in correct state")
            return
        if self._combat_substate: # cleanup combat if it exists, recalls end_turn
            self._end_combat()
        else:
            self.advance_active_player()
        

    def _buy_item(self, player: Player):
        if player.coins < 2:
            self._logger.info(f'player {player.name} tried to buy an item but does not have enough coins')
            return
        if len(player.items) > 4:
            self._logger.info(f'player {player.name} tried to buy an item but is holding too many')
            return    
        item = self.shop.pop(0)        
        shop_event = ShopEvent(game_id=self._id, item_id=item.name, item_uid=item.id, player_name=player.name)
        player.coins -= 2
        self._event_bus.emit(shop_event)
        if player.coins < 2:
            self._change_turn_phase(api_wrapper.TurnPhase.TURN_ENDED)
        else: 
            self._change_turn_phase(api_wrapper.TurnPhase.SHOPPING)
        #TODO Change
        player.items += [item]
        self._logger.info(f'player {player.name} bought item(s) {item.name}')


    def _end_combat(self):
        """End combat and check for leftover monsters"""
        if not self._combat_substate:
            self._logger.warning("end combat called with no combat subsytem")
            return
        if isinstance(self._combat_substate, self.NCombatSubstate):
            self.__end_normal_combat(self._combat_substate)
        else:
            self.__end_leftover_combat(self._combat_substate)
       

    def __end_normal_combat(self, combat: NCombatSubstate):
        if combat.has_leftover_monsters():
            self._change_turn_phase(api_wrapper.TurnPhase.COMBAT_SELECT)
            orig = combat.player.name
            self._combat_substate = self.LCombatSubstate(monsters=combat.leftover_queue, 
                                                            player=combat.player, 
                                                            order=[self.players[p] for p in self._turn_order if p != orig])
            self._logger.info(f'leftover monsters remain, entering leftover combat')
        else:
            self._combat_substate = None
            self._change_turn_phase(api_wrapper.TurnPhase.TURN_ENDED)
            self._state_end_turn()

    def __end_leftover_combat(self, combat: LCombatSubstate):
        if combat.is_finished():
            self._combat_substate = None
            self._change_turn_phase(api_wrapper.TurnPhase.TURN_ENDED)
            self._state_end_turn()
        else:
            self._change_turn_phase(api_wrapper.TurnPhase.COMBAT_SELECT)
            self._logger.info(f'leftover monsters remain, continuing leftover combat')

        

    def _state_pvp(self, player: str, action: api_wrapper.PlayerActionChoice = None, item_choice: int = None, player_target: str = None):
        pass



    def player_action(self, player: str, action: api_wrapper.PlayerActionChoice):

        if player not in self.players:
            self._logger.error(f'unregistered player {player} tried to take an action')
            return
        
        if player != self.get_active_player():
            self._logger.warning(f'player {player} tried to take action out of turn')
            return

        valid_states : dict[api_wrapper.TurnPhase, Callable[Any]]= {
            api_wrapper.TurnPhase.CHOOSING_ACTION: self._state_choosing_action,
            api_wrapper.TurnPhase.SHOPPING: self._state_shopping,
            api_wrapper.TurnPhase.FLED: self._state_fled,
        }

        if self.turn_phase not in valid_states:
            self._logger.warning(f'tried to do action {action.name} while in state {self.turn_phase.name}')
        
        if action == api_wrapper.PlayerActionChoice.END:
            self._change_turn_phase(api_wrapper.TurnPhase.TURN_ENDED)
        else:
            valid_states[self.turn_phase](player=player, action=action)

        if self.turn_phase == api_wrapper.TurnPhase.TURN_ENDED:
            self._state_end_turn()

    def player_select_item(self, player: str, choice: int):
        if player not in self.players:
            self._logger.error(f'unregistered player {player} tried to take an action')
            return

        valid_states = {
            api_wrapper.TurnPhase.CHOOSING_ACTION: self._state_choosing_action,
            api_wrapper.TurnPhase.COMBAT_FIGHT: self._state_combat_fight,
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

        valid_states = {
            api_wrapper.TurnPhase.PVP: self._state_pvp,
            api_wrapper.TurnPhase.COMBAT_FIGHT: self._state_combat_fight,
            api_wrapper.TurnPhase.COMBAT_ACTION: self._state_combat_action,
            api_wrapper.TurnPhase.COMBAT_SELECT: self._state_combat_select,
            api_wrapper.TurnPhase.FLED: self._state_fled,
        }

        if self.turn_phase not in valid_states:
            self._logger.warning(f'tried to select monster while in state {self.turn_phase.name}')
            return

        # Call appropriate state handler with monster_choice parameter
        valid_states[self.turn_phase](player=player, monster_idx=choice, combat_action=combat_action)

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
        self._change_turn_phase(api_wrapper.TurnPhase.CHOOSING_ACTION)

    def _change_turn_phase(self, new_phase: api_wrapper.TurnPhase):
        if not self.turn_phase or self.turn_phase != new_phase:
            self.turn_phase = new_phase
            #self._event_bus.emit(Event(type=EventType.TURN))
        

    def get_active_player(self) -> str | None:
        if self.status != api_wrapper.GameStatus.GAME:
            return None
        if self._combat_substate and isinstance(self._combat_substate, self.LCombatSubstate):
            return self._combat_substate.player.name
        
        return self._turn_order[self._active_player]
    
    def get_active_player_obj(self) -> Player:
        return self.players[self._turn_order[self._active_player]] if self.status == api_wrapper.GameStatus.GAME else None
    
    def get_selected_fight_items(self, player: str) -> list[bool]:
        """returns selected items for player"""
        if (not self._combat_substate) or (player != self._combat_substate.player.name):
            return [False]*len(self.players[player].items)
        else:
            return self._combat_substate.selected_items
    
    def __init_deck(self):
        self.deck = [Monster()]*40
        for i in range(40):
            if self._allowed_monsters == "*":
                mon_name = random.choice(list(MONSTER_REGISTRY.keys()))
            else:
                mon_name = random.choice(self._allowed_monsters)
            self.deck[i] = Monster.construct_from_id(mon_name)
        self._logger.info("intialized monster deck")
        
    def __init_shop(self):
        self.shop = [Item()]*40
        for i in range(40):
            if self._allowed_items == "*":
                item_name = random.choice(list(ITEM_REGISTRY.keys()))
            else:
                item_name = random.choice(self._allowed_items)
            self.shop[i] = Item.construct_from_id(item_name)
        self._logger.info("intialized item shop")

    def __del__(self):
        self._logger.critical("GAME CRASH")
    

    

