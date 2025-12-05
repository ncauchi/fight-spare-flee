
import eventlet
eventlet.monkey_patch()

import pytest
import uuid
import threading
import requests_mock
from collections.abc import Generator, Callable
from typing import TypedDict

# Import after monkey patching
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'helpers'))

from game_manager import app, socketio, connections, games, game_locks, connections_lock, games_lock
from gamestate import GameState
from flask import Flask
from flask_socketio import SocketIO
from helpers.socketio_client import TestSocketIOClient


class GameDetails(TypedDict):
    game_id: str
    name: str
    owner: str
    max_players: int


@pytest.fixture(scope="function")
def clean_global_state() -> Generator[None, None, None]:
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

    with connections_lock:
        connections.clear()

    with games_lock:
        games.clear()
        game_locks.clear()


@pytest.fixture(scope="session")
def app_fixture() -> Flask:
    """
    Provides the Flask app instance.
    Session-scoped so it's shared across all tests.
    """
    app.config['TESTING'] = True
    return app


@pytest.fixture(scope="session")
def socketio_server() -> SocketIO:
    """
    Provides the SocketIO server instance.
    Session-scoped so it's shared across all tests.
    """
    return socketio


@pytest.fixture(scope="function")
def game_id() -> str:
    """
    Generates a unique game ID for each test.
    """
    return str(uuid.uuid4())


@pytest.fixture(scope="function")
def mock_lobby_api() -> Generator[requests_mock.Mocker, None, None]:
    """
    Mocks HTTP requests to the lobby service (localhost:5000).
    """
    with requests_mock.Mocker() as m:
        # Mock PUT requests to lobby service
        m.put(requests_mock.ANY, json={'success': True}, status_code=200)
        yield m


#Remove this BS slop
@pytest.fixture(scope="function")
def test_game(game_id: str, mock_lobby_api: requests_mock.Mocker, clean_global_state: None) -> GameDetails:
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
        games[game_id] = GameState(game_id, game_name, owner, max_players)
        game_locks[game_id] = threading.Lock()

    return {
        'game_id': game_id,
        'name': game_name,
        'owner': owner,
        'max_players': max_players
    }


@pytest.fixture(scope="session")
def server_thread(socketio_server: SocketIO) -> Generator[None, None, None]:
    """
    Runs the SocketIO server in a background thread for testing.
    Session-scoped so the server starts once and is shared by all tests.
    """
    import threading

    # Start server in background thread
    server_thread = threading.Thread(
        target=lambda: socketio_server.run(app, host='127.0.0.1', port=5001, debug=False, use_reloader=False, log_output=False),
        daemon=True
    )
    server_thread.start()

    # Wait for server to start
    eventlet.sleep(1.5)

    yield

    # Server will be killed when test session ends (daemon thread)


@pytest.fixture(scope="function")
def client_factory(server_thread: None) -> Generator[Callable[[], TestSocketIOClient], None, None]:
    """
    Factory fixture for creating multiple test clients.
    Handles cleanup of all created clients.
    Requires server_thread to be running.
    """
    clients: list[TestSocketIOClient] = []

    def _create_client() -> TestSocketIOClient:
        """Creates a new SocketIO test client."""
        client = TestSocketIOClient('http://127.0.0.1:5001')
        clients.append(client)
        return client

    yield _create_client

    # Cleanup: disconnect all clients
    for client in clients:
        if client.is_connected():
            client.disconnect()
