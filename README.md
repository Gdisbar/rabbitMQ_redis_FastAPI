
## Sprint-0

**Start the Instance**

```bash
docker compose up --build -d 
# test using
curl localhost:8000/health
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