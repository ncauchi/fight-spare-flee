import "./Board.css";
import ChatWindow from "./ChatWindow";
import { useGameState, useAPI, useAnimations } from "./Game";
import { Spinner, Button, Stack } from "react-bootstrap";
import { useMemo, useState, useEffect, useCallback, useLayoutEffect, use } from "react";
import BoardPlayerBox from "./BoardPlayerBox";
import { usePlayerName } from "./NameContext";
import BoardPlayerHand from "./BoardPlayerHand";
import MonsterCard from "./MonsterCard";
import type { ItemInfo, MonsterInfo, PlayerCombatChoice } from "../api_wrapper";
import { AnimatePresence, motion } from "motion/react";
import ItemCard from "./ItemCard";
import type {
  CoinsAnimationInfo,
  ItemAnimationInfo,
  MonsterAnimationInfo,
  StarsAnimationInfo,
} from "./boardAnimations";

function Board() {
  const gameState = useGameState();
  const api = useAPI();
  const { anims, register, removeAnim } = useAnimations();
  const cardAnims = anims.filter((info): info is ItemAnimationInfo & { replaceId: number } => info.object === "item");
  const monAnims = anims.filter(
    (info): info is MonsterAnimationInfo & { replaceId: number } => info.object === "monster",
  );
  const hiddenCardIds = useMemo(
    () =>
      new Set(
        cardAnims.map((info) => info.replaceId), // no ! needed now
      ),
    [anims],
  );
  const hiddenMonsterIds = useMemo(() => new Set(monAnims.map((info) => info.replaceId)), [anims]);

  const starAnims = anims.filter((info): info is StarsAnimationInfo & { replaceId: number } => info.object === "stars");
  const coinAnims = anims.filter((info): info is CoinsAnimationInfo & { replaceId: number } => info.object === "coins");

  const handleAnimationComplete = useCallback((animId: number) => {
    removeAnim(animId);
  }, []);

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
    <div
      ref={(el) => {
        register("board", el);
      }}
      className="game-board"
    >
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
      <BoardPlayerHand
        selfRef={(el) => {
          register("player", el);
        }}
        registerRef={register}
        hiddenCardIds={hiddenCardIds}
        onItemClick={(i) => api.requestSendItemChoice(i)}
      />

      {anims.map((anim) => (
        <motion.div
          key={anim.id}
          className="animating-card"
          initial={anim.initial}
          animate={anim.animate}
          onAnimationComplete={() => handleAnimationComplete(anim.id)}
          transition={anim.transition}
        >
          {gameState.items && anim.object == "item" && <ItemCard data={anim.itemInfo} isSelected={false} />}
          {gameState.monsters && anim.object == "monster" && <MonsterCard data={anim.monsterInfo} isSelected={false} />}
          {anim.object == "coins" && <div className="animating-coins" />}
          {anim.object == "stars" && <div className="animating-stars" />}
        </motion.div>
      ))}
      <Stack direction="horizontal" gap={4} className="deck-shop-coins-stack">
        <div ref={(el) => register("deck", el)} onClick={() => api.requestSendAction("COMBAT")}>
          <h2>Deck: {gameState.deckSize}</h2>
        </div>
        <div ref={(el) => register("shop", el)} onClick={() => api.requestSendAction("SHOP")}>
          <h2>Shop: {gameState.shopSize}</h2>
        </div>
        <div ref={(el) => register("coins", el)} onClick={() => api.requestSendAction("COINS")}>
          <h2>Coin Stash</h2>
        </div>
      </Stack>
      <Stack direction="horizontal" gap={2} className="action-buttons-stack">
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
      <Stack direction="horizontal" gap={2} className="board-monster-stack">
        <AnimatePresence mode={"popLayout"}>
          {gameState.monsters?.map((mon, i) => (
            <motion.div
              key={mon.id}
              layout
              exit={{ opacity: 0 }}
              transition={{ layout: { type: "spring", duration: 0.2, bounce: 0.1 }, opacity: { duration: 0.1 } }}
            >
              <MonsterCard
                isActivePlayer={myTurn}
                data={mon}
                onClick={(s) => handleMonsterClick(s, i)}
                isSelected={selectedMon == i}
                isHidden={hiddenMonsterIds.has(mon.id)}
                ref={(el) => register(mon.id.toString(), el, "monster")}
              />
            </motion.div>
          ))}
        </AnimatePresence>
      </Stack>
    </div>
  );
}

export default Board;
