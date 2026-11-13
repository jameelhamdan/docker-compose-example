# docker-compose-example

```
docker compose up
```

- `web`: Flask todo app on port 8000: React single-page UI (loaded from a CDN, no build step), JSON API, image uploads
- `db`: PostgreSQL 16 (alpine), `PGDATA=/data/pgdata`
- `redis`: Redis 7 (alpine)

All persistent data is under `/data`: `web` keeps uploaded images in `/data/uploads` (`webdata` volume), `db` keeps PostgreSQL in `/data/pgdata` (`pgdata` volume), `redis` uses `/data` (`redisdata` volume). The browser needs internet access to load React from unpkg.

Compose files: `docker-compose.yml` is the default. `docker-compose.ghuyum.cloud.yml` is the same stack with memory limits; a platform whose domain is `ghuyum.cloud` reads it instead.
