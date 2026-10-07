
## Sprint-0

**Start the Instance**

```bash
# delete volume & any broken pg_primary data
docker compose down -v
# start instance
docker compose up --build -d 
# check logs - in pgadmin4 
docker compose logs -f pg-primary
# test on docker (pg-primary: The specific service/container name defined in your docker-compose.yml)
docker compose exec pg-primary psql -U app -d appdb -c "SELECT id, username FROM users;"
# testing on postman
localhost:8000/health



```

```bash
.
├── docker-compose.yml
├── README.md
├── postgres/
│   └── seed.sql
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── config.py
│       ├── security.py
│       ├── redis_client.py
│       ├── ratelimit.lua
│       ├── rabbit.py
│       ├── deps.py
│       ├── schemas.py
│       ├── main.py
│       └── routers/
│           ├── __init__.py
│           ├── auth.py
│           ├── items.py
│           └── me.py
└── worker/
    ├── Dockerfile
    ├── requirements.txt
    └── worker/
        ├── __init__.py
        ├── config.py
        ├── db.py
        ├── breaker.py
        ├── handlers.py
        └── main.py

```