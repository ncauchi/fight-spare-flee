// api_wrapper.ts
import { Socket } from "socket.io-client";

// ==================== TYPES ====================

// Server -> Client can have args, Client <- server needs to be wrapped in types

// Enums
export type PlayerActionChoice = "COINS" | "SHOP" | "COMBAT" | "END" | "CANCEL";

export type PlayerCombatChoice = "FIGHT" | "SPARE" | "FLEE" | "SELECT";

export type GameStatus = "LOBBY" | "GAME" | "END";

export type TurnPhase =
  | "CHOOSING_ACTION"
  | "COMBAT_SELECT"
  | "COMBAT_ACTION"
  | "COMBAT_FIGHT"
  | "SHOPPING"
  | "FLED"
  | "PVP"
  | "TURN_ENDED";

export type ItemTarget = "MONSTER" | "PLAYER" | "ITEM" | "NONE";

// Shared Models
export interface ItemInfo {
  name: string;
  text: string;
  target_type: ItemTarget;
}

export interface Message {
  player_name: string;
  text: string;
}

export interface MonsterInfo {
  name?: string;
  stars: number;
  max_health?: number;
  health?: number;
  spare?: number;
  flee_coins?: number;
  spare_coins?: number;
  fight_coins?: number;
}

export interface PlayerInfo {
  name: string;
  ready: boolean;
  coins: number;
  captured_stars: number[];
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

export interface BoardResponse {
  deck_size: number;
  shop_size: number;
  monsters: MonsterInfo[];
  selected_monster: number | null;
  items: ItemInfo[];
}

export interface HandResponse {
  items: ItemInfo[];
  selected_items: boolean[];
}

export interface TurnResponse {
  active: string;
  phase: TurnPhase;
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

export interface ChatRequest {
  text: string;
}

export interface ActionRequest {
  choice: PlayerActionChoice;
}

export interface CombatRequest {
  combat: PlayerCombatChoice;
  target: number;
}

export interface ItemChoiceRequest {
  item: number;
}

export interface PlayerChoiceRequest {
  player: string;
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
    console.log(`sending join request to server: ${player_name}, ${game_id}`);
  }

  requestSetLobbyReady(ready: boolean) {
    const req: LobbyReadyRequest = { ready: ready };
    this.socket.emit("LOBBY_READY", req);
    console.log(`sending lobby ready request to server ${ready}`);
  }

  requestStartGame() {
    this.socket.emit("START_GAME", {});
    console.log(`sending start game request to server`);
  }

  requestSendChat(text: string) {
    const req: ChatRequest = { text: text };
    this.socket.emit("CHAT", req);
    console.log(`sending chat request to server ${text}`);
  }

  requestSendAction(choice: PlayerActionChoice) {
    const req: ActionRequest = { choice: choice };
    this.socket.emit("ACTION", req);
    console.log(`sending action request to server ${choice}`);
  }

  requestSendCombat(choice: PlayerCombatChoice, target: number) {
    const req: CombatRequest = { combat: choice, target: target };
    this.socket.emit("COMBAT", req);
    console.log(`sending combat request to server: ${choice}, ${target}`);
  }

  requestSendItemChoice(item: number) {
    const req: ItemChoiceRequest = { item: item };
    this.socket.emit("ITEM_CHOICE", req);
    console.log(`sending item select request to server ${item}`);
  }

  requestSendPlayerChoice(target: string) {
    const req: PlayerChoiceRequest = { player: target };
    this.socket.emit("PLAYER_CHOICE", req);
    console.log(`sending player select request to server ${target}`);
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

  onTurn(handler: (active_player: string, TurnPhase: TurnPhase) => void, cleanup?: any[]) {
    this.socket.on("CHANGE_TURN", (data: TurnResponse) => handler(data.active, data.phase));
    cleanup?.push(() => this.socket.off("CHANGE_TURN", handler));
  }

  onBoard(
    handler: (
      deck_size: number,
      shop_size: number,
      monsters: MonsterInfo[],
      selected_monster: number | null,
      items: ItemInfo[],
    ) => void,
    cleanup?: any[],
  ) {
    this.socket.on("BOARD", (data: BoardResponse) =>
      handler(data.deck_size, data.shop_size, data.monsters, data.selected_monster, data.items),
    );
    cleanup?.push(() => this.socket.off("BOARD", handler));
  }

  onHandUpdate(handler: (items: ItemInfo[], selcted_items: boolean[]) => void, cleanup?: any[]) {
    this.socket.on("ITEMS", (data: HandResponse) => handler(data.items, data.selected_items));
    cleanup?.push(() => this.socket.off("ITEMS", handler));
  }
}
