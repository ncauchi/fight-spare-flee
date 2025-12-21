import { Spinner, Stack, Button } from "react-bootstrap";
import { usePlayerName } from "./NameContext";
import { useGameState, useAPI } from "./Game";
import { useState } from "react";
import PlayerBox from "./PlayerBox";
import ChatWindow from "./ChatWindow";
import { type PlayerInfo } from "../api_wrapper";

function Lobby() {
  const [ready, setReady] = useState(false);
  const gameState = useGameState();
  const playerName = usePlayerName();
  const api = useAPI();

  if (!gameState || !gameState.connected || !api) {
    console.log("GameState:", gameState);
    console.log("API obj: ", api);
    return <Spinner></Spinner>;
  }

  const handleReady = () => {
    const new_ready = !ready;
    setReady(new_ready);
    api.requestSetLobbyReady(new_ready);
  };

  const handleStartGame = () => {
    api.requestStartGame();
  };

  const createPlayerBox = (player: PlayerInfo, idx: number) => {
    if (!gameState) {
      return <div />;
    }
    return <PlayerBox key={idx} player={player} />;
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

  return (
    <>
      <h1 className="mb-2">{gameState.game_name}</h1>
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
