import { useState } from "react";
import { usePlayerName } from "./NameContext";
import Form from "react-bootstrap/Form";
import Button from "react-bootstrap/Button";
import Stack from "react-bootstrap/Stack";
import { useNavigate } from "react-router-dom";

function CreateRoom() {
  const playerName = usePlayerName();
  const [lobbyName, setLobbyName] = useState("");
  const navigate = useNavigate();

  const handleCreate = async () => {
    if (!lobbyName) {
      alert("Please enter a name");
      return;
    }

    const response = await fetch(`http://localhost:5000/rooms`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ name: lobbyName, owner: playerName }),
    });

    if (!response.ok) {
      const error = await response.json();
      console.error("Failed to create room:", error);
      alert(`Failed to create room: ${error.error || response.statusText}`);
      return;
    }
    const data: { id: string } = await response.json();
    console.log(data);
    navigate(`/lobby/${data.id}`);
  };

  const handleBack = () => {
    navigate("/");
  };

  return (
    <>
      <h1>Create Room</h1>
      <Form.Group className="name-input-group">
        <Form.Control
          size="lg"
          type="text"
          placeholder="Lobby Name"
          value={lobbyName}
          onChange={(e) => setLobbyName(e.target.value)}
        />
      </Form.Group>
      <Stack direction="horizontal" className="mt-4">
        <Button className="m-auto" onClick={handleBack} variant="secondary">
          Back
        </Button>
        <Button className="m-auto" onClick={handleCreate} variant="success">
          Start Game
        </Button>
      </Stack>
    </>
  );
}

export default CreateRoom;
