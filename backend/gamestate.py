class GameState:
    '''
    represents a class
    '''
    _id: str
    _name: str
    _owner: str
    _max_players: int
    players: dict[str, str] #player_name -> sid


    def __init__(self, id : str, name : str, owner : str, max_players: int):
        self._id = id
        self._name = name
        self._owner = owner
        self._max_players = max_players
        self.players = {}