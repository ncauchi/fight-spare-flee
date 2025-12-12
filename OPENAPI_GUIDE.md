# OpenAPI Format Guide for Fight Spare Flee

## Table of Contents
1. [OpenAPI Structure Overview](#openapi-structure-overview)
2. [Field Explanations](#field-explanations)
3. [Separating REST vs SocketIO](#separating-rest-vs-socketio)
4. [Separating CLIENT vs SERVER](#separating-client-vs-server)
5. [Common Patterns](#common-patterns)

---

## OpenAPI Structure Overview

```yaml
openapi: 3.0.0           # Version of OpenAPI spec
info:                    # Metadata about your API
  title: ...
  version: ...
  description: ...

components:              # Reusable schemas (your data types)
  schemas:
    Player: ...          # Define data structures here
    Item: ...

paths:                   # REST API endpoints
  /api/games:            # HTTP routes
    post: ...
    get: ...

x-socketio-events:       # Custom section for SocketIO (not standard OpenAPI)
  client-to-server: ...
  server-to-client: ...
```

---

## Field Explanations

### Top-Level Fields

#### `openapi`
The version of the OpenAPI specification you're using. Always use `3.0.0` or higher.

#### `info`
Metadata about your API:
```yaml
info:
  title: Fight Spare Flee API        # Name of your API
  version: 1.0.0                      # Your API version
  description: Brief explanation      # Optional documentation
```

#### `components.schemas`
**This is where you define all your data types.** Think of this as your type definitions that both Python and TypeScript will generate from.

```yaml
components:
  schemas:
    Player:              # Type name
      type: object       # It's an object (like a class/interface)
      required:          # Which fields are mandatory
        - name
        - ready
      properties:        # The actual fields
        name:
          type: string   # Field type
          example: "Alice"  # Example value (helpful for docs)
        ready:
          type: boolean
```

**Key property types:**
- `string` → Python `str`, TypeScript `string`
- `integer` → Python `int`, TypeScript `number`
- `number` → Python `float`, TypeScript `number`
- `boolean` → Python `bool`, TypeScript `boolean`
- `array` → Python `list`, TypeScript `Array`
- `object` → Python `dict`, TypeScript `object`

#### `paths`
Defines REST API HTTP endpoints:

```yaml
paths:
  /api/games:           # URL path
    post:               # HTTP method (GET, POST, PUT, DELETE, etc.)
      summary: Create a new game
      requestBody:      # What client sends
        required: true
        content:
          application/json:
            schema:     # Structure of request body
              type: object
              properties:
                game_name:
                  type: string
      responses:        # What server responds with
        '200':          # HTTP status code
          description: Success
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CreateGameResponse'
        '400':
          description: Bad request
```

---

## Separating REST vs SocketIO

### REST API (HTTP)
**When to use:** One-off requests/responses (create game, fetch status, etc.)

Define in the `paths:` section:
```yaml
paths:
  /api/games/{game_id}:
    get:
      summary: Get game info
      parameters:
        - name: game_id
          in: path          # Path parameter from URL
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Success
```

**How it works:**
- Client makes HTTP request: `GET /api/games/123`
- Server responds once with data
- Connection closes

---

### SocketIO (Real-time Events)
**When to use:** Real-time bidirectional communication (game updates, player actions, etc.)

Since **OpenAPI doesn't officially support SocketIO**, we use custom `x-` extension fields to document it:

```yaml
x-socketio-events:
  client-to-server:     # Events client emits
    events:
      player_action:    # Event name
        description: Player takes an action
        payload:        # Data sent with event
          $ref: '#/components/schemas/PlayerActionRequest'

  server-to-client:     # Events server emits
    events:
      game_state:       # Event name
        payload:
          $ref: '#/components/schemas/GameStateUpdateEvent'
```

**How it works:**
- Client: `socket.emit('player_action', { action: 'fight' })`
- Server: `socket.emit('game_state', { ... })`
- Persistent bidirectional connection

**Note:** The `x-socketio-events` section is for documentation. You'll need to manually implement SocketIO event handlers, but the payload types will be auto-generated.

---

## Separating CLIENT vs SERVER

Use **naming conventions** in your schema names to indicate direction:

### Naming Conventions

```yaml
# CLIENT → SERVER (requests)
JoinGameRequest:          # Client sends this
  type: object
  properties:
    player_name:
      type: string

PlayerActionRequest:      # Client sends this
  type: object
  properties:
    action:
      type: string

# SERVER → CLIENT (responses)
CreateGameResponse:       # Server responds with this
  type: object
  properties:
    game_id:
      type: string

GameStateUpdateEvent:     # Server broadcasts this
  type: object
  properties:
    players:
      type: array
```

### Indicating Direction in Descriptions

Always add direction arrows in descriptions:
```yaml
JoinGameRequest:
  description: "CLIENT → SERVER: Request to join a game"

GameStateUpdateEvent:
  description: "SERVER → CLIENT: Full game state update"
```

### For REST Endpoints

```yaml
paths:
  /api/games:
    post:
      description: "CLIENT → SERVER: Creates a new game lobby"
      requestBody:        # CLIENT → SERVER
        schema:
          $ref: '#/components/schemas/CreateGameRequest'
      responses:
        '200':            # SERVER → CLIENT
          schema:
            $ref: '#/components/schemas/CreateGameResponse'
```

### For SocketIO Events

Separate by section:
```yaml
x-socketio-events:
  client-to-server:       # CLIENT → SERVER
    events:
      join_game: ...
      player_action: ...

  server-to-client:       # SERVER → CLIENT
    events:
      game_state: ...
      player_joined: ...
```

---

## Common Patterns

### 1. Referencing Other Schemas

Use `$ref` to reference schemas defined in `components.schemas`:

```yaml
Player:
  type: object
  properties:
    items:
      type: array
      items:
        $ref: '#/components/schemas/Item'  # Reference Item schema
```

This creates: `Player { items: Item[] }`

### 2. Optional vs Required Fields

```yaml
Player:
  required:      # These fields MUST be present
    - name
    - ready
  properties:
    name:        # Required
      type: string
    ready:       # Required
      type: boolean
    coins:       # Optional (not in required list)
      type: integer
      default: 0
```

### 3. Enums (Limited Set of Values)

```yaml
status:
  type: string
  enum: [in_lobby, in_game, ended]  # Only these values allowed
```

Generates Python: `Literal["in_lobby", "in_game", "ended"]`
Generates TypeScript: `"in_lobby" | "in_game" | "ended"`

### 4. Validation Constraints

```yaml
health:
  type: integer
  minimum: 0       # Must be >= 0
  maximum: 4       # Must be <= 4

player_name:
  type: string
  minLength: 1     # Must have at least 1 character
  maxLength: 20    # Max 20 characters
```

### 5. Nested Objects (Inline)

```yaml
BoardState:
  type: object
  properties:
    deck:
      type: object      # Nested object defined inline
      properties:
        size:
          type: integer
        top_card_stars:
          type: integer
```

### 6. Arrays

```yaml
# Array of primitives
captured_stars:
  type: array
  items:
    type: integer

# Array of objects
players:
  type: array
  items:
    $ref: '#/components/schemas/Player'
```

---

## Quick Reference

| YAML Type | Python (Pydantic) | TypeScript |
|-----------|-------------------|------------|
| `string` | `str` | `string` |
| `integer` | `int` | `number` |
| `number` | `float` | `number` |
| `boolean` | `bool` | `boolean` |
| `array` | `list[T]` | `Array<T>` |
| `object` | `dict` or custom class | `object` or interface |
| `enum` | `Literal["a", "b"]` | `"a" \| "b"` |
| `$ref` | References other class | References other interface |

---

## Generating Code

After updating `api_schema.yaml`:

```bash
# Generate Python types
datamodel-codegen \
  --input api_schema.yaml \
  --output backend/api_types.py \
  --output-model-type pydantic_v2.BaseModel

# Generate TypeScript types
npx openapi-typescript api_schema.yaml \
  --output client/src/api-types.ts
```

Both backend and frontend stay in sync automatically!
