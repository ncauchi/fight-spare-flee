import uuid


class GameMetadata:
    """
    represents a game/lobby
    """
    id : str
    name : str
    owner : str
    num_players : int
    max_players : int
    status : str # in_lobby or in_game
    ws : str




    def __init__(self, name : str, owner : str, max_players : int =4):
        self.id = str(uuid.uuid4())
        self.name = name
        self.owner = owner
        self.num_players = 0
        self.max_players = max_players
        self.status = "in_lobby"


    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "owner": self.owner,
            "status": self.status,
            "num_players": self.num_players,
            "max_players": self.max_players,
        }
    
    def to_setup(self):
        return {
            "name": self.name,
            "owner": self.owner,
            "max_players": self.max_players,
        }

    def add_player(self, player_name):
        if len(self.players) >= self.max_players:
            return False, "Room is full"
        if player_name in self.players:
            return False, "Player already in room"
        self.players.append(player_name)
        return True, "Player joined successfully"

    def remove_player(self, player_name):
        if player_name in self.players:
            self.players.remove(player_name)
            return True
        return False