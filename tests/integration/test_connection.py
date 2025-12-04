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
