"""
Integration tests for SocketIO connection and disconnection handling.

Tests the connect/disconnect event handlers and cleanup logic.
"""
import pytest
import eventlet
from helpers.socketio_client import TestSocketIOClient


@pytest.mark.integration
def test_client_connect_success(socketio_server, clean_global_state):
    """
    Test that a client can successfully connect to the SocketIO server.
    """
    client = TestSocketIOClient('http://localhost:5001')

    # Connect to server
    client.connect()

    # Assert connection is established
    assert client.is_connected(), "Client should be connected"

    # Cleanup
    client.disconnect()


@pytest.mark.integration
def test_client_disconnect_cleanup(socketio_server, test_game, clean_global_state):
    """
    Test that disconnect properly cleans up player data from connections dict.
    """
    from game_manager import connections

    game_id = test_game['game_id']
    player_name = "TestPlayer"

    client = TestSocketIOClient('http://localhost:5001')
    client.connect()
    client.track_event('INIT')

    # Join game to get added to connections
    client.emit('JOIN', {'game_id': game_id, 'player_name': player_name})

    # Wait for JOIN to process
    eventlet.sleep(0.3)

    # Verify player was added to connections
    assert client.sid in connections, "Player should be in connections dict"
    assert connections[client.sid] == (player_name, game_id), "Connection data should match"

    # Disconnect
    client.disconnect()
    eventlet.sleep(0.2)

    # Verify cleanup happened
    assert client.sid not in connections, "Player should be removed from connections dict after disconnect"


@pytest.mark.integration
def test_multiple_clients_connect(socketio_server, clean_global_state):
    """
    Test that multiple clients can connect simultaneously.
    """
    clients = []

    # Connect 3 clients
    for i in range(3):
        client = TestSocketIOClient('http://localhost:5001')
        client.connect()
        clients.append(client)

    # Assert all connected
    for i, client in enumerate(clients):
        assert client.is_connected(), f"Client {i} should be connected"

    # Cleanup
    for client in clients:
        client.disconnect()
