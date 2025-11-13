import Button from "react-bootstrap/Button";
import Stack from "react-bootstrap/Stack";
import Spinner from "react-bootstrap/Spinner";
import ListGroup from "react-bootstrap/ListGroup";
import { usePlayerName } from "./NameContext";
import { useGameState } from "./Game";
import { useSocketEmit } from "./SocketContext";
import { useGameSocket } from "./SocketContext";

function Lobby() {
  const gameState = useGameState();
  const { connected } = useGameSocket();
  const playerName = usePlayerName();
  const emit = useSocketEmit();

  const handleSendChat = (msg: string) => {
    emit("CHAT", playerName, msg);
  };

  return (
    <>
      <h1>Hello World!</h1>
      <p>Connected: {connected ? "Yes" : "No"}</p>
      <ListGroup>
        {gameState.messages.map((message, index) => (
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
}

export default Lobby;
