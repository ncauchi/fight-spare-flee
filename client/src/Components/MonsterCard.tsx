import { useState } from "react";
import { type MonsterInfo, type PlayerCombatChoice } from "../api_wrapper";
import { Button, Stack } from "react-bootstrap";

interface Props {
  data: MonsterInfo;
  onClick?: (s: PlayerCombatChoice) => void;
}

function MonsterCard({ data, onClick }: Props) {
  const handleHover = (hovering: boolean) => {
    setHovering(hovering);
  };
  const hoverSpeed = 0.5;
  const [hovering, setHovering] = useState(false);
  const visible = data.name != undefined;

  if (!visible) {
    return (
      <div
        className={`m-3 monster-card`}
        onClick={() => (onClick ? onClick("SELECT") : undefined)}
        style={{ "--hover-speed": `${hoverSpeed}s` } as React.CSSProperties}
      >
        <Stack dir="horizontal">
          {Array.from({ length: data.stars }, (_) => (
            <h1>*</h1>
          ))}
        </Stack>
      </div>
    );
  } else {
    return (
      <>
        <div
          className={`m-3 monster-card ${hovering ? "hovering" : ""}`}
          onMouseEnter={() => {
            handleHover(true);
          }}
          onMouseLeave={() => {
            handleHover(false);
          }}
          style={{ "--hover-speed": `${hoverSpeed}s` } as React.CSSProperties}
        >
          <Stack dir="vertical">
            <h2>
              {data.name} {data.stars}
            </h2>
            <p>
              Health: {data.health}/{data.max_health} +{data.fight_coins}
            </p>
            <p>Spare: {data.spare}/6</p>
            <p>Flee: {data.flee_coins && data.flee_coins >= 0 ? data.flee_coins : "Can't Flee"}</p>
          </Stack>
        </div>
        {hovering && (
          <Stack dir="horizontal">
            <Button variant="primary" onClick={() => (onClick ? onClick("FIGHT") : undefined)}>
              Fight
            </Button>
            <Button variant="primary" onClick={() => (onClick ? onClick("SPARE") : undefined)}>
              Spare
            </Button>
            <Button variant="primary" onClick={() => (onClick ? onClick("FLEE") : undefined)}>
              Flee
            </Button>
          </Stack>
        )}
      </>
    );
  }
}

export default MonsterCard;
