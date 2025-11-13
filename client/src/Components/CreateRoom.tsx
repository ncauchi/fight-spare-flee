import { useState } from "react";
import { usePlayerName } from "./NameContext";
import Form from "react-bootstrap/Form";
import Button from "react-bootstrap/Button";
import Stack from "react-bootstrap/Stack";
import { useNavigate } from "react-router-dom";

function CreateRoom() {
  const playerName = usePlayerName();
  const [lobbyName, setLobbyName] = useState("");
  const [isLoading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleCreate = async () => {
    if (!lobbyName) {
      alert("Please enter a name");
      return;
    }
    setLoading(true);
    const response = await fetch(`http://localhost:5000/games`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ name: lobbyName, owner: playerName }),
    });

    if (!response.ok) {
      const error = await response.json();
      console.error("Failed to create game:", error);
      alert(`Failed to create game: ${error.error || response.statusText}`);
      setLoading(false);
      return;
    }
    const data: { id: string } = await response.json();
    console.log("created game: " + data);
    navigate(`/play/${data.id}/lobby`);
  };

  const handleBack = () => {
    navigate("/");
  };

  return (
    <>
      <h1>Create Game</h1>
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
        <Button className="m-auto" onClick={isLoading ? () => {} : handleCreate} disabled={isLoading} variant="success">
          {isLoading ? "Starting..." : "Start Game"}
        </Button>
      </Stack>
    </>
  );
}

export default CreateRoom;
