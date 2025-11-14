import { type Player } from "./Game";

interface Props {
  player: Player | null;
}
function PlayerBox({ player }: Props) {
  if (!player) {
    return "Empty";
  } else {
    const name = player.name;
    return <h1>{name}</h1>;
  }
}

export default PlayerBox;
