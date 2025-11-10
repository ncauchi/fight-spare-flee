from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
from datetime import datetime

app = Flask(__name__)
CORS(app)

class Room:
    def __init__(self, name, owner, max_players=4):
        self.id = str(uuid.uuid4())
        self.name = name
        self.owner = owner
        self.players = [owner]
        self.max_players = max_players

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "owner": self.owner,
            "players": self.players,
            "maxPlayers": self.max_players,
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

# In-memory storage for rooms
dev_room = Room("dev_room", "god")
rooms = {dev_room.id: dev_room}


@app.route("/rooms", methods=["GET"])
def get_rooms():
    """Get all available rooms"""
    rooms_list = [room.to_dict() for room in rooms.values()]
    return jsonify(rooms_list), 200


@app.route("/rooms", methods=["POST"])
def create_room():
    """Create a new room"""
    data = request.get_json()

    if not data or "name" not in data or "owner" not in data:
        return jsonify({"error": "Missing required fields: name, owner"}), 400

    room = Room(
        name=data["name"],
        owner=data["owner"],
        max_players=data.get("maxPlayers", 4),
    )

    rooms[room.id] = room

    return jsonify({"id": room.id}), 201


@app.route("/rooms/<room_id>", methods=["GET"])
def get_room(room_id):
    """Get details of a specific room"""
    room = rooms.get(room_id)

    if not room:
        return jsonify({"error": "Room not found"}), 404

    return jsonify(room.to_dict()), 200


@app.route("/rooms/<room_id>/join", methods=["POST"])
def join_room(room_id):
    """Join a room"""
    room = rooms.get(room_id)

    if not room:
        return jsonify({"error": f"Room {room_id} not found"}), 404

    data = request.get_json()
    if not data or "playerName" not in data:
        return jsonify({"error": "Missing required field: playerName"}), 400

    success, message = room.add_player(data["playerName"])

    if not success:
        return jsonify({"error": message}), 400

    return jsonify({"message": message, "room": room.to_dict()}), 200


@app.route("/rooms/<room_id>/leave", methods=["POST"])
def leave_room(room_id):
    """Leave a room"""
    room = rooms.get(room_id)

    if not room:
        return jsonify({"error": "Room not found"}), 404

    data = request.get_json()
    if not data or "playerName" not in data:
        return jsonify({"error": "Missing required field: playerName"}), 400

    if room.remove_player(data["playerName"]):
        # If room is empty, delete it
        if len(room.players) == 0:
            del rooms[room_id]
            return jsonify({"message": "Left room, room deleted (empty)"}), 200

        return jsonify({"message": "Left room", "room": room.to_dict()}), 200

    return jsonify({"error": "Player not in room"}), 400


@app.route("/rooms/<room_id>", methods=["DELETE"])
def delete_room(room_id):
    """Delete a room (owner only)"""
    room = rooms.get(room_id)

    if not room:
        return jsonify({"error": "Room not found"}), 404

    data = request.get_json()
    if not data or "playerName" not in data:
        return jsonify({"error": "Missing required field: playerName"}), 400

    if room.owner != data["playerName"]:
        return jsonify({"error": "Only room owner can delete the room"}), 403

    del rooms[room_id]
    return jsonify({"message": "Room deleted"}), 200


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "rooms": len(rooms)}), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)


