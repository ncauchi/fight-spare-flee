# Room Manager API

Simple Flask API for managing game rooms.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the server:

```bash
python room_manager.py
```

Server runs on `http://localhost:5000`

## API Endpoints

### GET /rooms

List all available rooms.

**Response:**

```json
[
  {
    "id": "uuid",
    "name": "Room Name",
    "owner": "player1",
    "players": ["player1"],
    "maxPlayers": 4,
    "createdAt": "2025-01-01T12:00:00"
  }
]
```

### POST /rooms

Create a new room.

**Request:**

```json
{
  "name": "My Room",
  "owner": "player1",
  "maxPlayers": 4
}
```

**Response:** Room object (201)

### GET /rooms/:room_id

Get details of a specific room.

**Response:** Room object (200)

### POST /rooms/:room_id/join

Join a room.

**Request:**

```json
{
  "playerName": "player2"
}
```

**Response:** Room object (200)

### POST /rooms/:room_id/leave

Leave a room.

**Request:**

```json
{
  "playerName": "player2"
}
```

**Response:** Room object (200)

### DELETE /rooms/:room_id

Delete a room (owner only).

**Request:**

```json
{
  "playerName": "owner"
}
```

**Response:** Success message (200)

### GET /health

Health check endpoint.

**Response:**

```json
{
  "status": "ok",
  "rooms": 0
}
```
