import { use, useState } from "react";
import { useAPI } from "./Game";
import { Stack, Button } from "react-bootstrap";

function ChoosingActionBox() {
  const api = useAPI();

  if (!api) {
    return;
  }

  const chooseCoins = () => {
    api.requestSendAction("COINS");
  };

  const chooseShop = () => {
    api.requestSendAction("SHOP");
  };

  const chooseFSF = () => {
    api.requestSendAction("FSF");
  };

  return (
    <div className="choosing-action-box">
      <Stack className="mx-auto justify-content-center" gap={2} direction="horizontal">
        <Button variant="primary" onClick={chooseCoins}>
          Take Coins
        </Button>
        <Button variant="primary" onClick={chooseShop}>
          Buy Items
        </Button>
        <Button variant="primary" onClick={chooseFSF}>
          Fight
        </Button>
      </Stack>
    </div>
  );
}

export default ChoosingActionBox;
