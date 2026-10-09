# Authentication Architecture (`docs/AUTHENTICATION.md`)

## 1. Overview
The ONYX Local Multimodal RAG platform enforces local-only authentication backed by SQLite (`users` and `user_sessions` tables), **Argon2id** password hashing, and **revocable HS256 JWT sessions**.

## 2. Password Security
- Passwords are never stored or logged in plaintext.
- All user passwords are hashed using `argon2-cffi` (`Argon2id`) via `hash_password()` and verified via `verify_password()` in [`backend/auth/auth_handler.py`](file:///c:/Users/devik/Desktop/rag/backend/auth/auth_handler.py).

## 3. Session Management & Immediate Revocation
1. **Login (`POST /api/auth/login`)**:
   - Enforces sliding-window login rate limiting (`check_login_rate_limit`) per IP and username (maximum 10 failed attempts per 5 minutes).
   - Verifies that `user.status == "ACTIVE"`. Accounts with `SUSPENDED` or `DISABLED` status are immediately rejected with `403 Forbidden`.
   - Generates a unique session identifier (`jti`) and embeds `user.token_version` (`tv`) in the JWT payload.
   - Persists an active `UserSession` record in SQLite and records `ADMIN_LOGIN` or `EMPLOYEE_LOGIN` in `audit_logs`.
2. **Logout (`POST /api/auth/logout`)**:
   - Marks the active `UserSession` (`is_active = False`, `revoked_at = utc_now()`) so the token cannot be reused.
3. **Immediate Session Invalidation**:
   - Whenever an administrator disables/suspends a user, resets their password, or changes their role (`admin` ↔ `employee`), `invalidate_user_sessions(db, user)` increments `user.token_version` and revokes all active `UserSession` rows.
   - Every subsequent API call with an old JWT is immediately rejected in `get_current_user()`.
