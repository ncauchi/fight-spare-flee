import { type Player } from "./Game";

interface Props {
  player: Player;
  index: number;
  numPlayers: number;
  active: boolean;
}

const baseAngleStep = 20;

function BoardPlayerBox({ player, index, numPlayers, active }: Props) {
  const relativePositionToMiddle = index - (numPlayers - 1) / 2;
  const angle = `${90 - baseAngleStep * relativePositionToMiddle}deg`;

  return (
    <div key={index} className="player-container position" style={{ "--angle": angle } as React.CSSProperties}>
      <div className={`player-container container ${active ? "active" : ""}`}>
        <h1>{player.name}</h1>
      </div>
    </div>
  );
}

export default BoardPlayerBox;
