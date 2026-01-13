import "./Board.css";
import ChatWindow from "./ChatWindow";
import { type GameState, useGameState, useAPI } from "./Game";
import { Spinner, Button, Stack } from "react-bootstrap";
import { useRef, useState } from "react";
import BoardPlayerBox from "./BoardPlayerBox";
import { usePlayerName } from "./NameContext";
import ChoosingActionBox from "./ChoosingActionBox";
import BoardPlayerHand from "./BoardPlayerHand";
import BoardCards from "./BoardCards";
import type { PlayerCombatChoice } from "../api_wrapper";

function Board() {
  const gameState = useGameState();
  const api = useAPI();

  if (!api || !gameState) {
    return <Spinner></Spinner>;
  }

  const [flipped, setFlipped] = useState(false);
  const selectedItemRef = useRef(-1);
  const selectedMonsterRef = useRef(-1);
  const [waitingAction, setWaitingAction] = useState(false);
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
  const handleHandItemClick = (idx: number) => {
    if (gameState.turn_phase != "IN_COMBAT" || !waitingAction) {
      return;
    }
    setWaitingAction(false);
    api.requestSendAction("COMBAT", "FIGHT", selectedMonsterRef.current, idx);
  };
  const handleBoardItemClick = (idx: number) => {};

  const handleBoardMonsterClick = (idx: number, selection: PlayerCombatChoice) => {
    if (gameState.turn_phase != "IN_COMBAT" || waitingAction) {
      return;
    }
    console.log(`selected monster ${idx}`);
    if (selection == "SELECT") {
      selectedMonsterRef.current = idx;
      api.requestSendAction("COMBAT", "SELECT", idx);
    } else if (selection == "FIGHT") {
      setWaitingAction(true);
      console.log("Waiting to select item");
    } else if (selection == "SPARE") {
      api.requestSendAction("COMBAT", "SPARE", idx);
    } else if (selection == "FLEE") {
      api.requestSendAction("COMBAT", "FLEE", idx);
    }
  };

  const handleDeckClick = () => {
    console.log("deck clicked");
    if (gameState.turn_phase == "CHOOSING_ACTION") {
      api.requestSendAction("FSF");
    } else {
      console.warn("wrong turn phase for that");
    }
  };

  const handleShopClick = () => {
    console.log("shop clicked");
    if (gameState.turn_phase == "CHOOSING_ACTION" || gameState.turn_phase == "SHOPPING") {
      api.requestSendAction("SHOP");
    } else {
      console.warn("wrong turn phase for that");
    }
  };

  const handleCoinsClick = () => {
    console.log("coins clicked");
    if (gameState.turn_phase == "CHOOSING_ACTION") {
      api.requestSendAction("COINS");
    } else {
      console.warn("wrong turn phase for that");
    }
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
        <>
          <Button variant="primary" className={"next-turn-button"} onClick={handleNextTurn}>
            <h3>Next Turn</h3>
          </Button>
        </>
      )}
      <BoardPlayerHand onItemClick={handleHandItemClick} />
      <BoardCards
        selectBoardItem={handleBoardItemClick}
        selectBoardMonster={handleBoardMonsterClick}
        deckClick={handleDeckClick}
        shopClick={handleShopClick}
        coinsClick={handleCoinsClick}
      />
    </div>
  );
}

export default Board;
