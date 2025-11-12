import { HashRouter, Routes, Route } from "react-router-dom";
import "./App.css";
import Homepage from "./Components/Homepage";
import Game from "./Components/Game";
import ServerBrowser from "./Components/ServerBrowser";
import Lobby from "./Components/Lobby";
import CreateRoom from "./Components/CreateRoom";
import { NameProvider } from "./Components/NameContext";

function App() {
  return (
    <NameProvider>
      <HashRouter>
        <Routes>
          <Route path="/" element={<Homepage />} />
          <Route path="/browse" element={<ServerBrowser />} />
          <Route path="/play:gameId" element={<Game />} />
          <Route path="/lobby/:gameId" element={<Lobby />} />
          <Route path="/create" element={<CreateRoom />} />
        </Routes>
      </HashRouter>
    </NameProvider>
  );
}

export default App;
