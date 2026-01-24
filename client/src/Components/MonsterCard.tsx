import { useState, useEffect } from "react";
import { type MonsterInfo, type PlayerCombatChoice } from "../api_wrapper";
import { Button, Stack } from "react-bootstrap";

interface Props {
  data: MonsterInfo;
  onClick?: (s: PlayerCombatChoice) => void;
  isActivePlayer: boolean;
  isSelected: boolean;
}

function MonsterCard({ data, onClick, isActivePlayer, isSelected }: Props) {
  const [flipped, setFlipped] = useState(false);

  useEffect(() => {
    if (data.name != undefined && !flipped) {
      setFlipped(true);
    }
  }, [data.name, flipped]);

  const showButtons = flipped && isSelected && isActivePlayer;

  const handleCardClick = () => {
    if (isActivePlayer && onClick) {
      onClick("SELECT");
    }
  };

  const handleSpare = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onClick) {
      onClick("SPARE");
    }
  };

  const handleFlee = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onClick) {
      onClick("FLEE");
    }
  };

  return (
    <div
      className={`monster-card-container ${isSelected ? "selected" : ""}`}
      onClick={handleCardClick}
      style={{ cursor: isActivePlayer ? "pointer" : "default" }}
    >
      <div className={`monster-card-flipper ${flipped ? "flipped" : ""}`}>
        {/* Card Back Face - Shows only stars */}
        <div className="monster-card-face monster-card-back">
          <Stack direction="horizontal" gap={1}>
            {Array.from({ length: data.stars }, (_, i) => (
              <h1 key={i} style={{ margin: 0, fontSize: "2rem" }}>
                ★
              </h1>
            ))}
          </Stack>
        </div>

        {/* Card Front Face - Shows monster details - Only render when flipped */}
        {flipped && (
          <div className="monster-card-face monster-card-front">
            <Stack direction="vertical" gap={1} style={{ fontSize: "0.8rem" }}>
              <h3 style={{ margin: 0, fontSize: "1rem" }}>
                {data.name} {"★".repeat(data.stars)}
              </h3>
              <p style={{ margin: 0 }}>
                HP: {data.health}/{data.max_health}
                {data.fight_coins ? ` +${data.fight_coins}` : ""}
              </p>
              <p style={{ margin: 0 }}>Spare: {data.spare}/6</p>
              <p style={{ margin: 0 }}>
                Flee: {data.flee_coins !== undefined && data.flee_coins >= 0 ? data.flee_coins : "Can't Flee"}
              </p>
            </Stack>

            {showButtons && (
              <div className="monster-card-buttons">
                <Button variant="secondary" size="sm" className="monster-card-button" onClick={handleSpare}>
                  Spare
                </Button>
                <Button variant="secondary" size="sm" className="monster-card-button" onClick={handleFlee}>
                  Flee
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default MonsterCard;
