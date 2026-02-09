# Authentication System Comparison

**Current State vs. Production Architecture**

This document compares the current simple token authentication with the proposed Google-level OAuth 2.1 + JWT architecture.

---

## Current System (Simple Token)

### How It Works Today

```
┌─────────────────────────────────────────────────┐
│ Configuration (.env):                           │
│   FOODLOG_TOKEN=my-secret-token                 │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│ Request:                                        │
│   GET /api/meals                                │
│   Authorization: Bearer my-secret-token         │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│ Server Validation (src/fcp/auth/local.py):     │
│   expected = os.environ.get("FOODLOG_TOKEN")    │
│   if token == expected:                         │
│       return admin user                         │
│   else:                                         │
│       return demo user (read-only)              │
└─────────────────────────────────────────────────┘
```

### Current Code

```python
# src/fcp/auth/local.py (simplified)
def authenticate(authorization: str) -> AuthenticatedUser:
    # Extract "Bearer <token>"
    token = authorization.split()[1]

    # Compare with environment variable
    expected_token = os.environ.get("FOODLOG_TOKEN")

    if expected_token and token == expected_token:
        # Valid token → Admin user
        return AuthenticatedUser(user_id="admin", role=UserRole.AUTHENTICATED)

    # Invalid/missing → Demo user (read-only)
    return AuthenticatedUser(user_id=DEMO_USER_ID, role=UserRole.DEMO)
```

### Pros ✅

- **Simple**: Easy to understand and implement
- **Fast**: String comparison is instant
- **No dependencies**: No Redis, no databases, no crypto libraries
- **Good for hackathon**: Quick to set up and demo

### Cons ❌

- **Single token for all users**: Everyone shares the same token
- **No user isolation**: Can't have multiple independent users
- **Token can't expire**: Once set, it's valid forever
- **Can't revoke**: If token leaks, must change env var and restart
- **No logout**: Token remains valid even after "logout"
- **String comparison**: Anyone with the token string can use it
- **Not production-ready**: Doesn't scale beyond single-user demos

### Current User Experience

```
Developer sets FOODLOG_TOKEN in .env:
  FOODLOG_TOKEN=abc123

All users use the same token:
  User 1 → Authorization: Bearer abc123
  User 2 → Authorization: Bearer abc123
  User 3 → Authorization: Bearer abc123

All users see/modify the same data.
No way to have separate user accounts.
```

---

## Proposed System (OAuth 2.1 + JWT)

### How It Works (New Architecture)

```
┌─────────────────────────────────────────────────┐
│ User Registration:                              │
│   POST /auth/register                           │
│   { "email": "user@example.com",                │
│     "password": "SecurePass123!" }              │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│ Server Creates Account:                         │
│   1. Hash password with bcrypt                  │
│   2. Store in auth.db                           │
│   3. Generate access + refresh JWTs             │
│   4. Return tokens to user                      │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│ User Makes Request:                             │
│   GET /api/meals                                │
│   Authorization: Bearer eyJhbGc...              │
│                        ↑                        │
│                    JWT Token                    │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│ Server Validates JWT:                           │
│   1. Verify signature with public key           │
│   2. Check expiration (15 min for access token) │
│   3. Check not revoked (Redis blacklist)        │
│   4. Extract user_id from token                 │
│   5. Load user's isolated database              │
│   6. Return user's data only                    │
└─────────────────────────────────────────────────┘
```

### New Code Architecture

