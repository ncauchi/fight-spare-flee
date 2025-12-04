# Server Listening Events

## JOIN(game_id: str, player_name: str)

client calls to actually join game after connecting to server

checks if game is full or player is already in the game

updates players state for connected clients

## LOBBY_READY(ready: bool):

client calls to let server know they are ready to start game

updates players state for connected clients

## START_GAME()

client game owner calls to start game

checks if caller has same name as game owner

checks that all players are ready

sends start game signal to connected clients

## END_TURN()

cleint sends to end their turn and advance game

sends change turn signal to connected clients

## ACTION(choice: str)

Choice:

```python
class EventType(Enum):
    FSF = auto()
    COINS = auto()
    SHOP = auto()
    FIGHT = auto()
    SPARE = auto()
    FLEE = auto()
```

client sends to do initial action on their turn

can update board, player, and/or hand for other clients depending on action

## FSF(target: int)

client sends after chooising fsf to decide what they want to do

## CHAT(player: str, text: str)

client sends to send a message in the game chat

broadcasts chat to connected players

# Server Sent Events

## Client Objects

```python
Player {
    "name": str
    "ready": bool
    "coins": int
    "num_items": int
    "health": int
}

Message {
    "player": str;
    "text": str;
}
```

## 'INIT' data : GameState

```python
    game_name: str,
    game_owner: str,
    max_players: int,
    players: list[Player],
    messages: list[Message],
    connected: bool,
    active_player: bool,
```

used to initialize client when they join a game

## "START_GAME", first_player : str

used to tell clients to move to game board, and initializes first player

## 'CHANGE_TURN', new_active : str

tells client who is the new active player when someone ends their turn

## 'CHAT', player: str, text: str

tells client when there is a new message in the game chat

## 'PLAYERS', players: list[Player]

updates client to 'public' state of all players in the game

## 'BOARD', board_snapshot

updates client to 'public' state of the board

## 'HAND', hand

updates client to the private contents of their hand
