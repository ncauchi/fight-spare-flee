import "./Board.css";
import ChatWindow from "./ChatWindow";
import { type GameState } from "./Game";
import { useGameState } from "./Game";
import { Spinner, Button } from "react-bootstrap";
import { useState } from "react";

function Board() {
  const gameState = useGameState();
  const [flipped, setFlipped] = useState(false);

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
      <div className="player-container position">
        <div className="player-container container">
          <div className="point" />
        </div>
      </div>
    </div>
  );
}

export default Board;