```python
# src/fcp/auth/jwt_manager.py
class JWTManager:
    def create_access_token(self, user_id: str) -> str:
        payload = {
            "sub": user_id,
            "exp": now + timedelta(minutes=15),
            "type": "access"
        }
        return jwt.encode(payload, private_key, algorithm="RS256")

    def validate_token(self, token: str) -> dict:
        # Cryptographic verification (can't be forged)
        claims = jwt.decode(token, public_key, algorithms=["RS256"])

        # Check expiration
        if claims["exp"] < time.time():
            raise TokenExpiredError()

        # Check blacklist
        if redis.exists(f"blacklist:{claims['jti']}"):
            raise TokenRevokedError()

        return claims

# src/fcp/auth/service.py
class AuthService:
    async def register(self, email: str, password: str):
        # Hash password
        password_hash = bcrypt.hashpw(password, bcrypt.gensalt())

        # Create user record
        user_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO users (user_id, email, password_hash) VALUES (?, ?, ?)",
            (user_id, email, password_hash)
        )

        # Generate tokens
        access_token = jwt_manager.create_access_token(user_id)
        refresh_token = jwt_manager.create_refresh_token(user_id)

        return {
            "user_id": user_id,
            "access_token": access_token,
            "refresh_token": refresh_token
        }

    async def login(self, email: str, password: str):
        # Lookup user
        user = db.execute(
            "SELECT user_id, password_hash FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        # Verify password
        if not bcrypt.checkpw(password, user["password_hash"]):
            raise InvalidCredentialsError()

        # Generate new tokens
        access_token = jwt_manager.create_access_token(user["user_id"])
        refresh_token = jwt_manager.create_refresh_token(user["user_id"])

        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
```

### Pros ✅

- **Multi-user**: Each user has their own account
- **User isolation**: Each user's data in separate database
- **Cryptographically secure**: Tokens can't be forged
- **Token expiration**: Access tokens expire after 15 minutes
- **Revocation**: Can invalidate tokens (logout)
- **Refresh rotation**: Prevents token replay attacks
- **Scalable**: Works with millions of users
- **Industry standard**: OAuth 2.1 + JWT (same as Google, GitHub, etc.)
- **Production-ready**: Rate limiting, audit logging, etc.

### Cons ❌

- **More complex**: ~400 lines of code vs ~50
- **Dependencies**: Redis, cryptography libraries
- **Infrastructure**: Need Redis server
- **Setup time**: 2 hours vs 5 minutes
- **More to test**: Token flows, expiration, refresh, revocation

### New User Experience

```
User 1 registers:
  POST /auth/register
  { "email": "alice@example.com", "password": "..." }

  Receives tokens:
    access_token: eyJhbGc... (contains user_id: user_abc123)
    refresh_token: eyJhbGc... (long-lived)

User 1 makes requests:
  GET /api/meals
  Authorization: Bearer eyJhbGc...

  Server extracts user_id: user_abc123
  Opens database: data/users/user_abc123/foodlog.db
  Returns Alice's meals only

User 2 registers:
  POST /auth/register
  { "email": "bob@example.com", "password": "..." }

  Receives different tokens:
    access_token: eyJhbGc... (contains user_id: user_def456)
    refresh_token: eyJhbGc...

User 2 makes requests:
  GET /api/meals
  Authorization: Bearer eyJhbGc...

  Server extracts user_id: user_def456
  Opens database: data/users/user_def456/foodlog.db
  Returns Bob's meals only

Alice and Bob's data is completely isolated!
```

---

## Side-by-Side Comparison

| Feature | Current (Simple Token) | Proposed (OAuth + JWT) |
|---------|----------------------|----------------------|
| **Authentication** | String comparison | RSA signature verification |
| **Multi-user** | ❌ Single token for all | ✅ Token per user |
| **User isolation** | ❌ Shared data | ✅ Database per user |
| **Token expiration** | ❌ Never expires | ✅ 15 min (access), 7 days (refresh) |
| **Token revocation** | ❌ Can't revoke | ✅ Redis blacklist |
| **Logout** | ❌ Token stays valid | ✅ Token blacklisted |
| **Security** | ❌ Static string | ✅ Cryptographic signatures |
| **Scalability** | ❌ Single user | ✅ Millions of users |
| **Code complexity** | 50 lines | 400 lines |
| **Dependencies** | None | Redis, cryptography |
| **Setup time** | 5 minutes | 2 hours |
| **Production ready** | ❌ Demo only | ✅ Yes |

---

## What Changes in the Codebase

### New Files Created

