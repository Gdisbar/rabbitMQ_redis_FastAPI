
## Sprint-1

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

## Sprint -2

```python
import secrets
# URL-Safe Base64 Token - put it in config.py,docker-compose.yml
url_token = secrets.token_urlsafe(32)
# Here it's - Bearer K2yBfQFgPnFvCBecUHHqb4h8geNPs3aqsvs4N1A9ouA
```

iat, jti, exp, and sub are standard registered claims used in the payload of a JSON Web Token (JWT) to convey specific metadata about the token and the user

    • iat (Issued At): Records the Unix timestamp of when the token was created, helping systems calculate the token's age.
    • jti (JWT ID): Provides a unique string identifier for the token, typically used to prevent replay attacks or handle token revocation.
    • exp (Expiration Time): Sets the Unix timestamp after which the token becomes invalid and must be rejected.
    • sub (Subject): Identifies the principal entity the token is about, usually representing the unique user ID

```bash
# remove previous volume (if getting error)
docker compose down 
docker compose up --build -d
docker compose logs -f api 

# re-building particular part
docker compose up -d --build api

# get registered users (seed.sql)
docker compose exec pg-primary psql -U user123 -d appdb -c "SELECT id, username, left(password_hash,7) AS hash_prefix FROM users;"

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