import { HashRouter, Routes, Route } from "react-router-dom";
import "./App.css";
import Homepage from "./Components/Homepage";
import Game from "./Components/Game";
import ServerBrowser from "./Components/ServerBrowser";

function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<Homepage />} />
        <Route path="/browse" element={<ServerBrowser />} />
        <Route path="/play" element={<Game />} />
      </Routes>
    </HashRouter>
  );
}

export default App;
