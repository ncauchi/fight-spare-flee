"""
Integration tests for SocketIO connection and disconnection handling.

Tests the connect/disconnect event handlers and cleanup logic.
"""
import pytest
import eventlet
from helpers.socketio_client import TestSocketIOClient


@pytest.mark.integration
def test_client_connect_success(client_factory, clean_global_state):
    """
    Test that a client can successfully connect to the SocketIO server.
    """
    client = client_factory()

    # Connect to server
    client.connect()

    # Assert connection is established
    assert client.is_connected(), "Client should be connected"

    # Cleanup
    client.disconnect()


@pytest.mark.integration
def test_client_disconnect_cleanup(client_factory, test_game, clean_global_state):
    """
    Test that disconnect properly cleans up player data from connections dict.
    """
    from game_manager import connections, games

    game_id = test_game['game_id']
    player_name = "TestPlayer"

    client = client_factory()
    client.connect()
    client.track_event('INIT')

    # Join game to get added to connections
    client.emit('JOIN', game_id, player_name)

    # Wait for JOIN to process
    eventlet.sleep(0.3)

    # Verify player was added to connections by checking the game players dict
    # (Note: client SID and server SID may differ)
    assert player_name in games[game_id].players, "Player should be in game.players dict"

    # Verify player is in connections (check by value, not key)
    player_in_connections = any(name == player_name and gid == game_id
                                for name, gid in connections.values())
    assert player_in_connections, "Player should be in connections dict"

    # Disconnect
    client.disconnect()
    eventlet.sleep(0.2)

    # Verify cleanup happened
    player_in_connections_after = any(name == player_name and gid == game_id
                                      for name, gid in connections.values())
    assert not player_in_connections_after, "Player should be removed from connections dict after disconnect"


@pytest.mark.integration
def test_multiple_clients_connect(client_factory, clean_global_state):
    """
    Test that multiple clients can connect simultaneously.
    """
    clients = []

    # Connect 3 clients
    for i in range(3):
        client = client_factory()
        client.connect()
        clients.append(client)

    # Assert all connected
    for i, client in enumerate(clients):
        assert client.is_connected(), f"Client {i} should be connected"

    # Cleanup
    for client in clients:
        client.disconnect()

@pytest.mark.integration
def test_client_join(client_factory, test_game, clean_global_state):


    client : TestSocketIOClient = client_factory()
    game_id = test_game['game_id']
    player_name = "test_player"

    expected_output = {
        "game_name": test_game["name"],
        "game_owner": test_game["owner"],
        "max_players": 4,
        "players": [{'name': player_name, 'ready': False}],
        "messages": [{'player': 'SERVER123', 'text': 'Welcome to the game'}],
    }

    client.track_event('INIT')

    client.connect()
    client.emit('JOIN', game_id, player_name)

    eventlet.sleep(0.3)

    init_events = client.get_received("INIT")

    assert client.is_connected(), "Client should be connected"
    assert len(init_events) == 1
    assert init_events[0] == expected_output

@pytest.mark.integration
def test_normal_run(client_factory, test_game, clean_global_state):


    client : TestSocketIOClient = client_factory()
    client_two : TestSocketIOClient = client_factory()
    game_id = test_game['game_id']
    player_name = "test_player"
    second_player_name = test_game["owner"]

    expected_init = {
        "game_name": test_game["name"],
        "game_owner": test_game["owner"],
        "max_players": 4,
        "players": [{'name': second_player_name, 'ready': True}, {'name': player_name, 'ready': False}],
        "messages": [{'player': 'SERVER123', 'text': 'Welcome to the game'}],
    }

    expected_players = [[{'name': second_player_name, 'ready': True, 'coins': 0, 'num_items': 0, 'health': 4}, 
                        {'name': player_name, 'ready': False, 'coins': 0, 'num_items': 0, 'health': 4}],
                        [{'name': second_player_name, 'ready': True, 'coins': 0, 'num_items': 0, 'health': 4}, 
                        {'name': player_name, 'ready': True, 'coins': 0, 'num_items': 0, 'health': 4}]]

    expected_start_game = second_player_name

    expected_turn = ['test_player', 'TestOwner']

    client.track_event('INIT')
    client.track_event('PLAYERS')
    client.track_event('START_GAME')
    client.track_event('CHANGE_TURN')
    
    
    client_two.connect()
    client_two.emit('JOIN', game_id, second_player_name)

    client.connect()
    client.emit('JOIN', game_id, player_name)
    eventlet.sleep(0.1)
    client_two.emit('LOBBY_READY', True)
    eventlet.sleep(0.1)
    client.emit('LOBBY_READY', True)
    eventlet.sleep(0.1)
    client_two.emit('START_GAME')

    eventlet.sleep(0.3)

    client.emit('END_TURN')
    client_two.emit('END_TURN')

    eventlet.sleep(0.3)



    init_events = client.get_received("INIT")
    players_events = client.get_received("PLAYERS")
    start_events = client.get_received("START_GAME")
    turn_events = client.get_received("CHANGE_TURN")
    
    assert len(init_events) == 1
    assert len(start_events) == 1
    assert init_events[0] == expected_init
    assert players_events == expected_players
    assert start_events[0] == expected_start_game
    assert turn_events == expected_turn


