import { useParams, Outlet, useNavigate } from "react-router-dom";
import { SocketProvider } from "./SocketContext";
import { usePlayerName } from "./NameContext";
import { useState, useMemo, createContext, useContext } from "react";

export interface Message {
  player: string;
  text: string;
}

export interface Player {
  name: string;
  ready?: boolean;
}

export interface GameState {
  game_name: string;
  game_owner: string;
  max_players: number;
  players: Player[];
  messages: Message[];
  connected: boolean;
}

const GameStateContext = createContext<GameState | undefined>(undefined);

export const useGameState = () => {
  const context = useContext(GameStateContext);
  return context;
};

function Game() {
  const { gameId } = useParams();
  const playerName = usePlayerName();
  const [gameState, setGameState] = useState<GameState | undefined>(undefined);
  const navigate = useNavigate();

  const handleChat = (data: Message) => {
    console.log("Recieved Message from server", data);
    setGameState((prevState) => {
      if (!prevState) return undefined;
      return {
        ...prevState,
        messages: [...prevState.messages, data],
      };
    });
  };

  const handlePlayersUpdate = (data: { players: Player[] }) => {
    console.log("Recieved player updates from server", data);
    setGameState((prevState) => {
      if (!prevState) return undefined;
      return {
        ...prevState,
        players: data.players,
      };
    });
  };

  const handleInit = (data: GameState) => {
    setGameState({
      game_name: data.game_name,
      game_owner: data.game_owner,
      max_players: data.max_players,
      players: data.players,
      messages: data.messages,
      connected: true,
    });
    console.log("Retrieved game data from game service.");
  };

  const handleStartGame = () => {
    console.log("Starting Game...");
    navigate(`/play/${gameId}/board`);
  };

  const bindings = useMemo(
    () => [
      {
        type: "CHAT",
        func: handleChat,
      },
      {
        type: "PLAYERS",
        func: handlePlayersUpdate,
      },
      {
        type: "INIT",
        func: handleInit,
      },
      {
        type: "START_GAME",
        func: handleStartGame,
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
