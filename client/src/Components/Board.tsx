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

  const playerName = usePlayerName();
  const opponents = gameState?.players.filter((p) => {
    return p.name != playerName;
  });
  const myTurn = gameState?.active_player === playerName;
  const isSelectedMonster =
    myTurn &&
    gameState.selectedMon != undefined &&
    gameState.monsters &&
    gameState.monsters.some((mon) => {
      return mon.name != undefined;
    });
  const selectedMon = gameState.selectedMon != undefined ? gameState.selectedMon : -1;

  const isLeftoverCombat = gameState.monsters?.every((mon) => {
    return mon.name != undefined;
  });
  const handleMonsterClick = (s: PlayerCombatChoice, i: number) => {
    if (myTurn) {
      api.requestSendCombat(s, i);
    }
  };

  return (
    <div className="game-board">
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
              onClick={(s) => handleMonsterClick(s, i)}
              isSelected={selectedMon == i}
            />
          ))}
        </Stack>
        <Stack direction="horizontal" gap={2}>
          {isSelectedMonster && gameState.turn_phase == "COMBAT_ACTION" && (
            <Button onClick={() => api.requestSendCombat("FIGHT", selectedMon)}>Fight</Button>
          )}
          {isSelectedMonster && gameState.turn_phase == "COMBAT_ACTION" && (
            <Button onClick={() => api.requestSendCombat("SPARE", selectedMon)}>Spare</Button>
          )}
          {isSelectedMonster && gameState.turn_phase == "COMBAT_ACTION" && !isLeftoverCombat && (
            <Button onClick={() => api.requestSendCombat("FLEE", selectedMon)}>Flee</Button>
          )}
          {isSelectedMonster && gameState.turn_phase == "COMBAT_ACTION" && isLeftoverCombat && (
            <Button onClick={() => api.requestSendCombat("FLEE", selectedMon)}>Pass</Button>
          )}
          {isSelectedMonster && gameState.turn_phase == "COMBAT_FIGHT" && (
            <Button variant="danger" onClick={() => api.requestSendCombat("FIGHT", selectedMon)}>
              Use Items
            </Button>
          )}
        </Stack>
      </Stack>
    </div>
  );
}

export default Board;
