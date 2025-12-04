"""
SocketIO test client wrapper for easier testing.

Provides event tracking, synchronous wait helpers, and clean connection management.
"""
import socketio
import eventlet
from typing import Dict, List, Any, Optional


class TestSocketIOClient:
    """
    Wrapper around python-socketio Client for testing.

    Features:
    - Automatic event tracking
    - Synchronous wait for events
    - Clean connection/disconnection
    - Helper methods for common operations
    """

    def __init__(self, server_url: str = 'http://localhost:5001'):
        """
        Initialize test client.

        Args:
            server_url: URL of the SocketIO server to connect to
        """
        self.server_url = server_url
        self.client = socketio.Client(engineio_logger=False, logger=False)
        self.received_events: Dict[str, List[Any]] = {}
        self._connected = False
        self._setup_default_handlers()

    def _setup_default_handlers(self):
        """Set up default event handlers for tracking."""
        @self.client.on('connect')
        def on_connect():
            self._connected = True

        @self.client.on('disconnect')
        def on_disconnect():
            self._connected = False

    def connect(self, auth: Optional[Dict] = None):
        """
        Connect to the SocketIO server.

        Args:
            auth: Optional authentication data
        """
        self.client.connect(
            self.server_url,
            auth=auth,
            transports=['websocket']
        )
        # Wait for connection to establish
        eventlet.sleep(0.05)

    def disconnect(self):
        """Disconnect from the SocketIO server."""
        if self._connected:
            self.client.disconnect()
            eventlet.sleep(0.05)

    def is_connected(self) -> bool:
        """Check if client is currently connected."""
        return self._connected

    def on(self, event_name: str):
        """
        Register an event handler that tracks received events.

        Args:
            event_name: Name of the event to listen for

        Returns:
            Decorator function

        Example:
            @client.on('CHAT')
            def handle_chat(data):
                print(f"Received: {data}")
        """
        def decorator(func):
            @self.client.on(event_name)
            def handler(data):
                # Track the event
                if event_name not in self.received_events:
                    self.received_events[event_name] = []
                self.received_events[event_name].append(data)
                # Call the original handler
                return func(data)
            return handler
        return decorator

    def track_event(self, event_name: str):
        """
        Start tracking an event without a custom handler.

        Args:
            event_name: Name of the event to track

        Example:
            client.track_event('PLAYERS')
            # Later: events = client.get_received('PLAYERS')
        """
        if event_name not in self.received_events:
            self.received_events[event_name] = []

        @self.client.on(event_name)
        def handler(data):
            self.received_events[event_name].append(data)

    def emit(self, event_name: str, data: Any = None):
        """
        Emit an event to the server.

        Args:
            event_name: Name of the event
            data: Data to send with the event
        """
        self.client.emit(event_name, data)

    def get_received(self, event_name: str) -> List[Any]:
        """
        Get all received events of a specific type.

        Args:
            event_name: Name of the event

        Returns:
            List of received event data (empty list if none received)
        """
        return self.received_events.get(event_name, [])

    def wait_for_event(self, event_name: str, timeout: float = 2.0, count: int = 1) -> bool:
        """
        Wait for a specific event to be received.

        Args:
            event_name: Name of the event to wait for
            timeout: Maximum time to wait in seconds
            count: Number of events to wait for

        Returns:
            True if event(s) received, False if timeout

        Example:
            client.track_event('INIT')
            client.emit('JOIN', {'game_id': '123', 'player_name': 'Alice'})
            if client.wait_for_event('INIT'):
                init_data = client.get_received('INIT')[0]
        """
        elapsed = 0.0
        interval = 0.05

        while elapsed < timeout:
            if event_name in self.received_events:
                if len(self.received_events[event_name]) >= count:
                    return True
            eventlet.sleep(interval)
            elapsed += interval

        return False

    def clear_received(self, event_name: Optional[str] = None):
        """
        Clear tracked events.

        Args:
            event_name: Specific event to clear, or None to clear all
        """
        if event_name:
            self.received_events[event_name] = []
        else:
            self.received_events.clear()

    @property
    def sid(self) -> str:
        """Get the session ID of this client."""
        return self.client.sid
