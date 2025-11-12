import { useNavigate } from "react-router-dom";
import { useState, useEffect, useRef } from "react";
import { useParams } from "react-router";
import Button from "react-bootstrap/Button";
import Stack from "react-bootstrap/Stack";
import Spinner from "react-bootstrap/Spinner";
import ListGroup from "react-bootstrap/ListGroup";
import { usePlayerName } from "./NameContext";

//const GAME_API = `http://localhost:5001`;

interface Message {
  player: string;
  text: string;
}

function Lobby() {
  let { gameId } = useParams();

  const socketRef = useRef<WebSocket>(null);
  const playerName = usePlayerName();
  const [messages, setMessages] = useState<Message[]>([]);

  const handleChat = (player: string, msg: string) => {
    setMessages((prev) => [...prev, { player: player, text: msg }]);
  };

  const handleSendChat = (msg: string) => {
    socketRef.current?.send(JSON.stringify({ type: "CHAT", player: playerName, message: msg }));
  };

  useEffect(() => {
    const socket = new WebSocket(`ws://localhost:5001/ws/${gameId}/${playerName}`);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log("Successfully Joined Game: ", gameId);
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type == "CHAT") {
        handleChat(data.player, data.message);
      } else if (data.type == "ERROR") {
        console.error("Server error:", data.message);
        alert(`Connection error: ${data.message}`);
      } else {
        console.log("Message from server", data.type, data.message);
      }
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    socket.onclose = (event) => {
      console.log("WebSocket closed:", event.code, event.reason);
    };

    // Cleanup function to close socket when component unmounts
    return () => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    };
  }, [gameId, playerName]);

  return (
    <>
      <h1>Hellow World!</h1>
      <ListGroup>
        {messages.map((message, index) => (
          <ListGroup.Item key={index}>
            {message.player}: {message.text}
          </ListGroup.Item>
        ))}
      </ListGroup>
      <Button variant="primary" className="me-2" size="lg" onClick={() => handleSendChat("Hello")}>
        Send
      </Button>
    </>
  );

  /*export function useGameSocket(gameId, playerName) {
  
  
  const socketRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const [gameState, setGameState] = useState(null);
  const [playerId, setPlayerId] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Create socket connection
    socketRef.current = io(SOCKET_URL, {
      transports: ['websocket', 'polling']
    });

    const socket = socketRef.current;

    // Connection events
    socket.on('connect', () => {
      console.log('Connected to server');
      setConnected(true);
      
      // Join game after connection
      if (gameId && playerName) {
        socket.emit('join_game', { gameId, playerName });
      }
    });

    socket.on('disconnect', () => {
      console.log('Disconnected from server');
      setConnected(false);
    });

    socket.on('connected', (data) => {
      setPlayerId(data.clientId);
    });

    // Game events
    socket.on('game_joined', (data) => {
      console.log('Joined game:', data);
      setPlayerId(data.playerId);
      setGameState(data.gameState);
    });

    socket.on('join_error', (data) => {
      console.error('Join error:', data.message);
      setError(data.message);
    });

    socket.on('player_joined', (data) => {
      console.log('Player joined:', data);
      setGameState(data.gameState);
    });

    socket.on('player_left', (data) => {
      console.log('Player left:', data);
      setGameState(data.gameState);
    });

    socket.on('player_ready_update', (data) => {
      console.log('Player ready update:', data);
      setGameState(data.gameState);
    });

    socket.on('game_started', (data) => {
      console.log('Game started!');
      setGameState(data.gameState);
    });

    socket.on('game_update', (data) => {
      console.log('Game update:', data);
      setGameState(data.gameState);
    });

    // Cleanup on unmount
    return () => {
      if (socket.connected) {
        socket.emit('leave_game', { gameId });
        socket.disconnect();
      }
    };
  }, [gameId, playerName]);

  // Actions
  const sendAction = (action) => {
    if (socketRef.current && connected) {
      socketRef.current.emit('game_action', { gameId, action });
    }
  };

  const setReady = () => {
    if (socketRef.current && connected) {
      socketRef.current.emit('player_ready', { gameId });
    }
  };

  const leaveGame = () => {
    if (socketRef.current && connected) {
      socketRef.current.emit('leave_game', { gameId });
    }
  };

  return {
    connected,
    gameState,
    playerId,
    error,
    sendAction,
    setReady,
    leaveGame
  };
}


  const playerName = usePlayerName();
  const navigate = useNavigate();
  let { gameId } = useParams();
  const [room, setRoom] = useState<Room | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const roomAPI = `http://localhost:5000/rooms/${gameId}`;

  const fetchRoom = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(roomAPI);

      if (!response.ok) {
        throw new Error(`Failed to fetch room: ${response.statusText}`);
      }

      const data = await response.json();
      setRoom(data);
    } catch (err) {
      console.error("Error fetching room:", err);
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
      console.log(`Loaded room: ${room}`);
    }
  };

  useEffect(() => {
    fetchRoom();
  }, [gameId]);

  const handleLeave = async () => {
    const response = await fetch(`http://localhost:5000/rooms/${gameId}/leave`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ playerName: playerName }),
    });

    if (!response.ok) {
      const error = await response.json();
      console.error("Failed to leave room:", error);
      alert(`Failed to leave room: ${error.error || response.statusText}`);
      return;
    }

    navigate("/browse");
  };

  const handleStartGame = () => {
    // TODO: Implement start game logic
    navigate("/play");
  };

  if (loading) {
    return (
      <div className="text-center">
        <Spinner animation="border" role="status">
          <span className="visually-hidden">Loading...</span>
        </Spinner>
      </div>
    );
  }

  if (error || !room) {
    return (
      <Stack gap={3}>
        <h1>Error</h1>
        <p>{error || "Room not found"}</p>
        <Button
          onClick={() => {
            navigate("/browse");
          }}
          variant="primary"
        >
          Back to Server Browser
        </Button>
      </Stack>
    );
  }

  return (
    <>
      <h1>{room.name}</h1>
      <p>Room ID: {gameId}</p>

      <h3 className="mt-4">Players</h3>
      <ListGroup>
        {room.players.map((player) => (
          <ListGroup.Item key={player}>
            {player} {player === room.owner && "(Owner)"}
          </ListGroup.Item>
        ))}
      </ListGroup>

      <Stack direction="horizontal" gap={3} className="mt-4">
        <Button className="m-auto" onClick={fetchRoom} variant="secondary">
          Refresh
        </Button>
        {room.players.length >= 2 && (
          <Button className="m-auto" onClick={handleStartGame} variant="success">
            Start Game
          </Button>
        )}
        <Button className="m-auto" onClick={handleLeave} variant="danger">
          Leave
        </Button>
      </Stack>
    </>
  );*/
}

export default Lobby;
