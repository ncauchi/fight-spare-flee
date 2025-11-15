import { Spinner, Stack, Button } from "react-bootstrap";
import { usePlayerName } from "./NameContext";
import { useGameState, type Player } from "./Game";
import { useSocketEmit } from "./SocketContext";
import { useGameSocket } from "./SocketContext";
import { useState } from "react";
import PlayerBox from "./PlayerBox";
import ChatWindow from "./ChatWindow";

function Lobby() {
  const [ready, setReady] = useState(false);
  const gameState = useGameState();
  const { connected } = useGameSocket();
  const playerName = usePlayerName();
  const emit = useSocketEmit();

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

  if (!connected || !gameState) return <Spinner></Spinner>;

  return (
    <>
      <h1 className="mb-2">{gameState.game_name}</h1>
      <p className="mb-4">Connected: {connected ? "Yes" : "No"}</p>
      <Stack direction="horizontal" gap={4}>
        <Stack className="my-auto">
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
        <ChatWindow gameName={gameState.game_name} gameOwner={gameState.game_owner} messages={gameState.messages} />
      </Stack>
    </>
  );
}

export default Lobby;
