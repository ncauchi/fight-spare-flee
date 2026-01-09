import "./Board.css";
import ChatWindow from "./ChatWindow";
import { type GameState, useGameState, useAPI } from "./Game";
import { Spinner, Button, Stack } from "react-bootstrap";
import { useState } from "react";
import BoardPlayerBox from "./BoardPlayerBox";
import { usePlayerName } from "./NameContext";
import ChoosingActionBox from "./ChoosingActionBox";
import BoardPlayerHand from "./BoardPlayerHand";

function Board() {
  const gameState = useGameState();
  const api = useAPI();

  if (!api || !gameState) {
    return <Spinner></Spinner>;
  }

  const [flipped, setFlipped] = useState(false);
  const playerName = usePlayerName();
  const opponents = gameState?.players.filter((p) => {
    return p.name != playerName;
  });
  const myTurn = gameState?.active_player === playerName;

  const handleFlip = () => {
    setFlipped(!flipped);
  };

  const handleNextTurn = () => {
    api.requestEndTurn();
  };

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
      <BoardPlayerHand />
      {gameState.turn_phase == "CHOOSING_ACTION" && <ChoosingActionBox />}
    </div>
  );
}

export default Board;
