// api_wrapper.ts
import { Socket } from "socket.io-client";

// ==================== TYPES ====================

// Server -> Client can have args, Client <- server needs to be wrapped in types

// Enums
export type PlayerActionChoice = "COINS" | "SHOP" | "FSF" | "END";

export type GameStatus = "LOBBY" | "GAME" | "ENDED";

export type TurnPhase = "CHOOSING_ACTION" | "IN_COMBAT" | "SHOPPING" | "USING_SPECIAL" | "TURN_ENDED";

// Shared Models
export interface ItemInfo {
  name: string;
}

export interface Message {
  player_name: string;
  text: string;
}

export interface MonsterInfo {
  name?: string;
  stars: number;
}

export interface PlayerInfo {
  name: string;
  ready: boolean;
  coins: number;
  num_items: number;
  health: number;
}

// Server -> Client Event Types
export interface InitResponse {
  game_name: string;
  game_owner: string;
  max_players: number;
  players: PlayerInfo[];
  messages: Message[];
  status: GameStatus;
  active_player?: string;
}

export interface ActionResponse {
  status: boolean;
}

// Client -> Server Packages
export interface JoinRequest {
  game_id: string;
  player_name: string;
}

export interface LobbyReadyRequest {
  ready: boolean;
}

export interface StartGameRequest {}

export interface EndTurnRequest {}

export interface ChatRequest {
  text: string;
}

export interface ActionRequest {
  choice: PlayerActionChoice;
}

// ==================== API WRAPPER CLASS ====================

export class GameAPI {
  socket: Socket;
  constructor(socket: Socket) {
    this.socket = socket;
  }

  // Client → Server methods
  requestJoinGame(game_id: string, player_name: string) {
    const data: JoinRequest = { game_id: game_id, player_name: player_name };
    this.socket.emit("JOIN", data);
  }

  requestSetLobbyReady(ready: boolean) {
    const req: LobbyReadyRequest = { ready: ready };
    this.socket.emit("LOBBY_READY", req);
  }

  requestStartGame() {
    this.socket.emit("START_GAME", {});
  }

  requestEndTurn() {
    this.socket.emit("END_TURN", {});
  }

  requestSendChat(text: string) {
    const req: ChatRequest = { text: text };
    this.socket.emit("CHAT", req);
  }

  sendAction(choice: PlayerActionChoice, aknowledgement: (val: ActionResponse) => void) {
    const req: ActionRequest = { choice: choice };
    this.socket.emit("ACTION", req, aknowledgement);
  }

  // Server → Client event listener
  onInit(handler: (data: InitResponse) => void, cleanup?: any[]) {
    this.socket.on("INIT", handler);
    cleanup?.push(() => this.socket.off("INIT", handler));
  }

  onPlayers(handler: (players: PlayerInfo[]) => void, cleanup?: any[]) {
    this.socket.on("PLAYERS", handler);
    cleanup?.push(() => this.socket.off("PLAYERS", handler));
  }

  onChat(handler: (data: Message) => void, cleanup?: any[]) {
    this.socket.on("CHAT", handler);
    cleanup?.push(() => this.socket.off("CHAT", handler));
  }

  onStartGame(handler: (first_player: string) => void, cleanup?: any[]) {
    this.socket.on("START_GAME", handler);
    cleanup?.push(() => this.socket.off("START_GAME", handler));
  }

  onChangeTurn(handler: (new_active_player: string) => void, cleanup?: any[]) {
    this.socket.on("CHANGE_TURN", handler);
    cleanup?.push(() => this.socket.off("CHANGE_TURN", handler));
  }

  onChangeTurnPhase(handler: (phase: TurnPhase) => void, cleanup?: any[]) {
    this.socket.on("TURN_PHASE", handler);
    cleanup?.push(() => this.socket.off("CHANGE_TURN", handler));
  }
}
