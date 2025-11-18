import "./Board.css";
import ChatWindow from "./ChatWindow";
import { type GameState, type Player } from "./Game";
import { useGameState } from "./Game";
import { Spinner, Button } from "react-bootstrap";
import { useState } from "react";
import BoardPlayerBox from "./BoardPlayerBox";
import { usePlayerName } from "./NameContext";

function Board() {
  const gameState = useGameState();
  const [flipped, setFlipped] = useState(false);
  const playerName = usePlayerName();
  const opponents = gameState?.players.filter((p) => {
    return p.name != playerName;
  });

  const handleFlip = () => {
    setFlipped(!flipped);
  };

  if (!gameState) return <Spinner></Spinner>;
  return (
    <div className="game-board">
      <Button variant="primary" onClick={handleFlip}>
        Flip
      </Button>
      <div className={`card ${flipped ? "flipped" : ""}`}>
        <div className="card-back" />
        <div className="card-front" />
      </div>
      <div className="game-chat">
        <ChatWindow gameName={gameState?.game_name} gameOwner={gameState.game_owner} messages={gameState.messages} />
      </div>
      {opponents?.map((p, i) => (
        <BoardPlayerBox key={i} player={p} index={i} numPlayers={opponents.length} />
      ))}
    </div>
  );
}

export default Board;
