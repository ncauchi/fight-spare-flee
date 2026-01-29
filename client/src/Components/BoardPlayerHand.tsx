import { Stack, Spinner } from "react-bootstrap";
import ItemCard from "./ItemCard";
import { useGameState } from "./Game";
import { usePlayerName } from "./NameContext";
import type { PlayerInfo } from "../api_wrapper";

interface Props {
  onItemClick: (idx: number) => void;
}

function BoardPlayerHand({ onItemClick }: Props) {
  const gameState = useGameState();
  const playerName = usePlayerName();
  const player = gameState?.players.find((p: PlayerInfo) => {
    return p.name == playerName;
  });
  if (!player) return <Spinner></Spinner>;
  const cards = gameState?.items;
  const selectedItems = gameState?.selectedItems;

  return (
    <div className="item-card-box">
      <p>
        Health: {player.health} Coins: {player.coins} Cards: {player.num_items}
      </p>
      <p>Phase: {gameState?.turn_phase}</p>
      <Stack direction="horizontal" gap={1}>
        {cards &&
          cards.map((info, i) => (
            <ItemCard
              data={info}
              onClick={() => onItemClick(i)}
              isSelected={selectedItems ? selectedItems[i] : false}
            />
          ))}
      </Stack>
    </div>
  );
}

export default BoardPlayerHand;
