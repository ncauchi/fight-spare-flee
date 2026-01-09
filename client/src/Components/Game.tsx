import { useParams, Outlet, useNavigate } from "react-router-dom";
import { usePlayerName } from "./NameContext";
import { useState, createContext, useContext, useRef, useEffect, type RefObject } from "react";
import { io } from "socket.io-client";
import * as api from "../api_wrapper.ts";
import configData from ".././config.json";

export interface GameState {
  game_name: string;
  game_owner: string;
  max_players: number;
  players: api.PlayerInfo[];
  messages: api.Message[];
  connected: boolean;
  status: api.GameStatus;
  active_player?: string;
  turn_phase?: api.TurnPhase;
  items?: api.ItemInfo[];
  monsters?: api.MonsterInfo[];
}

const GameStateContext = createContext<GameState | undefined>(undefined);
const APIContext = createContext<RefObject<api.GameAPI | undefined> | undefined>(undefined);

export const useGameState = () => {
  const context = useContext(GameStateContext);
  return context;
};

export const useAPI = () => {
  const context = useContext(APIContext);
  if (!context) {
    throw new Error("useAPI error");
  }
  return context.current;
};

function Game() {
  const { gameId } = useParams();
  const playerName = usePlayerName();
  const [gameState, setGameState] = useState<GameState | undefined>(undefined);
  const navigate = useNavigate();
  const apiRef = useRef<api.GameAPI>(undefined);

  useEffect(() => {
    const socket = io(configData.GAMES_URL, { transports: ["websocket", "polling"] });
    apiRef.current = new api.GameAPI(socket);

    const cleanup: (() => void)[] = [];

    socket.on("connect", () => {
      console.log("Connected to server");
      if (gameId && playerName) {
        console.log(`Requesting to joing game ${gameId}`);
        apiRef.current?.requestJoinGame(gameId, playerName);
      } else {
        if (!gameId) {
          console.error("Missing valid gameId in JOIN request");
        }
        if (!playerName) {
          console.error("Missing valid PlayerName in JOIN request");
        }
      }
    });

    socket.on("disconnect", () => {
      console.log("Disconnected from server");
    });

    apiRef.current.onChat(handleChat, cleanup);

    apiRef.current.onInit(handleInit, cleanup);

    apiRef.current.onPlayers(handlePlayersUpdate, cleanup);

    apiRef.current.onStartGame(handleStartGame, cleanup);

    apiRef.current.onChangeTurn(handleTurnChange, cleanup);

    apiRef.current.onActionResponse(handleActionResponse, cleanup);

    apiRef.current.onHandUpdate(handleHandUpdate, cleanup);

    return () => {
      // Remove all event listeners
      cleanup.forEach((func) => func());
      socket.off("connect");
      socket.off("disconnect");

      // Disconnect the socket from this effect's closure
      socket.disconnect();
    };
  }, [playerName]);

  const handleChat = (data: api.Message) => {
    console.log("Recieved Message from server", data);
    setGameState((prevState) => {
      if (!prevState) return undefined;
      return {
        ...prevState,
        messages: [...prevState.messages, data],
      };
    });
  };

  const handlePlayersUpdate = (data: api.PlayerInfo[]) => {
    console.log("Recieved player updates from server", data);
    setGameState((prevState) => {
      if (!prevState) return undefined;
      return {
        ...prevState,
        players: data,
      };
    });
  };

  const handleInit = (data: api.InitResponse) => {
    const initState: GameState = {
      game_name: data.game_name,
      game_owner: data.game_owner,
      max_players: data.max_players,
      players: data.players,
      messages: data.messages,
      connected: true,
      status: data.status,
      active_player: data.active_player,
    };
    setGameState(initState);
    console.log("Retrieved game data from game service.");
    if (initState.status == "GAME") {
      navigate(`/play/${gameId}/board`);
    }
  };

  const handleTurnChange = (new_player: string) => {
    console.log("New player turn: ", new_player);
    setGameState((prevState) => {
      if (!prevState) return undefined;
      return {
        ...prevState,
        active_player: new_player,
        turn_phase: new_player == playerName ? "CHOOSING_ACTION" : "TURN_ENDED",
      };
    });
  };

  const handleActionResponse = (
    new_phase: api.PlayerActionChoice,
    coins_change: number,
    monsters: api.MonsterInfo[]
  ) => {
    if (new_phase == "COINS") {
      console.log(`Picked up ${coins_change} coins`);
    } else if (new_phase == "SHOP") {
      console.log(`Bought item for ${coins_change * -1} coins.`);
      setGameState((prevState) => {
        if (!prevState) return undefined;
        return {
          ...prevState,
          turn_phase: "SHOPPING",
        };
      });
    } else if (new_phase == "FSF") {
      console.log(`FSFing ${monsters}`);
      setGameState((prevState) => {
        if (!prevState) return undefined;
        return {
          ...prevState,
          turn_phase: "IN_COMBAT",
          monsters: monsters,
        };
      });
    }
  };

  const handleStartGame = (first_player: string) => {
    console.log("Starting Game...");
    const firstName = first_player;
    setGameState((prevState) => {
      if (!prevState) return undefined;
      return {
        ...prevState,
        active_player: first_player,
        turn_phase: firstName == playerName ? "CHOOSING_ACTION" : "TURN_ENDED",
      };
    });
    navigate(`/play/${gameId}/board`);
  };

  const handleHandUpdate = (items: api.ItemInfo[]) => {
    console.log("Items update: ", items);
    setGameState((prevState) => {
      if (!prevState) return undefined;
      return {
        ...prevState,
        items: items,
      };
    });
  };

  return (
    <APIContext.Provider value={apiRef}>
      <GameStateContext.Provider value={gameState}>
        <Outlet />
      </GameStateContext.Provider>
    </APIContext.Provider>
  );
}

export default Game;
