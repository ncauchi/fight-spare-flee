import { useState } from "react";
import { type ItemInfo } from "../api_wrapper";
import { Stack } from "react-bootstrap";

interface Props {
  data: ItemInfo;
  onClick?: React.MouseEventHandler<HTMLDivElement>;
  isSelected: boolean;
}

function ItemCard({ data, onClick, isSelected }: Props) {
  const handleHover = (hovering: boolean) => {
    setHovering(hovering);
  };
  const hoverSpeed = 0.5;
  const [hovering, setHovering] = useState(false);
  return (
    <div
      className={`m-3 item-card ${hovering ? "hovering" : ""} ${isSelected ? "selected" : ""}`}
      onMouseEnter={() => {
        handleHover(true);
      }}
      onMouseLeave={() => {
        handleHover(false);
      }}
      onClick={onClick}
      style={{ "--hover-speed": `${hoverSpeed}s` } as React.CSSProperties}
    >
      <Stack dir="vertical">
        <h2>{data.name}</h2>
        <p>{data.text}</p>
        <p>{data.target_type}</p>
      </Stack>
    </div>
  );
}

export default ItemCard;
