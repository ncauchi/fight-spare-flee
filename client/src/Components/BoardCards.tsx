import { useGameState } from "./Game";
import { useAPI } from "./Game";
import { Stack, Button } from "react-bootstrap";
import ItemCard from "./ItemCard";
import MonsterCard from "./MonsterCard";
import type { PlayerCombatChoice } from "../api_wrapper";

interface Props {
  selectBoardItem: (i: number) => void;
  selectBoardMonster: (i: number, s: PlayerCombatChoice) => void;
  deckClick: () => void;
  shopClick: () => void;
  coinsClick: () => void;
}

function BoardCards({ selectBoardItem, selectBoardMonster, deckClick, shopClick, coinsClick }: Props) {
  const api = useAPI();
  const gameState = useGameState();

  if (!api || !gameState) {
    return;
  }
  const fsfMonsters = gameState.monsters;
  const boardItems = gameState.boardItems;
  const phase = gameState.turn_phase;

  return (
    <Stack dir="horizontal">
      <div onClick={deckClick}>
        <h2>Deck: {gameState.deckSize}</h2>
        {phase == "CHOOSING_ACTION" && <p>Click to Fight!</p>}
      </div>
      <div onClick={shopClick}>
        <h2>Shop: {gameState.shopSize}</h2>
        {phase == "CHOOSING_ACTION" && <p>Click to buy an Item</p>}
      </div>
      <div onClick={coinsClick}>
        <h2>Coin Stash</h2>
        {phase == "CHOOSING_ACTION" && <p>Click to take two coins</p>}
      </div>
      <Stack dir="vertical">
        <Stack dir="horizontal">
          {fsfMonsters?.map((mon, i) => (
            <MonsterCard data={mon} onClick={(s: PlayerCombatChoice) => selectBoardMonster(i, s)} />
          ))}
        </Stack>
        <Stack dir="horizontal">
          {boardItems?.map((item, i) => (
            <ItemCard data={item} onClick={() => selectBoardItem(i)} />
          ))}
        </Stack>
      </Stack>
    </Stack>
  );
}

export default BoardCards;
