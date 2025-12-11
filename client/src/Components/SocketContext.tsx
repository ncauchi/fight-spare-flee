import { type ReactNode, createContext, useState, useContext, useRef, useEffect, type RefObject } from "react";
import { io, type Socket } from "socket.io-client";
import configData from ".././config.json";

const SOCKET_URL = configData.GAMES_URL;

export interface SocketContextType {
  socketRef: RefObject<Socket | null>;
  connected: boolean;
}

const SocketContext = createContext<SocketContextType | undefined>(undefined);

interface Props {
  children?: ReactNode;
  gameId: string | undefined;
  playerName: string;
  bindings: { type: string; func: (data?: any) => void }[];
}

export const SocketProvider = ({ children, gameId, playerName, bindings }: Props) => {
  const socketRef = useRef<Socket>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const socket = io(SOCKET_URL, { transports: ["websocket", "polling"] });
    socketRef.current = socket;

    bindings.forEach(({ type, func }) => {
      socket.on(type, func);
    });

    socket.on("connect", () => {
      console.log("Connected to server");
      setConnected(true);
    });

    if (gameId && playerName) {
      console.log(`Requesting to joing game ${gameId}`);
      socket.emit("JOIN", gameId, playerName);
    } else {
      if (!gameId) {
        console.error("Missing valid gameId in JOIN request");
      }
      if (!playerName) {
        console.error("Missing valid PlayerName in JOIN request");
      }
    }

    socket.on("disconnect", () => {
      console.log("Disconnected from server");
      setConnected(false);
    });

    return () => {
      // Remove all event listeners
      bindings.forEach(({ type, func }) => {
        socket.off(type, func);
      });
      socket.off("connect");
      socket.off("disconnect");

      // Disconnect the socket from this effect's closure
      socket.disconnect();
    };
  }, [playerName]);

  return <SocketContext.Provider value={{ socketRef, connected }}>{children}</SocketContext.Provider>;
};

export const useGameSocket = () => {
  const context = useContext(SocketContext);
  if (!context) {
    throw new Error("useGameSocket must be used within a SocketProvider");
  }
  return context;
};

export const useSocketEmit = () => {
  const { socketRef } = useGameSocket();

  return (event: string, ...data: any[]) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit(event, ...data);
    } else {
      console.warn(`Cannot emit "${event}": socket not connected`);
    }
  };
};
