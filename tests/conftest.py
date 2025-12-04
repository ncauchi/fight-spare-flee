"""
Core test fixtures and configuration for Flask-SocketIO testing.

CRITICAL: eventlet.monkey_patch() must be called BEFORE any other imports
to ensure proper async behavior and threading compatibility.
"""
import eventlet
eventlet.monkey_patch()

import pytest
import uuid
import threading
import requests_mock

# Import after monkey patching
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from game_manager import app, socketio, connections, games, game_locks, connections_lock, games_lock
from gamestate import GameState


@pytest.fixture(scope="function")
def clean_global_state():
    """
    Clears all global state before and after each test.
    Critical for test isolation.
    """
    # Clear before test
    with connections_lock:
        connections.clear()

    with games_lock:
        games.clear()
        game_locks.clear()

    yield

    # Clear after test
    with connections_lock:
        connections.clear()

    with games_lock:
        games.clear()
        game_locks.clear()


@pytest.fixture(scope="function")
def app_fixture(clean_global_state):
    """
    Provides a fresh Flask app instance with cleaned state.
    """
    app.config['TESTING'] = True
    return app


@pytest.fixture(scope="function")
def socketio_server(app_fixture):
    """
    Provides the SocketIO server instance with cleaned state.
    """
    return socketio


@pytest.fixture(scope="function")
def game_id():
    """
    Generates a unique game ID for each test.
    """
    return str(uuid.uuid4())


@pytest.fixture(scope="function")
def mock_lobby_api():
    """
    Mocks HTTP requests to the lobby service (localhost:5000).
    """
    with requests_mock.Mocker() as m:
        # Mock PUT requests to lobby service
        m.put(requests_mock.ANY, json={'success': True}, status_code=200)
        yield m


@pytest.fixture(scope="function")
def test_game(game_id, mock_lobby_api, clean_global_state):
    """
    Creates a pre-configured test game via the /internal endpoint.

    Returns:
        dict: Game details including game_id, name, owner, and max_players
    """
    game_name = "Test Game"
    owner = "TestOwner"
    max_players = 4

    # Create game directly by initializing GameState and locks
    with games_lock:
        games[game_id] = GameState(game_name, owner, max_players)
        game_locks[game_id] = threading.Lock()

    return {
        'game_id': game_id,
        'name': game_name,
        'owner': owner,
        'max_players': max_players
    }


@pytest.fixture(scope="function")
def client_factory(socketio_server):
    """
    Factory fixture for creating multiple test clients.
    Handles cleanup of all created clients.
    """
    clients = []

    def _create_client():
        """Creates a new SocketIO test client."""
        from helpers.socketio_client import TestSocketIOClient
        client = TestSocketIOClient('http://localhost:5001')
        clients.append(client)
        return client

    yield _create_client

    # Cleanup: disconnect all clients
    for client in clients:
        if client.is_connected():
            client.disconnect()
