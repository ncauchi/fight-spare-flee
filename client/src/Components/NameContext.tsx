import { type ReactNode, createContext, useState, useContext, useEffect } from "react";
import { getCookie, addCookie } from "./CookieContext";

const NameContext = createContext("uninitialized");
const NameUpdateContext = createContext((_: string) => {});

interface Props {
  children?: ReactNode;
}
export const NameProvider = ({ children }: Props) => {
  const [playerName, setPlayerNameState] = useState("");

  const setPlayerName = (name: string) => {
    addCookie("playerName", name, 2);
    setPlayerNameState(name);
  };

  useEffect(() => {
    const savedPlayerName = getCookie("playerName");
    if (!savedPlayerName) {
      return;
    }
    console.log(`Retrieved player name: ${savedPlayerName} from cookies.`);
    setPlayerName(savedPlayerName);
  }, []);

  return (
    <NameUpdateContext value={setPlayerName}>
      <NameContext.Provider value={playerName}>{children}</NameContext.Provider>
    </NameUpdateContext>
  );
};

export const usePlayerName = () => {
  const context = useContext(NameContext);
  if (!context) {
    console.warn("Session has no player name");
  }
  return context;
};

export const useSetPlayerName = () => {
  const context = useContext(NameUpdateContext);
  return context;
};
