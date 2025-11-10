import { type ReactNode, createContext, useState, useContext } from "react";

const NameContext = createContext("");
const NameUpdateContext = createContext((_: string) => {});

interface Props {
  children?: ReactNode;
}
export const NameProvider = ({ children }: Props) => {
  const [playerName, setPlayerNameState] = useState("");

  const setPlayerName = (name: string) => {
    setPlayerNameState(name);
  };

  return (
    <NameUpdateContext value={setPlayerName}>
      <NameContext.Provider value={playerName}>{children}</NameContext.Provider>
    </NameUpdateContext>
  );
};

export const usePlayerName = () => {
  const context = useContext(NameContext);
  return context;
};

export const useSetPlayerName = () => {
  const context = useContext(NameUpdateContext);
  return context;
};
