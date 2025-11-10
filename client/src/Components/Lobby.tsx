import { useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { useParams } from "react-router";
import Button from "react-bootstrap/Button";
import Stack from "react-bootstrap/Stack";
import Spinner from "react-bootstrap/Spinner";
import ListGroup from "react-bootstrap/ListGroup";
import { usePlayerName } from "./NameContext";

interface Room {
  id: string;
  name: string;
  owner: string;
  players: string[];
  maxPlayers: number;
}

function Lobby() {
  const playerName = usePlayerName();
  const navigate = useNavigate();
  let { roomId } = useParams();
  const [room, setRoom] = useState<Room | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const roomAPI = `http://localhost:5000/rooms/${roomId}`;

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
  }, [roomId]);

  const handleLeave = async () => {
    const response = await fetch(`http://localhost:5000/rooms/${roomId}/leave`, {
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
      <p>Room ID: {roomId}</p>

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
  );
}

export default Lobby;
