from typing import Literal

class GameState:
    '''
    represents a class
    '''
    _id: str
    _name: str
    _owner: str
    _max_players: int
    players: dict[str, str] #player_name -> sid
    status: Literal["in_lobby", "in_game", "ended"]


    def __init__(self, id : str, name : str, owner : str, max_players: int):
        self._id = id
        self._name = name
        self._owner = owner
        self._max_players = max_players
        self.players = {}
        self.status = "in_lobby"

    def to_status(self):
        return {
            "num_players": len(self.players),
            "status": self.status
        }