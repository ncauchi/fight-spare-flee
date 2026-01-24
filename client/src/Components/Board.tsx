import "./Board.css";
import ChatWindow from "./ChatWindow";
import { type GameState, useGameState, useAPI } from "./Game";
import { Spinner, Button, Stack } from "react-bootstrap";
import { useRef, useState } from "react";
import BoardPlayerBox from "./BoardPlayerBox";
import { usePlayerName } from "./NameContext";
import BoardPlayerHand from "./BoardPlayerHand";
import MonsterCard from "./MonsterCard";
import type { PlayerCombatChoice } from "../api_wrapper";

function Board() {
  const gameState = useGameState();
  const api = useAPI();

  if (!api || !gameState) {
    return <Spinner></Spinner>;
  }

  const [flipped, setFlipped] = useState(false);
  const [selectedMon, setSelectedMon] = useState(-1);
  const playerName = usePlayerName();
  const opponents = gameState?.players.filter((p) => {
    return p.name != playerName;
  });
  const myTurn = gameState?.active_player === playerName;

  const handleFlip = () => {
    setFlipped(!flipped);
  };

  const handleMonsterSelect = (s: PlayerCombatChoice, i: number) => {
    setSelectedMon(i);
    api.requestSendCombat(s, i);
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
          <Button variant="primary" className={"next-turn-button"} onClick={() => api.requestSendAction("END")}>
            <h3>Next Turn</h3>
          </Button>
        </>
      )}
      <BoardPlayerHand onItemClick={(i) => api.requestSendItemChoice(i)} />
      <Stack direction="vertical" className="deck-shop-coins-stack">
        <Stack direction="horizontal" gap={4}>
          <div onClick={() => api.requestSendAction("COMBAT")}>
            <h2>Deck: {gameState.deckSize}</h2>
          </div>
          <div onClick={() => api.requestSendAction("SHOP")}>
            <h2>Shop: {gameState.shopSize}</h2>
          </div>
          <div onClick={() => api.requestSendAction("COINS")}>
            <h2>Coin Stash</h2>
          </div>
        </Stack>
        <Stack direction="horizontal" gap={2}>
          {gameState.monsters?.map((mon, i) => (
            <MonsterCard
              key={i}
              isActivePlayer={myTurn}
              data={mon}
              onClick={(s) => handleMonsterSelect(s, i)}
              isSelected={selectedMon == i}
            />
          ))}
        </Stack>
      </Stack>
    </div>
  );
}

export default Board;
