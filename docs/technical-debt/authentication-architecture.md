# FCP Authentication Architecture

**Status:** Planning / Research Phase
**Target:** Google Software-Level Production Quality
**Last Updated:** 2026-02-07

## Table of Contents

- [Overview](#overview)
- [Architecture Decisions](#architecture-decisions)
- [HTTP API Authentication](#http-api-authentication)
- [User Data Isolation](#user-data-isolation)
- [Rate Limiting](#rate-limiting)
- [MCP Server Security](#mcp-server-security)
- [Implementation Roadmap](#implementation-roadmap)
- [Tech Stack](#tech-stack)
- [References](#references)

---

## Overview

This document outlines the production-grade authentication and security architecture for FCP FCP (Food Context Protocol). The design follows industry best practices from Google Cloud, OAuth 2.1 specification, and MCP security guidelines.

### Design Principles

1. **Security by Default** - All endpoints require authentication; fail closed, not open
2. **Zero Trust** - Validate every request; treat all inputs as untrusted
3. **User Isolation** - Complete data separation between users
4. **Performance** - Sub-100ms auth overhead using Redis caching
5. **Scalability** - Designed for millions of users (database-per-tenant pattern proven at iCloud scale)

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                            │
│  (Mobile App, CLI, MCP Client)                                  │
└────────────────┬────────────────────────────────────────────────┘
                 │ OAuth 2.1 Flow
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Authorization Server                         │
│  - JWT Token Generation (RS256)                                 │
│  - Refresh Token Rotation                                       │
│  - Token Revocation (Redis Blacklist)                           │
└────────────────┬────────────────────────────────────────────────┘
                 │ Access Token (15 min)
                 │ Refresh Token (7 days)
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                          │
│  - Token Validation Middleware                                  │
│  - Rate Limiting (Redis Token Bucket)                           │
│  - Audit Logging                                                │
└────────────────┬────────────────────────────────────────────────┘
                 │ user_id extracted from JWT
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Data Isolation Layer                          │
│  - Database-per-tenant (SQLite)                                 │
│  - User-specific database: data/users/{user_id}/foodlog.db     │
│  - Complete data isolation                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Architecture Decisions

### HTTP API: OAuth 2.1 + JWT

**Decision:** Use OAuth 2.1 with JWT tokens (RS256 asymmetric signing)

**Rationale:**
- Industry standard for API authentication
- Google Cloud's recommended approach
- RS256 allows public key distribution for token verification
- Stateless authentication (no server-side sessions)
- Supports refresh token rotation for enhanced security

**Trade-offs:**
- ✅ Pro: Scalable, stateless, industry-standard
- ✅ Pro: Tokens can be validated without DB lookup
- ⚠️ Con: Requires Redis for token blacklist (revocation)
- ⚠️ Con: More complex than simple API keys

### User Isolation: Database-Per-Tenant

**Decision:** Each user gets their own SQLite database

**Rationale:**
- Complete data isolation (no risk of cross-user data leakage)
- Proven at massive scale (iCloud uses millions of SQLite databases)
- Simple permissions model (no row-level security needed)
- Easy GDPR compliance (delete user = delete their database)
- Efficient backups and migrations (per-user granularity)

**Trade-offs:**
- ✅ Pro: Maximum security, simple permissions, easy backups
- ✅ Pro: Scales to millions of users (proven pattern)
- ⚠️ Con: Cross-user analytics require ATTACH operations
- ⚠️ Con: More complex migrations (must run on all user DBs)

### Rate Limiting: Redis Token Bucket

**Decision:** Redis-based token bucket algorithm with Lua scripts

**Rationale:**
- Atomic operations prevent race conditions
- Per-user, per-endpoint granularity
- Smooth traffic distribution (better than fixed window)
- Scales horizontally with Redis cluster

**Trade-offs:**
- ✅ Pro: Accurate, atomic, distributed-safe
- ✅ Pro: Flexible rate limits per endpoint type
- ⚠️ Con: Requires Redis infrastructure
- ⚠️ Con: More complex than in-memory counters

### MCP Server: Client-Side Auth + Response Signing

**Decision:** No server-side sessions; OAuth 2.1 client + cryptographic response signing

**Rationale:**
- MCP spec explicitly forbids server-side sessions
- MCP servers run locally (client controls access)
- Response signing prevents tampering by malicious clients
- OAuth 2.1 provides standard authorization flow

**Trade-offs:**
- ✅ Pro: Follows MCP specification
- ✅ Pro: Client controls access (appropriate for local tools)
- ⚠️ Con: Must implement response verification in client
- ⚠️ Con: Key management complexity

---

## HTTP API Authentication

### Token Architecture

#### Access Token (Short-Lived)

```json
{
  "sub": "user_abc123",
  "aud": "foodlog-api",
  "iss": "foodlog.example.com",
  "exp": 1234567890,
  "iat": 1234567000,
  "jti": "unique-token-id-12345",
  "type": "access",
  "scopes": ["read", "write"]
}
```

**Properties:**
- **Lifetime:** 15 minutes
- **Algorithm:** RS256 (RSA + SHA-256)
- **Storage:** Client memory (not persisted)
- **Transmission:** `Authorization: Bearer <token>` header

#### Refresh Token (Long-Lived)

```json
{
  "sub": "user_abc123",
  "aud": "foodlog-api",
  "iss": "foodlog.example.com",
  "exp": 1234567890,
  "iat": 1234567000,
  "jti": "refresh-token-id-67890",
  "type": "refresh",
  "token_family": "family-uuid-abc"
}
```

**Properties:**
- **Lifetime:** 7 days
- **Algorithm:** RS256
- **Storage:** httpOnly cookie (XSS protection)
- **Rotation:** New token issued on every refresh

### Authentication Flows

#### 1. Login Flow

```
Client                    Auth Server                   Redis
  │                            │                           │
  │ POST /auth/login          │                           │
  │ {email, password}         │                           │
  ├──────────────────────────>│                           │
  │                            │                           │
  │                            │ Verify credentials        │
  │                            │ Generate access token     │
  │                            │ Generate refresh token    │
  │                            │                           │
  │                            │ Store token family        │
  │                            ├─────────────────────────>│
  │                            │                           │
  │ {access_token,            │                           │
  │  refresh_token}           │                           │
  │<──────────────────────────┤                           │
  │                            │                           │
  │ Store in httpOnly cookie  │                           │
  │                            │                           │
```

#### 2. Authenticated Request Flow

```
Client                    API Gateway                   User DB
  │                            │                           │
  │ GET /api/meals            │                           │
  │ Authorization: Bearer ... │                           │
  ├──────────────────────────>│                           │
  │                            │                           │
  │                            │ Validate JWT signature    │
  │                            │ Check expiry              │
  │                            │ Verify audience           │
  │                            │                           │
  │                            │ Check Redis blacklist     │
  │                            │ (not revoked?)            │
  │                            │                           │
  │                            │ Extract user_id from JWT  │
  │                            │                           │
  │                            │ Query user-specific DB    │
  │                            ├─────────────────────────>│
  │                            │                           │
  │ {meals: [...]}            │                           │
  │<──────────────────────────┤                           │
```

#### 3. Token Refresh Flow (Rotation)

```
Client                    Auth Server                   Redis
  │                            │                           │
  │ POST /auth/refresh        │                           │
  │ Cookie: refresh_token=... │                           │
  ├──────────────────────────>│                           │
  │                            │                           │
  │                            │ Validate refresh token    │
  │                            │                           │
  │                            │ Check if revoked          │
  │                            ├─────────────────────────>│
  │                            │<─────────────────────────┤
  │                            │                           │
  │                            │ Generate NEW tokens       │
  │                            │                           │
  │                            │ Blacklist OLD refresh     │
  │                            ├─────────────────────────>│
  │                            │                           │
  │                            │ Store NEW token family    │
  │                            ├─────────────────────────>│
  │                            │                           │
  │ {access_token,            │                           │
  │  refresh_token}           │                           │
  │<──────────────────────────┤                           │
```

**Key Security Feature:** Refresh token rotation prevents token replay attacks. If an old refresh token is used after rotation, it indicates theft, and the entire token family is revoked.

### Implementation Example

```python
# src/fcp/auth/jwt_manager.py
from datetime import datetime, timedelta
from typing import Optional
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

class JWTManager:
    """Manages JWT token generation and validation."""

    def __init__(
        self,
        private_key_pem: str,
        public_key_pem: str,
        issuer: str = "foodlog.example.com",
        audience: str = "foodlog-api"
    ):
        self.private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None,
            backend=default_backend()
        )
        self.public_key = serialization.load_pem_public_key(
            public_key_pem.encode(),
            backend=default_backend()
        )
        self.issuer = issuer
        self.audience = audience

    def create_access_token(
        self,
        user_id: str,
        scopes: list[str] = ["read", "write"]
    ) -> str:
        """Generate a short-lived access token (15 minutes)."""
        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "aud": self.audience,
            "iss": self.issuer,
            "exp": now + timedelta(minutes=15),
            "iat": now,
            "jti": f"access-{uuid.uuid4()}",
            "type": "access",
            "scopes": scopes
        }

        return jwt.encode(payload, self.private_key, algorithm="RS256")

    def create_refresh_token(
        self,
        user_id: str,
        token_family: Optional[str] = None
    ) -> str:
        """Generate a long-lived refresh token (7 days)."""
        now = datetime.utcnow()
        family = token_family or str(uuid.uuid4())

        payload = {
            "sub": user_id,
            "aud": self.audience,
            "iss": self.issuer,
            "exp": now + timedelta(days=7),
            "iat": now,
            "jti": f"refresh-{uuid.uuid4()}",
            "type": "refresh",
            "token_family": family
        }

        return jwt.encode(payload, self.private_key, algorithm="RS256")

    def validate_token(self, token: str) -> dict:
        """Validate JWT token and return claims."""
        try:
            claims = jwt.decode(
                token,
                self.public_key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True
                }
            )
            return claims
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {e}")
```

### Token Revocation (Redis Blacklist)

```python
# src/fcp/auth/token_blacklist.py
import redis
from datetime import timedelta

class TokenBlacklist:
    """Manages revoked tokens using Redis."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def revoke_token(self, jti: str, ttl_seconds: int):
        """Add token to blacklist with TTL matching token expiry."""
        self.redis.setex(
            f"blacklist:{jti}",
            ttl_seconds,
            "1"
        )

    def is_revoked(self, jti: str) -> bool:
        """Check if token is revoked."""
        return bool(self.redis.exists(f"blacklist:{jti}"))

    def revoke_token_family(self, family_id: str):
        """Revoke all tokens in a family (used when theft detected)."""
        self.redis.setex(
            f"family_revoked:{family_id}",
            timedelta(days=7).total_seconds(),
            "1"
        )

    def is_family_revoked(self, family_id: str) -> bool:
        """Check if entire token family is revoked."""
        return bool(self.redis.exists(f"family_revoked:{family_id}"))
```

### FastAPI Middleware

```python
# src/fcp/auth/middleware.py
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManager = Depends(get_jwt_manager),
    blacklist: TokenBlacklist = Depends(get_blacklist)
) -> AuthenticatedUser:
    """Validate JWT and return authenticated user."""

    token = credentials.credentials

    try:
        # Validate JWT signature and claims
        claims = jwt_manager.validate_token(token)

        # Check if token is revoked
        if blacklist.is_revoked(claims["jti"]):
            raise HTTPException(401, "Token has been revoked")

        # Check if token family is revoked
        if claims["type"] == "refresh":
            family = claims.get("token_family")
            if family and blacklist.is_family_revoked(family):
                raise HTTPException(401, "Token family revoked (possible theft)")

        # Return authenticated user
        return AuthenticatedUser(
            user_id=claims["sub"],
            scopes=claims.get("scopes", [])
        )

    except AuthenticationError as e:
        raise HTTPException(401, str(e))
```

---

## User Data Isolation

### Database-Per-Tenant Architecture

Each user gets their own SQLite database with complete data isolation:

```
data/
  users/
    user_abc123/
      foodlog.db          # SQLite database
      metadata.json       # User preferences
      attachments/        # User-uploaded files
    user_def456/
      foodlog.db
      metadata.json
      attachments/
    user_ghi789/
      foodlog.db
      metadata.json
      attachments/
```

### Benefits

1. **Security**: Complete data isolation - no risk of cross-user queries
2. **Performance**: Each DB is small and fast (user-specific indexes)
3. **Scalability**: Proven at massive scale (iCloud uses millions of DBs)
4. **Compliance**: GDPR right-to-deletion = delete user directory
5. **Backups**: Granular per-user backups and point-in-time recovery
6. **Sharding**: Easy to distribute users across storage tiers

### Implementation

```python
# src/fcp/database/user_db_manager.py
from pathlib import Path
import sqlite3
from typing import Optional

class UserDatabaseManager:
    """Manages per-user SQLite databases."""

    def __init__(self, base_path: str = "data/users"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def get_user_db_path(self, user_id: str) -> Path:
        """Get path to user's database."""
        user_dir = self.base_path / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir / "foodlog.db"

    def get_connection(self, user_id: str) -> sqlite3.Connection:
        """Get connection to user's database."""
        db_path = self.get_user_db_path(user_id)

        # Initialize schema if first time
        is_new = not db_path.exists()
        conn = sqlite3.connect(str(db_path))

        if is_new:
            self._init_schema(conn)

        return conn

    def _init_schema(self, conn: sqlite3.Connection):
        """Initialize database schema for new user."""
        conn.executescript("""
            CREATE TABLE meals (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                calories INTEGER,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE recipes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                ingredients TEXT,
                instructions TEXT
            );

            CREATE TABLE pantry (
                id TEXT PRIMARY KEY,
                item_name TEXT NOT NULL,
                quantity REAL,
                unit TEXT,
                expiry_date DATE
            );

            CREATE INDEX idx_meals_logged ON meals(logged_at DESC);
            CREATE INDEX idx_pantry_expiry ON pantry(expiry_date);
        """)
        conn.commit()

    def delete_user_data(self, user_id: str):
        """Delete all user data (GDPR compliance)."""
        user_dir = self.base_path / user_id
        if user_dir.exists():
            shutil.rmtree(user_dir)
```

### Cross-User Queries (Admin Analytics)

For admin operations that need to aggregate across users (e.g., total meals logged globally), use SQLite's ATTACH feature:

```python
def get_global_stats(self, admin_user_id: str) -> dict:
    """Get statistics across all users (admin only)."""
    conn = self.get_connection(admin_user_id)

    # Attach all user databases
    user_ids = self.list_users()
    for user_id in user_ids:
        db_path = self.get_user_db_path(user_id)
        conn.execute(
            f"ATTACH DATABASE '{db_path}' AS user_{user_id}"
        )

    # Query across all attached databases
    query = " UNION ALL ".join([
        f"SELECT '{user_id}' as user_id, COUNT(*) as meal_count "
        f"FROM user_{user_id}.meals"
        for user_id in user_ids
    ])

    results = conn.execute(query).fetchall()

    # Detach databases
    for user_id in user_ids:
        conn.execute(f"DETACH DATABASE user_{user_id}")

    return {"total_meals": sum(r[1] for r in results)}
```

**Performance Note:** ATTACH is fast for dozens of databases. For thousands of users, consider:
- Pre-computed aggregates in a separate analytics DB
- Background jobs that collect stats periodically
- Sampling (query random subset of users)

---

## Rate Limiting

### Algorithm: Token Bucket

The token bucket algorithm provides smooth rate limiting with burst allowance:

```
┌────────────────────────────────────────────────┐
│  Token Bucket (Capacity: 30 tokens)           │
│                                                │
│  Refill Rate: 0.5 tokens/second (30/min)      │
│                                                │
│  Current Tokens: 25                            │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░                     │
│                                                │
│  Request arrives → Consume 1 token            │
│  ├─ Tokens >= 1? ✓ Allow request             │
│  └─ Tokens < 1?  ✗ Reject (429)              │
└────────────────────────────────────────────────┘
```

**Advantages over Fixed Window:**
- Smooths traffic spikes (no "thundering herd" at window reset)
- Allows small bursts (user can consume multiple tokens quickly)
- More accurate rate limiting (no edge-case double-counting)

### Redis Implementation (Atomic)

```python
# src/fcp/ratelimit/token_bucket.py
import redis
import time
from typing import NamedTuple

class RateLimitResult(NamedTuple):
    allowed: bool
    remaining: int
    reset_at: float

# Lua script for atomic token bucket operations
TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local max_tokens = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])

-- Get current bucket state
local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1]) or max_tokens
local last_refill = tonumber(bucket[2]) or now

-- Calculate token refill
local elapsed = now - last_refill
local refilled = elapsed * refill_rate
tokens = math.min(max_tokens, tokens + refilled)

-- Try to consume tokens
if tokens >= cost then
    tokens = tokens - cost
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 3600)  -- 1 hour TTL

    -- Calculate time until next token
    local reset_at = now + ((cost - tokens % 1) / refill_rate)

    return {1, math.floor(tokens), reset_at}  -- allowed, remaining, reset
else
    -- Calculate time until enough tokens available
    local needed = cost - tokens
    local wait_time = needed / refill_rate
    local reset_at = now + wait_time

    return {0, math.floor(tokens), reset_at}  -- denied, remaining, reset
end
"""

class RateLimiter:
    """Token bucket rate limiter using Redis."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.script = self.redis.register_script(TOKEN_BUCKET_LUA)

    async def check_limit(
        self,
        user_id: str,
        endpoint: str,
        max_requests: int = 30,
        per_seconds: int = 60,
        cost: int = 1
    ) -> RateLimitResult:
        """Check if request is within rate limit."""

        key = f"ratelimit:{user_id}:{endpoint}"
        refill_rate = max_requests / per_seconds
        now = time.time()

        result = self.script(
            keys=[key],
            args=[max_requests, refill_rate, now, cost]
        )

        return RateLimitResult(
            allowed=bool(result[0]),
            remaining=result[1],
            reset_at=result[2]
        )
```

### Rate Limit Tiers

Different endpoint categories have different limits based on resource cost:

```python
# src/fcp/ratelimit/limits.py
from enum import Enum

class RateLimitTier(Enum):
    """Rate limit tiers for different endpoint types."""

    # Expensive: Gemini API calls, image analysis
    ANALYSIS = {"max": 10, "per": 60, "burst": 2}

    # Moderate: Database writes, recipe generation
    WRITE = {"max": 30, "per": 60, "burst": 5}

    # Light: Search queries, autocomplete
    SEARCH = {"max": 60, "per": 60, "burst": 10}

    # Minimal: Read-only queries (meals, recipes)
    READ = {"max": 100, "per": 60, "burst": 20}

# Usage
ENDPOINT_LIMITS = {
    "/api/analyze": RateLimitTier.ANALYSIS,
    "/api/meals": RateLimitTier.WRITE,
    "/api/search": RateLimitTier.SEARCH,
    "/api/recipes/{id}": RateLimitTier.READ,
}
```

### FastAPI Integration

```python
# src/fcp/ratelimit/middleware.py
from fastapi import Request, HTTPException, Depends
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

async def rate_limit_middleware(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    limiter: RateLimiter = Depends(get_rate_limiter)
):
    """Rate limiting middleware for FastAPI."""

    # Determine endpoint tier
    endpoint = request.url.path
    tier = ENDPOINT_LIMITS.get(endpoint, RateLimitTier.READ)

    # Check rate limit
    result = await limiter.check_limit(
        user_id=user.user_id,
        endpoint=endpoint,
        **tier.value
    )

    # Add rate limit headers
    request.state.rate_limit_remaining = result.remaining
    request.state.rate_limit_reset = result.reset_at

    if not result.allowed:
        raise HTTPException(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry after {result.reset_at - time.time():.0f}s",
            headers={
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(result.reset_at)),
                "Retry-After": str(int(result.reset_at - time.time()))
            }
        )

# Add response headers
@app.middleware("http")
async def add_rate_limit_headers(request: Request, call_next):
    response = await call_next(request)

    if hasattr(request.state, "rate_limit_remaining"):
        response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit_remaining)
        response.headers["X-RateLimit-Reset"] = str(int(request.state.rate_limit_reset))

    return response
```

---

## MCP Server Security

### Authentication Model

Per [MCP specification](https://modelcontextprotocol.io/specification/draft/basic/security_best_practices):

> **MCP servers MUST NOT use sessions for authentication**

Instead, MCP servers validate tokens on every request:

```
┌─────────────────────────────────────────────────────────┐
│  MCP Client (Claude Desktop, Gemini Extension)          │
│  1. User authorizes via OAuth 2.1 flow                  │
│  2. Client receives access token from auth server       │
│  3. Client stores token securely                        │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ MCP Request + Authorization: Bearer <token>
                 ▼
┌─────────────────────────────────────────────────────────┐
│  MCP Server (foodlog stdio)                             │
│  1. Validate JWT signature (RS256)                      │
│  2. Check token expiry                                  │
│  3. Verify audience claim (RFC 8707)                    │
│  4. Extract user_id from token                          │
│  5. Execute tool with user context                      │
│  6. Sign response cryptographically                     │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ Signed Response
                 ▼
┌─────────────────────────────────────────────────────────┐
│  MCP Client                                             │
│  1. Verify response signature                           │
│  2. Use response data                                   │
└─────────────────────────────────────────────────────────┘
```

### Token Validation

```python
# src/fcp/mcp/auth.py
import jwt
from cryptography.hazmat.primitives import serialization

class MCPAuthValidator:
    """Validates JWT tokens in MCP requests."""

    def __init__(self, public_key_pem: str):
        self.public_key = serialization.load_pem_public_key(
            public_key_pem.encode()
        )

    def validate_request(self, request: dict) -> AuthenticatedUser:
        """Validate MCP request and extract user context."""

        # Extract token from request metadata
        token = request.get("meta", {}).get("authorization")
        if not token or not token.startswith("Bearer "):
            raise MCPAuthError("Missing or invalid authorization")

        token = token[7:]  # Remove "Bearer " prefix

        try:
            # Validate JWT with strict checks
            claims = jwt.decode(
                token,
                self.public_key,
                algorithms=["RS256"],
                audience="foodlog-mcp",  # RFC 8707 Resource Indicators
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "require": ["sub", "aud", "exp", "iat"]
                }
            )

            return AuthenticatedUser(
                user_id=claims["sub"],
                scopes=claims.get("scopes", [])
            )

        except jwt.InvalidTokenError as e:
            raise MCPAuthError(f"Invalid token: {e}")
```

### Response Signing

Cryptographically sign MCP responses to prevent tampering:

```python
# src/fcp/mcp/signing.py
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
import json

class MCPResponseSigner:
    """Signs MCP responses to prevent tampering."""

    def __init__(self, private_key: rsa.RSAPrivateKey):
        self.private_key = private_key

    def sign_response(self, response_data: dict) -> dict:
        """Sign MCP tool response."""

        # Canonicalize response (sorted JSON)
        canonical = json.dumps(response_data, sort_keys=True, separators=(',', ':'))

        # Sign with RSA-PSS (more secure than PKCS#1 v1.5)
        signature = self.private_key.sign(
            canonical.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        return {
            "data": response_data,
            "signature": {
                "value": signature.hex(),
                "algorithm": "RSA-PSS-SHA256",
                "timestamp": int(time.time())
            }
        }

class MCPResponseVerifier:
    """Verifies signed MCP responses (client-side)."""

    def __init__(self, public_key: rsa.RSAPublicKey):
        self.public_key = public_key

    def verify_response(self, signed_response: dict) -> dict:
        """Verify response signature and extract data."""

        data = signed_response["data"]
        sig_info = signed_response["signature"]

        # Reconstruct canonical form
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))

        try:
            # Verify signature
            self.public_key.verify(
                bytes.fromhex(sig_info["value"]),
                canonical.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            return data

        except Exception as e:
            raise MCPSecurityError(f"Signature verification failed: {e}")
```

### Input Validation

**Critical:** All MCP tool inputs must be validated. Treat LLM-generated inputs as untrusted:

```python
# src/fcp/mcp/validation.py
from pydantic import BaseModel, Field, validator
import re

class MealInput(BaseModel):
    """Validated input for add_meal tool."""

    meal_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Name of the meal"
    )

    calories: int = Field(
        ...,
        ge=0,
        le=10000,
        description="Calories (0-10000)"
    )

    image_path: str | None = Field(
        None,
        regex=r"^[a-zA-Z0-9/_-]+\.(jpg|png|jpeg)$",
        description="Path to meal image (alphanumeric only)"
    )

    @validator('meal_name')
    def validate_meal_name(cls, v):
        """Prevent SQL injection and XSS."""
        # Allow letters, numbers, spaces, basic punctuation
        if not re.match(r"^[a-zA-Z0-9\s,.\-'&()]+$", v):
            raise ValueError("Meal name contains invalid characters")
        return v

    @validator('image_path')
    def prevent_path_traversal(cls, v):
        """Prevent directory traversal attacks."""
        if v is None:
            return v

        if '..' in v or v.startswith('/') or v.startswith('\\'):
            raise ValueError("Path traversal attempt detected")

        return v

# Usage in MCP tool
def add_meal_tool(raw_input: dict, user: AuthenticatedUser) -> dict:
    """MCP tool for adding a meal."""

    try:
        # Validate input with Pydantic
        validated = MealInput(**raw_input)

        # Safe to use validated input
        meal_id = create_meal(
            user_id=user.user_id,
            name=validated.meal_name,
            calories=validated.calories,
            image_path=validated.image_path
        )

        return {"success": True, "meal_id": meal_id}

    except ValidationError as e:
        return {"success": False, "error": str(e)}
```

### TLS for Network MCP (Optional)

If your MCP server runs over network (not stdio):

```python
# src/fcp/mcp/tls_server.py
import ssl
from pathlib import Path

def create_tls_context(
    cert_file: Path,
    key_file: Path,
    ca_file: Path | None = None
) -> ssl.SSLContext:
    """Create TLS context for MCP network server."""

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

    # Load server certificate and private key
    context.load_cert_chain(cert_file, key_file)

    # Require TLS 1.3+ (most secure)
    context.minimum_version = ssl.TLSVersion.TLSv1_3

    # Mutual authentication (optional)
    if ca_file:
        context.load_verify_locations(ca_file)
        context.verify_mode = ssl.CERT_REQUIRED

    return context
```

---

## Implementation Roadmap

### Phase 1: HTTP API Auth (Week 1)

**Goal:** Production-ready OAuth 2.1 + JWT authentication

**Tasks:**
- [ ] Set up Redis instance (local dev + production)
- [ ] Generate RSA key pair for JWT signing (RS256)
- [ ] Implement `JWTManager` class (token generation/validation)
- [ ] Create `/auth/login` endpoint (credentials → tokens)
- [ ] Create `/auth/refresh` endpoint (refresh token rotation)
- [ ] Create `/auth/logout` endpoint (token revocation)
- [ ] Implement token validation middleware
- [ ] Add `TokenBlacklist` with Redis
- [ ] Write unit tests (100% coverage)
- [ ] Integration tests with real Redis

**Deliverables:**
- `src/fcp/auth/jwt_manager.py`
- `src/fcp/auth/token_blacklist.py`
- `src/fcp/auth/middleware.py`
- `src/fcp/routes/auth.py`
- `tests/unit/auth/test_jwt.py`
- `tests/integration/test_auth_flow.py`

### Phase 2: User Isolation (Week 1-2)

**Goal:** Database-per-tenant architecture

**Tasks:**
- [ ] Design directory structure (`data/users/{user_id}/`)
- [ ] Implement `UserDatabaseManager` class
- [ ] Create schema initialization script
- [ ] Update all service methods to use user-specific DBs
- [ ] Implement ATTACH for cross-user queries
- [ ] Create migration system for schema updates
- [ ] Add database cleanup for user deletion (GDPR)
- [ ] Write unit tests for DB manager
- [ ] Performance testing (1000+ user databases)

**Deliverables:**
- `src/fcp/database/user_db_manager.py`
- `src/fcp/database/migrations/`
- Updated services (meals, recipes, pantry)
- `tests/unit/database/test_user_db_manager.py`
- Performance benchmark report

### Phase 3: Rate Limiting (Week 2)

**Goal:** Per-user, per-endpoint rate limiting with Redis

**Tasks:**
- [ ] Implement token bucket algorithm (Lua script)
- [ ] Create `RateLimiter` class
- [ ] Define rate limit tiers (analysis, write, search, read)
- [ ] Implement FastAPI middleware
- [ ] Add rate limit response headers
- [ ] Create rate limit override for admin users
- [ ] Write unit tests with mock Redis
- [ ] Integration tests with real Redis
- [ ] Load testing (simulate rate limit violations)

**Deliverables:**
- `src/fcp/ratelimit/token_bucket.py`
- `src/fcp/ratelimit/middleware.py`
- `src/fcp/ratelimit/limits.py`
- `tests/unit/ratelimit/test_token_bucket.py`
- Load test results

### Phase 4: MCP Security (Week 2-3)

**Goal:** Secure MCP server with OAuth 2.1 + response signing

**Tasks:**
- [ ] Implement OAuth 2.1 client in Gemini extension
- [ ] Add JWT validation in MCP server
- [ ] Implement `MCPResponseSigner` class
- [ ] Implement `MCPResponseVerifier` (client-side)
- [ ] Add input validation for all MCP tools (Pydantic)
- [ ] Create TLS context for network MCP (optional)
- [ ] Update MCP tool registry with validation
- [ ] Write unit tests for auth + signing
- [ ] Integration tests with real MCP client

**Deliverables:**
- `src/fcp/mcp/auth.py`
- `src/fcp/mcp/signing.py`
- `src/fcp/mcp/validation.py`
- Updated `gemini-extension/` with OAuth client
- `tests/unit/mcp/test_auth.py`
- `tests/integration/test_mcp_security.py`

### Phase 5: Production Hardening (Week 3-4)

**Goal:** Deploy-ready security and observability

**Tasks:**
- [ ] Store keys in Google Cloud Secret Manager
- [ ] Set up audit logging (auth events, permission denials)
- [ ] Implement token revocation API endpoint
- [ ] Add security headers (HSTS, CSP, X-Frame-Options)
- [ ] Set up monitoring (auth failures, rate limits)
- [ ] Create security incident response runbook
- [ ] Penetration testing (OWASP Top 10)
- [ ] Security audit with third-party tool
- [ ] Documentation for production deployment

**Deliverables:**
- Google Cloud Secret Manager integration
- Audit logging dashboard
- Security monitoring alerts
- Penetration test report
- Production deployment guide

---

## Tech Stack

### Dependencies

```toml
# pyproject.toml
[project.dependencies]
# Core Framework
fastapi = "^0.109.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}

# Authentication & Crypto
pyjwt = {extras = ["crypto"], version = "^2.8.0"}
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
cryptography = "^42.0.0"

# Rate Limiting & Caching
redis = {extras = ["hiredis"], version = "^5.0.0"}
hiredis = "^2.3.0"

# Validation
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"
email-validator = "^2.1.0"

# Database
aiosqlite = "^0.19.0"

# Utilities
python-dotenv = "^1.0.0"
```

### Infrastructure

**Development:**
- Redis: Local instance via Docker
- Database: SQLite (local files)
- Secrets: `.env` file (not committed)

**Production:**
- Redis: Google Cloud Memorystore for Redis
- Database: SQLite on Google Cloud Storage (or Turso for hosted SQLite)
- Secrets: Google Cloud Secret Manager
- TLS: Google-managed certificates

---

## References

### OAuth 2.0 / JWT

- [Google Cloud: Using OAuth 2.0 to Access Google APIs](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud: Using JWT OAuth tokens](https://docs.cloud.google.com/apigee/docs/api-platform/security/oauth/using-jwt-oauth)
- [FastAPI: OAuth2 with Password (and hashing), Bearer with JWT tokens](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [Medium: JWT in FastAPI, the Secure Way (Refresh Tokens Explained)](https://medium.com/@jagan_reddy/jwt-in-fastapi-the-secure-way-refresh-tokens-explained-f7d2d17b1d17)
- [TestDriven.io: Securing FastAPI with JWT Token-based Authentication](https://testdriven.io/blog/fastapi-jwt-auth/)

### Rate Limiting

- [Redis: Rate Limiting Glossary](https://redis.io/glossary/rate-limiting/)
- [Redis: Building a Rate Limiter with Redis](https://redis.io/learn/howtos/ratelimiting)
- [Redis: Fixed Window Rate Limiting using Redis](https://redis.io/learn/develop/java/spring/rate-limiting/fixed-window)
- [SystemsDesign.cloud: Design a Distributed Scalable API Rate Limiter](https://systemsdesign.cloud/SystemDesign/RateLimiter)

### User Isolation / Multi-Tenancy

- [Turso: Database Per Tenant](https://turso.tech/multi-tenancy)
- [Turso: Give each of your users their own SQLite database](https://turso.tech/blog/give-each-of-your-users-their-own-sqlite-database)
- [Julik Tarkhanov: A can of shardines: SQLite multitenancy with Rails](https://blog.julik.nl/2025/04/a-can-of-shardines)
- [ByteBase: Multi-Tenant Database Architecture Patterns Explained](https://www.bytebase.com/blog/multi-tenant-database-architecture-patterns-explained/)

### MCP Security

- [Model Context Protocol: Security Best Practices](https://modelcontextprotocol.io/specification/draft/basic/security_best_practices)
- [Stytch: MCP authentication and authorization implementation guide](https://stytch.com/blog/MCP-authentication-and-authorization-guide/)
- [Oso: Authorization for MCP: OAuth 2.1, PRMs, and Best Practices](https://www.osohq.com/learn/authorization-for-ai-agents-mcp-oauth-21)
- [Red Hat: Advanced authentication and authorization for MCP Gateway](https://developers.redhat.com/articles/2025/12/12/advanced-authentication-authorization-mcp-gateway)
- [Coalition for Secure AI: Securing the AI Agent Revolution: A Practical Guide to MCP Security](https://www.coalitionforsecureai.org/securing-the-ai-agent-revolution-a-practical-guide-to-mcp-security)
- [Corgea: Securing Model Context Protocol (MCP) Servers: Threats and Best Practices](https://corgea.com/Learn/securing-model-context-protocol-(mcp)-servers-threats-and-best-practices)

---

## Next Steps

1. **Review** this architecture with the team
2. **Prioritize** phases based on hackathon timeline (Feb 9 deadline)
3. **Spike** Redis setup and key generation
4. **Begin** Phase 1 implementation (HTTP API auth)

For questions or clarifications, see the original research in this document's sources.
