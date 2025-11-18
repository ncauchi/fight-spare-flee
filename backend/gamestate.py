from typing import Literal

class Player:
    name: str
    lobby_ready: bool
    session: str

    def __init__(self, name: str, sid: str):
        self.name = name
        self.sid = sid
        self.lobby_ready = False

class GameState:
    '''
    represents a class
    '''
    _id: str
    _name: str
    _owner: str
    _max_players: int
    players: dict[str, Player] #player_name -> Player
    status: Literal["in_lobby", "in_game", "ended"]
    active_player: int
    _turn_order: list[str]


    def __init__(self, id : str, name : str, owner : str, max_players: int):
        self._id = id
        self._name = name
        self._owner = owner
        self._max_players = max_players
        self.players = {}
        self.status = "in_lobby"

    def to_status(self):
        return {
            "num_players": len(self.players.keys()),
            "status": self.status
        }
    
    def start(self):
        self.status = "in_game"
        order = [p for p in self.players.keys()]
        self._turn_order = order
        self.active_player = 0
        return self._turn_order[0]

    def advance_active_player(self):
        curr = self.active_player
        new_player = (curr + 1)%len(self._turn_order)
        self.active_player = new_player
        return self._turn_order[new_player]

    

