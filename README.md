# Fight Spare Flee

## Game made by Noah Cauchi and no one else

## To run Dev Build

1. Set .env file in project directory

```
in fight-spare-flee/.env

POSTGRES_PASSWORD= ___
JWT_SECRET= ___

POSTGRES_USER= ___
POSTGRES_DB= ___
DB_FOLDER= ___

GAMES_API_URL=http://game_manager:5001
LOBBY_API_URL=http://room_manager:5000
```

2. Run `docker-compose up --build`
