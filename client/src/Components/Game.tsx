import { useParams, Outlet } from "react-router-dom";
import { SocketProvider } from "./SocketContext";
import { usePlayerName } from "./NameContext";
import { useState, useMemo, createContext, useContext } from "react";

interface Message {
  player: string;
  text: string;
}

export interface GameState {
  messages: Message[];
  connected: boolean;
}

const GameStateContext = createContext<GameState | undefined>(undefined);

const defaultGameState: GameState = {
  messages: [],
  connected: false,
};

export const useGameState = () => {
  const context = useContext(GameStateContext);
  if (!context) throw new Error("Must be used within GameStateProvider");
  return context;
};

function Game() {
  const { gameId } = useParams();
  const playerName = usePlayerName();
  const [gameState, setGameState] = useState<GameState>(defaultGameState);

  const handleChat = (data: Message) => {
    console.log("Recieved Message from server", data);
    setGameState((prevState) => ({
      ...prevState,
      messages: [...prevState.messages, data],
    }));
  };

  const bindings = useMemo(
    () => [
      {
        type: "CHAT",
        func: handleChat,
      },
    ],
    []
  );

  return (
    <SocketProvider playerName={playerName} gameId={gameId} bindings={bindings}>
      <GameStateContext.Provider value={gameState}>
        <Outlet />
      </GameStateContext.Provider>
    </SocketProvider>
  );
}

export default Game;