```
src/fcp/auth/
  jwt_manager.py           # JWT token creation/validation
  service.py               # User registration/login
  blacklist.py             # Redis token revocation
  password.py              # Bcrypt password hashing
  middleware.py            # FastAPI auth dependency

src/fcp/routes/
  auth.py                  # Auth endpoints (/register, /login, etc.)

src/fcp/database/
  user_db_manager.py       # Database-per-user management

data/
  auth.db                  # Central auth database
  users/                   # Per-user databases
    {user_id}/
      foodlog.db           # User's data
      metadata.json        # User settings
```

### Modified Files

```
src/fcp/routes/*.py
  # All route handlers updated to:
  async def handler(user: AuthenticatedUser = Depends(get_current_user)):
      # Now have access to user.user_id
      db = user_db_manager.get_connection(user.user_id)
      # Query user-specific database

src/fcp/services/*.py
  # All services updated to accept user_id parameter:
  async def get_meals(user_id: str):
      db = user_db_manager.get_connection(user_id)
      return db.execute("SELECT * FROM meals").fetchall()

pyproject.toml
  # Add dependencies:
  dependencies = [
    "pyjwt[crypto]",
    "passlib[bcrypt]",
    "redis",
    "cryptography"
  ]

.env
  # Add configuration:
  REDIS_URL=redis://localhost:6379
  JWT_PRIVATE_KEY_PATH=/path/to/private_key.pem
  JWT_PUBLIC_KEY_PATH=/path/to/public_key.pem
```

### Database Schema Changes

```sql
-- New: Central auth database (data/auth.db)
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,           -- UUID
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,        -- bcrypt hash
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Existing: Per-user database (data/users/{user_id}/foodlog.db)
-- No changes needed! Each user gets their own isolated copy.
```

---

## Infrastructure Requirements

### Current (Simple Token)

```
None! Just environment variable:
  FOODLOG_TOKEN=abc123
```

### Proposed (OAuth + JWT)

**Local Development:**
```
1. Redis server:
   docker run -d -p 6379:6379 redis:latest

2. RSA key pair:
   openssl genrsa -out private_key.pem 2048
   openssl rsa -in private_key.pem -pubout -out public_key.pem

3. SQLite databases:
   data/auth.db (central)
   data/users/{user_id}/foodlog.db (per-user)
```

**Production:**
```
1. Google Cloud Memorystore for Redis:
   - Size: 1 GB
   - Cost: ~$45/month
   - Auto-scaling, high availability

2. Google Cloud Secret Manager:
   - Store RSA private key
   - Store RSA public key
   - Cost: ~$1/month

3. Google Cloud Storage:
   - Store SQLite databases
   - Cost: ~$0.02/GB/month

Total Cost: ~$50/month for production
```

---

## Migration Path

### Phase 1: Add OAuth Alongside Current Auth (Backward Compatible)

```python
# src/fcp/auth/middleware.py
async def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return demo_user()

    token = auth_header.split()[1]

    # Try new JWT validation first
    try:
        claims = jwt_manager.validate_token(token)
        return AuthenticatedUser(
            user_id=claims["sub"],
            role=UserRole.AUTHENTICATED
        )
    except JWTError:
        pass

    # Fallback to old simple token validation
    expected = os.environ.get("FOODLOG_TOKEN")
    if expected and token == expected:
        return AuthenticatedUser(
            user_id="admin",
            role=UserRole.AUTHENTICATED
        )

    # Neither worked → demo user
    return demo_user()
```

**Benefit:** Both old and new auth work simultaneously during migration.

### Phase 2: Database-Per-User (Requires Migration)

