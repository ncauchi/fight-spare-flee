import { type PlayerInfo } from "../api_wrapper";
import { Stack } from "react-bootstrap";
import { usePlayerName } from "./NameContext";

interface Props {
  player: PlayerInfo;
}
function PlayerBox({ player }: Props) {
  const name = player.name;
  const ready = player.ready;
  const clientPlayerName = usePlayerName();
  return (
    <div key={name} className={`mb-2 lobby-player-box ${ready ? "ready" : "not-ready"}`}>
      <Stack direction="horizontal" gap={1}>
        <h1>{name}</h1>
        {clientPlayerName == name ? "(me)" : ""}
      </Stack>
    </div>
  );
}

export default PlayerBox;
