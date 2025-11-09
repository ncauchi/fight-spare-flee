import { useNavigate } from "react-router-dom";
import Button from "react-bootstrap/Button";
import Stack from "react-bootstrap/Stack";

function ServerBrowser() {
  const navigate = useNavigate();

  interface Room {
    id: string;
    name: string;
    owner: string;
    players: number;
    maxPlayers: number;
  }
  // TODO: Fetch available rooms from server
  const rooms: Room[] = [
    { id: "room1", name: "Room 1", owner: "bob", players: 2, maxPlayers: 4 },
    { id: "room2", name: "Room 2", owner: "n", players: 1, maxPlayers: 4 },
  ];

  const handleJoinRoom = (roomId: string) => {
    // TODO: Implement join room logic
    navigate("/play");
  };

  const handleBack = () => {
    navigate("/");
  };

  const createRoom = (room: Room) => {
    return (
      <Stack direction="horizontal" className="server-browser-row" gap={3}>
        <h2 className="m-auto">{room.name}</h2>
        <div className="vr" />
        <h3 className="m-auto">
          {room.players}/{room.maxPlayers}
        </h3>
        <p className="m-auto">{room.id}</p>
        <p className="m-auto">{room.owner}</p>
        <Button onClick={() => handleJoinRoom(room.id)} variant="success" className="m-auto">
          Join
        </Button>
      </Stack>
    );
  };

  return (
    <>
      <Stack direction="horizontal" gap={3} className="mb-4">
        <Button onClick={handleBack} variant="primary">
          Back
        </Button>
        <h1>Server Browser</h1>
      </Stack>

      <Stack gap={3} className="server-browser">
        {rooms.map(createRoom)}
      </Stack>
    </>
  );
}

export default ServerBrowser;