```python
# Migration script
def migrate_to_per_user_databases():
    # Read old shared database
    old_db = sqlite3.connect("data/foodlog.db")

    # Get all unique user_ids
    user_ids = old_db.execute("SELECT DISTINCT user_id FROM meals").fetchall()

    for (user_id,) in user_ids:
        # Create user directory
        user_dir = Path(f"data/users/{user_id}")
        user_dir.mkdir(parents=True, exist_ok=True)

        # Create user's database
        user_db = sqlite3.connect(user_dir / "foodlog.db")

        # Copy user's data
        user_db.execute("CREATE TABLE meals (...)")
        old_db.execute("INSERT INTO meals SELECT * FROM meals WHERE user_id = ?", (user_id,))

        user_db.commit()

    # Backup old database
    shutil.move("data/foodlog.db", "data/foodlog.db.backup")
```

### Phase 3: Remove Old Auth (Breaking Change)

```python
# Remove simple token fallback
async def get_current_user(request: Request):
    token = extract_token(request)
    claims = jwt_manager.validate_token(token)  # JWT only
    return AuthenticatedUser(user_id=claims["sub"])
```

---

## Performance Comparison

### Request Latency

**Current (Simple Token):**
```
String comparison: <0.1ms
Total overhead: ~0.1ms
```

**Proposed (OAuth + JWT):**
```
JWT signature verification: ~1-2ms
Redis blacklist check: ~0.5-1ms
Total overhead: ~2-5ms
```

**Verdict:** Negligible difference (<5ms) for the added security.

### Throughput

**Current:**
- No bottlenecks (stateless string comparison)
- Scales infinitely

**Proposed:**
- Redis bottleneck at ~100,000 requests/second (single instance)
- Can scale horizontally with Redis cluster
- Still handles millions of requests/day

---

## Security Comparison

### Attack Vectors

| Attack | Current | Proposed |
|--------|---------|----------|
| **Token theft** | ❌ Token valid forever | ✅ Expires in 15 min |
| **Token replay** | ❌ Reusable indefinitely | ✅ Refresh rotation prevents |
| **Token forgery** | ❌ Easy (just a string) | ✅ Impossible (RSA signature) |
| **Brute force** | ❌ No rate limiting | ✅ Redis rate limiting |
| **Session fixation** | ❌ No session concept | ✅ New tokens on login |
| **CSRF** | ⚠️ Depends on client | ✅ SameSite cookies |
| **XSS** | ⚠️ Depends on client | ✅ httpOnly cookies |

### Compliance

| Standard | Current | Proposed |
|----------|---------|----------|
| **OAuth 2.1** | ❌ No | ✅ Yes |
| **OWASP Top 10** | ⚠️ Partial | ✅ Full |
| **SOC 2** | ❌ No | ✅ Yes (with audit logs) |
| **GDPR** | ⚠️ No user isolation | ✅ Right to deletion |
| **HIPAA** | ❌ No | ✅ With encryption at rest |

---

## Recommendation

### For Hackathon (Feb 9 Deadline)

**If < 2 days remaining:**
- ✅ Keep current simple token system
- ✅ Focus on Gemini 3 features (judging priority)
- ✅ Document "production roadmap" in README
- ✅ Mention OAuth + JWT as "next step" in demo video

**If 2+ days remaining:**
- ✅ Implement basic OAuth + JWT (Phase 1)
- ✅ Skip database-per-user for now (can demo with shared DB)
- ✅ Adds "production-ready architecture" talking point for judges
- ⚠️ Allocate 2-4 hours for implementation + testing

### Post-Hackathon (Production)

**Must-haves:**
1. OAuth 2.1 + JWT authentication
2. Database-per-user isolation
3. Redis rate limiting
4. Token refresh rotation
5. Audit logging

**Timeline:** 1-2 weeks for full implementation

---

## Next Steps

1. **Review** this comparison with team
2. **Decide** on timeline (hackathon vs post-hackathon)
3. **If proceeding:** Start with Phase 1 (OAuth + JWT only)
4. **If deferring:** Document in roadmap for post-hackathon

---

## References

- [OAuth 2.1 Specification](https://oauth.net/2.1/)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
- [Google Cloud Auth Guide](https://cloud.google.com/docs/authentication)
- See `docs/authentication-architecture.md` for full implementation details
- See `docs/auth-quickstart.md` for practical setup guide
