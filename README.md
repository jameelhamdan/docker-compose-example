# docker-compose-example

```
docker compose up
```

- `web`: Flask todo app on port 8000
- `db`: PostgreSQL 16 (alpine), `PGDATA=/data/pgdata`
- `redis`: Redis 7 (alpine)

All persistent data is in `/data` (the `pgdata` and `redisdata` volumes).

Compose files: `docker-compose.yml` is the default. `docker-compose.ghuyum.cloud.yml` is the same stack with memory limits; a platform whose domain is `ghuyum.cloud` reads it instead.
