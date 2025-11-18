import "./Board.css";
import ChatWindow from "./ChatWindow";
import { type GameState, type Player } from "./Game";
import { useGameState } from "./Game";
import { Spinner, Button, Stack } from "react-bootstrap";
import { useState } from "react";
import BoardPlayerBox from "./BoardPlayerBox";
import { usePlayerName } from "./NameContext";
import ItemCard from "./ItemCard";
import { useSocketEmit } from "./SocketContext";

function Board() {
  const gameState = useGameState();
  const [flipped, setFlipped] = useState(false);
  const playerName = usePlayerName();
  const opponents = gameState?.players.filter((p) => {
    return p.name != playerName;
  });
  const myTurn = gameState?.active_player === playerName;
  const emit = useSocketEmit();

  const handleFlip = () => {
    setFlipped(!flipped);
  };

  const handleNextTurn = () => {
    emit("END_TURN");
  };

  if (!gameState) return <Spinner></Spinner>;
  return (
    <div className="game-board">
      <div className={`card ${flipped ? "flipped" : ""}`}>
        <div className="card-back" />
        <div className="card-front" />
      </div>
      <div className="game-chat">
        <ChatWindow gameName={gameState?.game_name} gameOwner={gameState.game_owner} messages={gameState.messages} />
      </div>
      {opponents?.map((p, i) => (
        <BoardPlayerBox
          key={i}
          player={p}
          index={i}
          numPlayers={opponents.length}
          active={gameState.active_player === p.name}
        />
      ))}
      {myTurn && (
        <Button variant="primary" className={"next-turn-button"} onClick={handleNextTurn}>
          <h3>Next Turn</h3>
        </Button>
      )}
      <Stack direction="horizontal" gap={1} className="item-card-box">
        <ItemCard />
        <ItemCard />
      </Stack>
    </div>
  );
}

export default Board;
