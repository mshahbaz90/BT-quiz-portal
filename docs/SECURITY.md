# BreakThru Assessments — Security Policy & Controls

## 1. Authentication & Session Security
- **PBKDF2 Password Hashing**: Utilizes industry-standard SHA256/PBKDF2 password hashing with high iteration counts.
- **Brute-Force Throttling**: 5 failed consecutive attempts result in a temporary 15-minute account lock.
- **Session Protection**: `HttpOnly`, `SameSite=Lax` (and `Secure=True` in production HTTPS).
- **Mandatory Password Rotation**: First-time login requires immediate password change when provisioned with a temporary password.

## 2. Assessment Integrity & Anti-Cheating Deterrents
- **Server-Authoritative Clock**: Time limits are computed against server timestamps. Tampering with client local time has zero effect.
- **Answer Key Confidentiality**: Answer keys are never transmitted to the browser during the assessment. Only question texts and choices are serialized.
- **Attempt Isolation**: Users cannot query or inspect other employees' attempts.
- **Idempotency**: Submissions are guarded by database transactions and unique constraints.

## 3. Data Protection & Input Sanitation
- **CSRF Tokens**: All mutating POST/PUT/DELETE requests enforce CSRF verification.
- **SQL Injection Prevention**: 100% parameterized queries via Django ORM.
- **XSS Escaping**: Auto-escaped templates for all user-supplied inputs.
- **Role Enforcement at Server**: Every view and API endpoint asserts explicit role checks (`@login_required`, `@role_required`).

## 4. Production Checklist
- [ ] Set `DEBUG=False` in `.env`.
- [ ] Generate a cryptographically random `SECRET_KEY`.
- [ ] Configure `ALLOWED_HOSTS` with `assessments.breakthru.pk`.
- [ ] Enable `SECURE_SSL_REDIRECT = True`, `SESSION_COOKIE_SECURE = True`, and `CSRF_COOKIE_SECURE = True`.
- [ ] Set up daily automated PostgreSQL backups.
