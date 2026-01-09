import { Stack, Spinner } from "react-bootstrap";
import ItemCard from "./ItemCard";
import { useGameState } from "./Game";
import { usePlayerName } from "./NameContext";
import type { PlayerInfo } from "../api_wrapper";

function BoardPlayerHand() {
  const gameState = useGameState();
  const playerName = usePlayerName();
  const player = gameState?.players.find((p: PlayerInfo) => {
    return p.name == playerName;
  });
  if (!player) return <Spinner></Spinner>;
  return (
    <div className="item-card-box">
      <p>
        Health: {player.health} Coins: {player.coins} Cards: {player.num_items}
      </p>
      <Stack direction="horizontal" gap={1}>
        <ItemCard />
        <ItemCard />
      </Stack>
    </div>
  );
}

export default BoardPlayerHand;
