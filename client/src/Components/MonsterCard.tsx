import { useState, useEffect } from "react";
import { type MonsterInfo, type PlayerCombatChoice } from "../api_wrapper";
import { Button, Stack } from "react-bootstrap";

interface Props {
  data: MonsterInfo;
  onClick?: (s: PlayerCombatChoice) => void;
  isActivePlayer?: boolean;
  isSelected?: boolean;
  isHidden?: boolean;
  ref?: React.Ref<HTMLDivElement>;
}

function MonsterCard({ data, onClick, isActivePlayer = false, isSelected = false, isHidden = false, ref }: Props) {
  const flipped = data.name != undefined;

  const handleCardClick = () => {
    if (isActivePlayer && onClick) {
      onClick("SELECT");
    }
  };

  return (
    <div
      className={`monster-card ${flipped ? "flipped" : ""} ${isSelected ? "selected" : ""}`}
      onClick={handleCardClick}
      style={{ cursor: isActivePlayer ? "pointer" : "default", opacity: isHidden ? 0 : 1 }}
      ref={ref}
    >
      <div className="monster-card-back">
        <Stack direction="horizontal" gap={1}>
          {Array.from({ length: data.stars }, (_, i) => (
            <h1 key={i} style={{ margin: 0, fontSize: "2rem" }}>
              ★
            </h1>
          ))}
        </Stack>
      </div>

      {flipped && (
        <div className="monster-card-front">
          <Stack direction="vertical" gap={1} style={{ fontSize: "0.8rem" }}>
            <h3 style={{ color: "black", margin: 0, fontSize: "1rem" }}>
              {data.name} {"★".repeat(data.stars)}
            </h3>
            <p style={{ color: "black", margin: 0 }}>
              HP: {data.health}/{data.max_health}
              {data.fight_coins ? ` +${data.fight_coins}` : ""}
            </p>
            <p style={{ color: "black", margin: 0 }}>Spare: {data.spare}/6</p>
            <p style={{ color: "black", margin: 0 }}>
              Flee: {data.flee_coins !== undefined && data.flee_coins >= 0 ? data.flee_coins : "Can't Flee"}
            </p>
          </Stack>
        </div>
      )}
    </div>
  );
}

export default MonsterCard;
