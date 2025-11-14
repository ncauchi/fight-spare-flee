import { Form, Spinner, Stack, Button, ListGroup } from "react-bootstrap";
import { usePlayerName } from "./NameContext";
import { useGameState, type Player } from "./Game";
import { useSocketEmit } from "./SocketContext";
import { useGameSocket } from "./SocketContext";
import { useState, useEffect, useRef } from "react";
import PlayerBox from "./PlayerBox";

function Lobby() {
  const [ready, setReady] = useState(false);
  const gameState = useGameState();
  const [message, setMessage] = useState("");
  const { connected } = useGameSocket();
  const playerName = usePlayerName();
  const emit = useSocketEmit();
  const chatEndRef = useRef<HTMLDivElement>(null);

  const handleSendChat = () => {
    if (message) {
      emit("CHAT", playerName, message);
      setMessage("");
    }
  };

  const handleReady = () => {
    const new_ready = !ready;
    setReady(new_ready);
    emit("LOBBY_READY", new_ready);
  };

  const handleStartGame = () => {
    emit("START_GAME");
  };

  const createPlayerBox = (player: Player) => {
    if (!gameState) {
      return <div />;
    }
    return <PlayerBox player={player} />;
  };

  const createEmptyPlayerBox = (idx: number) => {
    if (!gameState) {
      return <div />;
    }
    return (
      <div key={idx} className="mb-2 lobby-player-box not-ready">
        Empty
      </div>
    );
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [gameState?.messages]);

  if (!connected || !gameState) return <Spinner></Spinner>;

  return (
    <>
      <Stack direction="horizontal" gap={4}>
        <Stack>
          <h1 className="mb-2">{gameState.game_name}</h1>
          <p className="mb-4">Connected: {connected ? "Yes" : "No"}</p>
          {gameState.players.map(createPlayerBox)}
          {[...Array(gameState.max_players - gameState.players.length).keys()].map(createEmptyPlayerBox)}
          <Button variant={ready ? "warning" : "success"} onClick={handleReady} className="mt-2">
            {ready ? "Unready" : "Ready"}
          </Button>
          {playerName == gameState.game_owner && gameState.players.every((p) => p.ready) && (
            <Button variant="success" onClick={handleStartGame} className="mt-2">
              Start Game
            </Button>
          )}
        </Stack>
        <Stack>
          <ListGroup className="overflow-y-auto overflow-x-hidden m-4 lobby-chat">
            {gameState.messages.map((message, index) => (
              <ListGroup.Item key={index}>
                {message.player == "SERVER123" ? gameState.game_name : message.player}
                {message.player == "SERVER123" && <span style={{ color: "#D2691E" }}>{"(Server)"}</span>}
                {message.player == gameState.game_owner && <span style={{ color: "blue" }}>{"(Owner)"}</span>}:{" "}
                {message.text}
              </ListGroup.Item>
            ))}
            <div ref={chatEndRef} />
          </ListGroup>
          <Stack direction="horizontal" gap={2} className="mx-4">
            <Form.Control
              type="text"
              placeholder="Send Message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  handleSendChat();
                }
              }}
            />
            <Button variant="primary" onClick={handleSendChat}>
              Send
            </Button>
          </Stack>
        </Stack>
      </Stack>
    </>
  );
}

export default Lobby;
