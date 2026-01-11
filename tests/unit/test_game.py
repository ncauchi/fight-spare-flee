import pytest
from gamestate import GameState
from api_wrapper import *

@pytest.mark.unit
def test_lobby():
    game = GameState("123", "test", "god", "4")
    game.add_player("bob", "aaa")
    game.add_player("god", "bbb")
    game.set_player_lobby_ready("bob", True)
    

    players = game.get_status_players()
    lobby = game.get_status_lobby()

    assert len(players) == 2
    assert players[0] == PlayerInfo(name='bob', ready=True, coins=0, num_items=0, health=4)
    assert players[1] == PlayerInfo(name='god', ready=False, coins=0, num_items=0, health=4)
    assert lobby == {'num_players': 2, 'status': 'LOBBY'}

    game.start()

    lobby = game.get_status_lobby()
    first_player = game.get_active_player()

    assert lobby == {'num_players': 2, 'status': 'GAME'}
    assert first_player == "bob"

@pytest.mark.unit
def test_game():
    game = GameState("123", "test", "god", "4")
    game.add_player("bob", "aaa")
    game.add_player("god", "bbb")
    game.start()

    assert game.active_player_take_coins() == 2
    game.advance_active_player()
    game.active_player_take_coins()
    game.advance_active_player()
    item = game.active_player_buy_item()
    assert item != None

    players = game.get_status_players()
    assert game.get_active_player() == "bob"
    assert game.get_active_player_obj().get_status_hand() == [ItemInfo(name="dev_item", text="jajaja 5dmg", target_type=ItemTarget.MONSTER)]
    assert players[0] == PlayerInfo(name='bob', captured_stars=[], ready=False, coins=0, num_items=1, health=4)
    assert players[1] == PlayerInfo(name='god',  captured_stars=[], ready=False, coins=2, num_items=0, health=4)

    game.advance_active_player()
    game.advance_active_player()
    game.active_player_fsf()
    monsters = game.get_status_fsf()

    assert game.get_active_player() == "bob"
    assert len(monsters) == 3
    assert monsters == [MonsterInfo(stars=1)]*3

    game.fsf_select(0)
    game.fsf_fight(0, 0)
    players = game.get_status_players()
    monsters = game.get_status_fsf()

    assert players[0] == PlayerInfo(name='bob', captured_stars=[1], ready=False, coins=3, num_items=0, health=4)
    assert players[1] == PlayerInfo(name='god',  captured_stars=[], ready=False, coins=2, num_items=0, health=4)
    assert game.fsf_monsters == []

    game.advance_active_player()
    assert game.get_active_player() == "god"
    game.active_player_fsf()
    monsters = game.get_status_fsf()
    game.fsf_select(0)
    game.fsf_fight(1, -1)
    players = game.get_status_players()

    assert players[0] == PlayerInfo(name='bob', captured_stars=[1], ready=False, coins=3, num_items=0, health=4)
    assert players[1] == PlayerInfo(name='god',  captured_stars=[], ready=False, coins=2, num_items=0, health=3)

    

    

    

