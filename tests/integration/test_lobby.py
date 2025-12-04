"""
Integration tests for lobby-related SocketIO events.

Tests JOIN, LOBBY_READY, and game room management.
"""
import pytest
import eventlet
from helpers.socketio_client import TestSocketIOClient


@pytest.mark.integration
def test_join_game_new_player(socketio_server, test_game, mock_lobby_api, clean_global_state):
    """
    Test that a new player can successfully join a game and receive INIT event.
    """
    from game_manager import connections, games

    game_id = test_game['game_id']
    player_name = "Alice"

    client = TestSocketIOClient('http://localhost:5001')
    client.connect()
    client.track_event('INIT')
    client.track_event('CHAT')

    # Emit JOIN event
    client.emit('JOIN', {'game_id': game_id, 'player_name': player_name})

    # Wait for INIT event (sent via background task with 0.2s delay)
    assert client.wait_for_event('INIT', timeout=1.0), "Should receive INIT event"

    # Verify INIT event data
    init_data = client.get_received('INIT')[0]
    assert 'game_name' in init_data
    assert 'owner' in init_data
    assert 'players' in init_data
    assert init_data['game_name'] == test_game['name']

    # Verify player was added to connections
    assert client.sid in connections
    assert connections[client.sid] == (player_name, game_id)

    # Verify player was added to game
    assert player_name in games[game_id].players
    assert games[game_id].players[player_name].name == player_name

    # Cleanup
    client.disconnect()


@pytest.mark.integration
def test_join_game_full_room(socketio_server, test_game, mock_lobby_api, clean_global_state):
    """
    Test that joining a full game disconnects the player.
    """
    from game_manager import games

    game_id = test_game['game_id']
    max_players = test_game['max_players']

    clients = []

    # Fill the game to capacity
    for i in range(max_players):
        client = TestSocketIOClient('http://localhost:5001')
        client.connect()
        client.track_event('INIT')
        client.emit('JOIN', {'game_id': game_id, 'player_name': f'Player{i}'})
        client.wait_for_event('INIT', timeout=1.0)
        clients.append(client)

    # Verify game is full
    assert len(games[game_id].players) == max_players

    # Try to join with one more player (should be rejected)
    overflow_client = TestSocketIOClient('http://localhost:5001')
    overflow_client.connect()
    overflow_client.track_event('INIT')

    overflow_client.emit('JOIN', {'game_id': game_id, 'player_name': 'OverflowPlayer'})

    # Wait a bit for processing
    eventlet.sleep(0.5)

    # The overflow player should be disconnected
    # Note: disconnect happens server-side, but client may not receive INIT
    init_events = overflow_client.get_received('INIT')
    assert len(init_events) == 0, "Overflow player should not receive INIT (disconnected)"

    # Verify game still has max_players
    assert len(games[game_id].players) == max_players

    # Cleanup
    for client in clients:
        client.disconnect()
    overflow_client.disconnect()


@pytest.mark.integration
def test_lobby_ready_updates_status(socketio_server, test_game, mock_lobby_api, clean_global_state):
    """
    Test that LOBBY_READY event updates player ready status and broadcasts PLAYERS event.
    """
    from game_manager import games

    game_id = test_game['game_id']
    player_name = "Bob"

    client = TestSocketIOClient('http://localhost:5001')
    client.connect()
    client.track_event('INIT')
    client.track_event('PLAYERS')

    # Join game
    client.emit('JOIN', {'game_id': game_id, 'player_name': player_name})
    client.wait_for_event('INIT', timeout=1.0)

    # Clear PLAYERS events from join
    client.clear_received('PLAYERS')

    # Set lobby ready to True
    client.emit('LOBBY_READY', {'ready': True})

    # Wait for PLAYERS event
    assert client.wait_for_event('PLAYERS', timeout=1.0), "Should receive PLAYERS event"

    # Verify player ready status was updated
    player = games[game_id].players[player_name]
    assert player.lobby_ready is True, "Player lobby_ready should be True"

    # Verify PLAYERS event contains updated status
    players_data = client.get_received('PLAYERS')[0]
    assert isinstance(players_data, list), "PLAYERS event should be a list"

    # Find our player in the list
    our_player_data = next((p for p in players_data if p['name'] == player_name), None)
    assert our_player_data is not None, "Our player should be in PLAYERS data"
    assert our_player_data['lobby_ready'] is True, "Player should show as ready in PLAYERS event"

    # Cleanup
    client.disconnect()


@pytest.mark.integration
def test_player_rejoin_kicks_old_session(socketio_server, test_game, mock_lobby_api, clean_global_state):
    """
    Test that a player rejoining with the same name kicks the old session.
    """
    from game_manager import connections, games

    game_id = test_game['game_id']
    player_name = "Charlie"

    # First connection
    client1 = TestSocketIOClient('http://localhost:5001')
    client1.connect()
    client1.track_event('INIT')
    client1.emit('JOIN', {'game_id': game_id, 'player_name': player_name})
    client1.wait_for_event('INIT', timeout=1.0)

    old_sid = client1.sid
    assert old_sid in connections, "First client should be in connections"

    # Wait a bit
    eventlet.sleep(0.2)

    # Second connection with same player name (rejoin)
    client2 = TestSocketIOClient('http://localhost:5001')
    client2.connect()
    client2.track_event('INIT')
    client2.emit('JOIN', {'game_id': game_id, 'player_name': player_name})
    client2.wait_for_event('INIT', timeout=1.0)

    new_sid = client2.sid
    eventlet.sleep(0.2)

    # Verify old session was removed from connections
    assert old_sid not in connections, "Old session should be removed from connections"

    # Verify new session is in connections
    assert new_sid in connections, "New session should be in connections"
    assert connections[new_sid] == (player_name, game_id)

    # Verify only one player entry in game (updated with new sid)
    player = games[game_id].players[player_name]
    assert player.sid == new_sid, "Player should have new session ID"

    # Cleanup
    client1.disconnect()
    client2.disconnect()
