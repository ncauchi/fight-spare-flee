import { type PlayerInfo } from "../api_wrapper";
import dancingBanana from "../assets/dancing-banana.gif";

interface Props {
  player: PlayerInfo;
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
      <div
        className={`player-container container ${active ? "active" : ""}`}
        style={{ backgroundImage: `url(${dancingBanana})`, backgroundSize: "cover", backgroundPosition: "center" }}
      >
        <h1>{player.name}</h1>
        <p>
          Health: {player.health} Coins: {player.coins} Cards: {player.num_items}
          <br />
          Stars: {player.captured_stars.join(", ")}
        </p>
      </div>
    </div>
  );
}

export default BoardPlayerBox;
