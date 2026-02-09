# Authentication Quick Start Guide

**How OAuth 2.1 + JWT Actually Works in Practice**

This guide explains the authentication system in plain terms with real examples.

---

## Table of Contents

- [The Big Picture](#the-big-picture)
- [What You Need (Infrastructure)](#what-you-need-infrastructure)
- [How It Works: User Perspective](#how-it-works-user-perspective)
- [How It Works: Behind the Scenes](#how-it-works-behind-the-scenes)
- [Code Components Needed](#code-components-needed)
- [Minimal Setup (30 Minutes)](#minimal-setup-30-minutes)
- [Testing the Flow](#testing-the-flow)

---

## The Big Picture

**Current FoodLog (Simple Token):**
```
User → Sets FOODLOG_TOKEN=abc123 in .env
User → Sends request with "Authorization: Bearer abc123"
Server → Checks if abc123 == FOODLOG_TOKEN
Server → If match: authenticated, else: demo mode
```

**With OAuth 2.1 + JWT (Production):**
```
User → Sends email + password to /auth/login
Server → Validates credentials
Server → Returns 2 tokens:
         - Access token (JWT, expires in 15 min)
         - Refresh token (JWT, expires in 7 days)
User → Sends requests with access token
Server → Validates token cryptographically (no DB lookup needed!)
Server → Extracts user_id from token
Server → Uses user_id to load user's database

When access token expires (15 min):
User → Sends refresh token to /auth/refresh
Server → Issues new access + refresh tokens
User → Continues using new tokens
```

**Key Difference:**
- **Simple token**: String comparison (`token == FOODLOG_TOKEN`)
- **JWT**: Cryptographic validation (signed with RSA keys, can't be forged)

---

## What You Need (Infrastructure)

### 1. Redis (For Token Blacklist + Rate Limiting)

**What it does:**
- Stores revoked tokens (when user logs out)
- Tracks rate limits per user
- Fast in-memory storage (sub-millisecond lookups)

**How to set up (Local Dev):**

```bash
# Option 1: Docker (easiest)
docker run -d --name redis -p 6379:6379 redis:latest

# Option 2: Homebrew (macOS)
brew install redis
brew services start redis

# Option 3: apt (Linux)
sudo apt install redis-server
sudo systemctl start redis

# Test it works
redis-cli ping
# Should respond: PONG
```

**How to set up (Production):**

```bash
# Google Cloud Memorystore for Redis
gcloud redis instances create foodlog-redis \
    --size=1 \
    --region=us-central1 \
    --redis-version=7.0
```

**Cost:**
- Local: Free
- Production: ~$45/month (Google Cloud Memorystore 1GB)

### 2. RSA Key Pair (For JWT Signing)

**What it does:**
- Private key: Signs JWTs (only server has this)
- Public key: Verifies JWTs (can be shared publicly)

**How to generate:**

```bash
# Generate private key (keep this SECRET!)
openssl genrsa -out private_key.pem 2048

# Generate public key from private key
openssl rsa -in private_key.pem -pubout -out public_key.pem

# Move keys to secure location
mkdir -p ~/.secrets/foodlog
mv private_key.pem ~/.secrets/foodlog/
mv public_key.pem ~/.secrets/foodlog/

# Secure permissions (only you can read private key)
chmod 600 ~/.secrets/foodlog/private_key.pem
chmod 644 ~/.secrets/foodlog/public_key.pem
```

**In production:**
Store keys in Google Cloud Secret Manager (not in files):

```bash
# Upload private key to Secret Manager
gcloud secrets create foodlog-jwt-private-key \
    --data-file=~/.secrets/foodlog/private_key.pem

# Upload public key
gcloud secrets create foodlog-jwt-public-key \
    --data-file=~/.secrets/foodlog/public_key.pem
```

### 3. User Database (SQLite - Already Have!)

**What it does:**
- Stores user credentials (email, hashed password)
- One user database per user for data isolation

**Schema:**

```sql
-- Central auth database: data/auth.db
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,          -- uuid
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,       -- bcrypt hash
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Per-user database: data/users/{user_id}/foodlog.db
-- (Already designed in main architecture doc)
```

---

## How It Works: User Perspective

### Flow 1: First-Time Registration

```
1. User opens app → clicks "Sign Up"

2. App shows form:
   Email: [user@example.com]
   Password: [********]
   [Sign Up Button]

3. User submits → App sends:
   POST /auth/register
   {
     "email": "user@example.com",
     "password": "SecurePass123!"
   }

4. Server responds:
   {
     "success": true,
     "user_id": "user_abc123",
     "access_token": "eyJhbGc...",
     "refresh_token": "eyJhbGc..."
   }

5. App stores tokens:
   - Access token → Memory (short-lived)
   - Refresh token → Secure storage (httpOnly cookie or keychain)

6. User is now logged in! 🎉
```

### Flow 2: Daily Login

```
1. User opens app → clicks "Login"

2. App shows form:
   Email: [user@example.com]
   Password: [********]
   [Login Button]

3. User submits → App sends:
   POST /auth/login
   {
     "email": "user@example.com",
     "password": "SecurePass123!"
   }

4. Server validates:
   ✓ User exists?
   ✓ Password correct?

5. Server responds:
   {
     "success": true,
     "access_token": "eyJhbGc...",
     "refresh_token": "eyJhbGc..."
   }

6. User is logged in!
```

### Flow 3: Making Requests (Every API Call)

```
1. User wants to log a meal:

   App UI:
   Meal Name: [Chicken Salad]
   Calories: [450]
   [Log Meal Button]

2. App sends:
   POST /api/meals
   Headers:
     Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
   Body:
     {
       "meal_name": "Chicken Salad",
       "calories": 450
     }

3. Server:
   ✓ Validates token (signature, expiry)
   ✓ Extracts user_id from token
   ✓ Opens user's database (data/users/user_abc123/foodlog.db)
   ✓ Inserts meal record

4. Server responds:
   {
     "success": true,
     "meal_id": "meal_xyz789"
   }

5. App shows: "Meal logged! ✓"
```

### Flow 4: Token Refresh (Every 15 Minutes, Automatic)

```
1. User continues using app...

2. After 14 minutes, access token is about to expire

3. App automatically sends (user doesn't notice):
   POST /auth/refresh
   Headers:
     Cookie: refresh_token=eyJhbGc...

4. Server:
   ✓ Validates refresh token
   ✓ Issues NEW access + refresh tokens
   ✓ Blacklists OLD refresh token (prevents reuse)

5. Server responds:
   {
     "access_token": "eyJhbGc...",  (NEW)
     "refresh_token": "eyJhbGc..."  (NEW)
   }

6. App replaces old tokens with new ones

7. User continues working (seamless!)
```

### Flow 5: Logout

```
1. User clicks "Logout"

2. App sends:
   POST /auth/logout
   Headers:
     Authorization: Bearer eyJhbGc...
     Cookie: refresh_token=eyJhbGc...

3. Server:
   ✓ Extracts token IDs (jti claims)
   ✓ Adds both tokens to Redis blacklist
   ✓ Sets TTL = token expiry time

4. Server responds:
   {
     "success": true
   }

5. App deletes stored tokens

6. User is logged out
```

---

## How It Works: Behind the Scenes

### What's in a JWT Token?

A JWT has 3 parts separated by dots:

```
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyX2FiYzEyMyIsImF1ZCI6ImZvb2Rsb2ctYXBpIiwiaXNzIjoiZm9vZGxvZy5leGFtcGxlLmNvbSIsImV4cCI6MTcwNzM1NTIwMCwiaWF0IjoxNzA3MzU0MzAwLCJqdGkiOiJhY2Nlc3MtdXVpZC0xMjM0NSIsInR5cGUiOiJhY2Nlc3MiLCJzY29wZXMiOlsicmVhZCIsIndyaXRlIl19.signature-here
```

Decoded:

**Part 1: Header**
```json
{
  "alg": "RS256",      // RSA + SHA-256 signing
  "typ": "JWT"         // It's a JWT
}
```

**Part 2: Payload (Claims)**
```json
{
  "sub": "user_abc123",           // Subject (user ID)
  "aud": "foodlog-api",           // Audience (this API)
  "iss": "foodlog.example.com",   // Issuer (who created it)
  "exp": 1707355200,              // Expiration (Unix timestamp)
  "iat": 1707354300,              // Issued at (Unix timestamp)
  "jti": "access-uuid-12345",     // JWT ID (unique identifier)
  "type": "access",               // Token type
  "scopes": ["read", "write"]     // Permissions
}
```

**Part 3: Signature**
```
RSASSA-PKCS1-v1_5-SHA256(
  base64(header) + "." + base64(payload),
  private_key
)
```

### How Server Validates Token (Fast!)

```python
def validate_token(token: str):
    # Step 1: Split token into parts
    header, payload, signature = token.split('.')

    # Step 2: Verify signature using PUBLIC KEY
    # (This proves token was signed with our private key)
    is_valid = rsa_verify(
        data=header + "." + payload,
        signature=signature,
        public_key=PUBLIC_KEY
    )

    if not is_valid:
        raise AuthError("Invalid signature!")

    # Step 3: Decode payload
    claims = json.loads(base64_decode(payload))

    # Step 4: Check expiration
    if claims["exp"] < time.time():
        raise AuthError("Token expired!")

    # Step 5: Check audience
    if claims["aud"] != "foodlog-api":
        raise AuthError("Wrong audience!")

    # Step 6: Check if revoked (Redis lookup)
    if redis.exists(f"blacklist:{claims['jti']}"):
        raise AuthError("Token revoked!")

    # ✓ Token is valid!
    return claims["sub"]  # Return user_id
```

**Why This Is Fast:**
- No database lookup needed (signature proves authenticity)
- Only Redis check (in-memory, <1ms)
- No password hashing (already done at login)

**Benchmark:** ~2-5ms per request

---

## Code Components Needed

### 1. Auth Service (`src/fcp/auth/service.py`)

**Responsibilities:**
- User registration (create account)
- User login (verify credentials)
- Token generation (access + refresh)
- Token validation
- Token refresh (rotation)
- Token revocation (logout)

**Key Methods:**
```python
class AuthService:
    async def register(email: str, password: str) -> AuthResponse
    async def login(email: str, password: str) -> AuthResponse
    async def validate_token(token: str) -> AuthenticatedUser
    async def refresh_tokens(refresh_token: str) -> AuthResponse
    async def revoke_token(token: str) -> None
```

### 2. JWT Manager (`src/fcp/auth/jwt_manager.py`)

**Responsibilities:**
- Generate access tokens
- Generate refresh tokens
- Validate JWT signatures
- Extract claims from tokens

**Key Methods:**
```python
class JWTManager:
    def create_access_token(user_id: str) -> str
    def create_refresh_token(user_id: str) -> str
    def validate_token(token: str) -> dict
```

### 3. Token Blacklist (`src/fcp/auth/blacklist.py`)

**Responsibilities:**
- Add tokens to blacklist (logout)
- Check if token is revoked
- Revoke entire token families (security)

**Key Methods:**
```python
class TokenBlacklist:
    async def revoke(jti: str, ttl: int) -> None
    async def is_revoked(jti: str) -> bool
    async def revoke_family(family_id: str) -> None
```

### 4. Password Hasher (`src/fcp/auth/password.py`)

**Responsibilities:**
- Hash passwords securely (bcrypt)
- Verify passwords

**Key Methods:**
```python
class PasswordHasher:
    def hash(password: str) -> str
    def verify(password: str, hash: str) -> bool
```

### 5. Auth Routes (`src/fcp/routes/auth.py`)

**Endpoints:**
```python
POST /auth/register   # Create account
POST /auth/login      # Get tokens
POST /auth/refresh    # Refresh tokens
POST /auth/logout     # Revoke tokens
GET  /auth/me         # Get current user info
```

### 6. Auth Middleware (`src/fcp/auth/middleware.py`)

**Responsibilities:**
- Extract token from request header
- Validate token
- Inject user into request context

**Usage:**
```python
@router.get("/api/meals")
async def get_meals(
    user: AuthenticatedUser = Depends(get_current_user)
):
    # user.user_id is available here!
    meals = get_user_meals(user.user_id)
    return meals
```

---

## Minimal Setup (30 Minutes)

Let's implement the absolute minimum to get OAuth + JWT working:

### Step 1: Install Dependencies (5 min)

```bash
# Add to pyproject.toml
uv add pyjwt[crypto]
uv add passlib[bcrypt]
uv add redis
uv add cryptography

# Install
uv sync
```

### Step 2: Start Redis (2 min)

```bash
docker run -d --name redis -p 6379:6379 redis:latest
```

### Step 3: Generate Keys (2 min)

```bash
mkdir -p ~/.secrets/foodlog
openssl genrsa -out ~/.secrets/foodlog/private_key.pem 2048
openssl rsa -in ~/.secrets/foodlog/private_key.pem -pubout -out ~/.secrets/foodlog/public_key.pem
```

### Step 4: Create Auth Database (3 min)

```bash
# Create data/auth.db
sqlite3 data/auth.db <<EOF
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
EOF
```

### Step 5: Update .env (2 min)

```bash
# .env
REDIS_URL=redis://localhost:6379
JWT_PRIVATE_KEY_PATH=/Users/jwegis/.secrets/foodlog/private_key.pem
JWT_PUBLIC_KEY_PATH=/Users/jwegis/.secrets/foodlog/public_key.pem
JWT_ALGORITHM=RS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Step 6: Implement Core Components (15 min)

I can generate the minimal working code for:
- `src/fcp/auth/jwt_manager.py` (100 lines)
- `src/fcp/auth/service.py` (150 lines)
- `src/fcp/routes/auth.py` (100 lines)
- `src/fcp/auth/middleware.py` (50 lines)

**Total:** ~400 lines of code

Want me to generate this now?

---

## Testing the Flow

### 1. Register a User

```bash
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!"
  }'

# Response:
{
  "success": true,
  "user_id": "user_abc123",
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc..."
}
```

### 2. Login

```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!"
  }'

# Response:
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc..."
}
```

### 3. Make Authenticated Request

```bash
# Save token
TOKEN="eyJhbGc..."

# Log a meal
curl -X POST http://localhost:8080/api/meals \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meal_name": "Chicken Salad",
    "calories": 450
  }'

# Response:
{
  "success": true,
  "meal_id": "meal_xyz789"
}
```

### 4. Refresh Token

```bash
# After 14 minutes...
REFRESH_TOKEN="eyJhbGc..."

curl -X POST http://localhost:8080/auth/refresh \
  -H "Cookie: refresh_token=$REFRESH_TOKEN"

# Response:
{
  "access_token": "eyJhbGc...",  # NEW
  "refresh_token": "eyJhbGc..."  # NEW
}
```

### 5. Logout

```bash
curl -X POST http://localhost:8080/auth/logout \
  -H "Authorization: Bearer $TOKEN" \
  -H "Cookie: refresh_token=$REFRESH_TOKEN"

# Response:
{
  "success": true
}

# Try using old token → Should fail
curl -X GET http://localhost:8080/api/meals \
  -H "Authorization: Bearer $TOKEN"

# Response:
{
  "error": "Token has been revoked"
}
```

---

## What Happens in Production?

### Security Improvements:

1. **HTTPS Only** - All requests over TLS
2. **Secure Cookies** - `httpOnly`, `Secure`, `SameSite=Strict`
3. **Key Rotation** - Rotate RSA keys every 90 days
4. **Rate Limiting** - Prevent brute force attacks
5. **Password Requirements** - Min 12 chars, complexity rules
6. **2FA** - Optional TOTP (Google Authenticator)
7. **Audit Logging** - Log all auth events
8. **Secret Manager** - Keys stored in Google Cloud, not files

### Infrastructure:

```
Production Setup:
- API: Cloud Run (auto-scaling)
- Redis: Memorystore for Redis (managed, HA)
- Secrets: Secret Manager (encrypted, audited)
- Database: Cloud Storage (or Turso for hosted SQLite)
- TLS: Google-managed certificates
```

---

## Next Steps

1. **Decide:** Do you want me to implement the minimal setup now?
2. **Timeline:** This is ~2 hours of work for basic auth
3. **Hackathon:** Is this worth the time vs focusing on Gemini features?

**My Recommendation for Feb 9 Deadline:**
- If you have 2+ days left: Implement basic auth (impressive for judges)
- If < 2 days: Keep simple token, focus on Gemini demo

Want me to generate the code?
