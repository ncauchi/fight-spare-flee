import { useState } from "react";

function ItemCard() {
  const handleHover = (hovering: boolean) => {
    console.log("Hover");
    setHovering(hovering);
  };
  const hoverSpeed = 0.5;
  const [hovering, setHovering] = useState(false);
  return (
    <div
      className={`m-3 item-card ${hovering ? "hovering" : ""}`}
      onMouseEnter={() => {
        handleHover(true);
      }}
      onMouseLeave={() => {
        handleHover(false);
      }}
      style={{ "--hover-speed": `${hoverSpeed}s` } as React.CSSProperties}
    >
      <h4>Item</h4>
    </div>
  );
}

export default ItemCard;
