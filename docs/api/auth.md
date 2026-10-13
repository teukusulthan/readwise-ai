# API Auth Specifications

**Version:** 1.0.0

REST API for Vibe Codebase — cover authentication. Auth uses JWT-based tokens.

---

## Auth

### `POST /auth/login`

Login and obtain access token + refresh token. Tokens are stored in HttpOnly cookies.

**Request Body** — `AuthDTO`

| Field | Type | Required | Description |
|---|---|---|---|
| `email` | string | yes | User email |
| `password` | string | yes | User password |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 12, "responseCode": 200, "message": "Success" },
  "data": {
    "user": {
      "id": "string",
      "fullname": "string",
      "username": "string",
      "email": "string",
      "phone": "string",
      "image": "string",
      "permissionId": "string",
      "groupId": "string",
      "status": "string",
      "additional": {}
    },
    "auth": {
      "token": "string",
      "refresh_token": "string",
      "expire": 1234567890,
      "multiLogin": false
    }
  }
}
```

> `auth` is not returned in the response body — it is moved to HttpOnly cookies (`token`, `refresh_token`).

**Responses**

| Status | Description |
|---|---|
| `200` | Login successful |
| `400` | Login failed (unknown account or wrong password — the account's state is never revealed before the password matches), or locked after `BE_ACCOUNT_FAIL_LIMIT` failures; unknown identifiers lock and take as long as real ones |
| `403` | Correct password, but the account may not log in: expired, deleted, blocked, or any `status` other than `"active"` ("User doesn't have login access") |
| `429` | Auth rate limit (`BE_RATE_LIMIT_AUTH_PER_MINUTE`, shared by the auth endpoints, per client) |

Only accounts with `status: "active"` log in. Both registration paths create active accounts
(`/auth/verification` with `emailVerified: true`; the development path with `emailVerified: false`); `emailVerified`
itself is not checked at login. Accounts created through the optional admin `user` router need `status: "active"`.

---

### `POST /auth/register`

Register a new account. Closed with `BE_AUTH_REGISTRATION_OPEN=false` (`403` "Registration is closed.", as on
`/auth/verification` and `/auth/google/register`). By default (`BE_AUTH_EMAIL_VERIFICATION=true`) the email is checked (MX + Proofy) and an
OTP is mailed over SMTP; the account exists only after `POST /auth/verification`. With
`BE_AUTH_EMAIL_VERIFICATION=false` (development only) the active account is created immediately and no mail is sent.

**Request Body** — `RegisterDTO`

| Field | Type | Required | Description |
|---|---|---|---|
| `username` | string | yes | 3-40 letters, digits, `.`, `_`, `-`, at least one letter |
| `email` | string | yes | Valid email, stored lower-case (verified for MX + deliverability unless `BE_AUTH_EMAIL_VERIFICATION=false`) |
| `password` | string | yes | 8+ characters, at most 72 bytes, not a very common password nor the username/email |
| `phone` | string | yes | `+` and 6-20 digits; spaces, dashes and brackets are stripped |
| `fullname` | string | no | Full name, up to 120 printable characters |

Email, username and phone must not match any identifier (email, username or phone) of another account, compared
case-insensitively: all three sign in. With email verification on, the pending registration waits in Redis for
30 minutes with only a bcrypt hash of the password.

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": { "message": "Email register sent", "verificationRequired": true }
}
```

With `BE_AUTH_EMAIL_VERIFICATION=false`: `"data": { "message": "Account created", "verificationRequired": false, "id": "string" }`.

**Responses**

| Status | Description |
|---|---|
| `200` | Registration successful (OTP sent, or account created) |
| `400` | Email / username / phone already taken, or the mail could not be sent |
| `422` | Input breaks the rules above (the first message is in `detail[0].msg`) |
| `403` | Registration is closed (`BE_AUTH_REGISTRATION_OPEN=false`) |

---

### `POST /auth/verification`

Confirm a registration with the emailed code. Creates the account with `status: "active"` and `emailVerified: true`.
The code is valid only together with the email it was sent to, for 30 minutes, and is discarded after 5 wrong tries.

**Request Body** — `EmailOtpDTO`

| Field | Type | Required |
|---|---|---|
| `email` | string | yes |
| `otp` | string (6 digits) | yes |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": { "message": "Account verified" }
}
```

**Responses**

| Status | Description |
|---|---|
| `200` | Account created |
| `400` | "The code is invalid or has expired", or one of the identifiers was taken meanwhile |
| `403` | Registration is closed (`BE_AUTH_REGISTRATION_OPEN=false`) |
| `422` | Missing email, or the code is not 6 digits |
| `429` | Auth rate limit (`BE_RATE_LIMIT_AUTH_PER_MINUTE`) |

---

### `DELETE /auth/logout` :lock:

Logout: clear both cookies and revoke the refresh token (stored in Redis until it would have expired), so a copy of
the cookie cannot start a new session. The access token is not revoked; it expires after `BE_JWT_EXPIRED`.

**Auth:** `JWTRefresh`

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": "Logout Success"
}
```

**Responses**

| Status | Description |
|---|---|
| `200` | Logout successful |
| `400` | Logout failed |

---

### `GET /auth/validate` :lock:

Validate an active token.

**Auth:** `JWTRefresh`

**Query Parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `full_response` | boolean | `false` | Return full user data if `true` |

**Response `200`** (default, `full_response=false`)

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": { "status": "active" }
}
```

**Response `200`** (`full_response=true`)

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": {
    "user": { "id": "string", "fullname": "string", "username": "string", "email": "string" },
    "auth": { "token": "string", "refresh_token": "string", "expire": 1234567890 }
  }
}
```

**Responses**

| Status | Description |
|---|---|
| `200` | Token valid |
| `400` | Token invalid |

---

### `GET /auth/refresh` :lock:

Refresh access token using refresh token.

**Auth:** `JWTRefresh`

**Query Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `user_id` | string | no | Target user ID |
| `permission_id` | string | no | Permission context |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": "Refresh Success"
}
```

> New tokens are stored in HttpOnly cookies (`token`, `refresh_token`).

**Responses**

| Status | Description |
|---|---|
| `200` | Refresh successful, new tokens in cookies |
| `400` | Refresh failed |
| `401` | Session not found or token expired > 24 hours ago |

---

### Google OAuth (`/auth/google/*`)

The four `/auth/google/*` routes below are **mounted only when both `BE_GOOGLE_CLIENT_ID` and
`BE_GOOGLE_CLIENT_SECRET` are set**; otherwise they do not exist (`404`). The web app does not use them.

### `GET /auth/google`

Initiate Google OAuth redirect.

**Query Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `redirect_uri` | string | yes | Redirect URI after auth |

**Response:** Redirects to Google OAuth consent screen.

---

### `POST /auth/google/callback`

Google OAuth callback.

**Request Body** — `GoogleSSORequest`

| Field | Type | Required | Description |
|---|---|---|---|
| `code` | string | yes | Authorization code from Google |
| `redirect_uri` | string | yes | Same redirect URI as init |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 12, "responseCode": 200, "message": "Success" },
  "data": {
    "user": {
      "id": "string",
      "fullname": "string",
      "username": "string",
      "email": "string",
      "phone": "string",
      "image": "string",
      "status": "string"
    },
    "auth": {
      "token": "string",
      "refresh_token": "string",
      "expire": 1234567890,
      "multiLogin": false
    }
  }
}
```

**Responses**

| Status | Description |
|---|---|
| `200` | Google login successful |
| `400` | Google auth failed |

---

### `POST /auth/google/token_exchange`

Exchange a Google token.

**Request Body**

| Field | Type | Required |
|---|---|---|
| `token` | string | yes |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 12, "responseCode": 200, "message": "Success" },
  "data": {
    "user": { "id": "string", "fullname": "string", "username": "string", "email": "string" },
    "auth": { "token": "string", "refresh_token": "string", "expire": 1234567890 }
  }
}
```

**Responses**

| Status | Description |
|---|---|
| `200` | Token exchange successful |
| `400` | Exchange failed |

---

### `POST /auth/google/register`

Register a user via Google SSO (after `/auth/google/callback` answered `registered: false`).

**Request Body** — `UserDTO` (minimum: `email`, `phone`). Only the profile fields `fullname`, `username`, `email`,
`phone`, `password`, `image` are used; the account is always created with `status: "active"`,
`emailVerified: false` and no permission/group/expiry, whatever the body says.

> This endpoint does not itself prove that the caller owns the Google account for `email` — it is the boilerplate
> flow, available only while Google OAuth is configured and registration is open. Close it with
> `BE_AUTH_REGISTRATION_OPEN=false` (or leave Google unconfigured) on a public deployment that must not accept
> unverified sign-ups.

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": {
    "id": "string",
    "username": "string",
    "email": "string",
    "phone": "string",
    "fullname": "string",
    "status": "string"
  }
}
```

**Responses**

| Status | Description |
|---|---|
| `200` | Google registration successful, user object returned |
| `400` | Registration failed |
| `403` | Registration is closed (`BE_AUTH_REGISTRATION_OPEN=false`) |
| `404` | Google OAuth is not configured (route not mounted) |

---

### `POST /auth/forgot-password/request`

Request a password reset code by email. The answer is the same whether or not an account exists (and when the request
is throttled: one mail a minute, three per `BE_ACCOUNT_LOCK_TIME`); only active accounts with a verified email get a
code (valid 30 minutes, 5 tries).

**Request Body** — `RequestChangeDTO`

| Field | Type | Required |
|---|---|---|
| `email` | string | yes |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": { "message": "If an account with this email exists, a reset code has been sent to it." }
}
```

**Responses**

| Status | Description |
|---|---|
| `200` | Always (see above) |
| `422` | Invalid email, or its domain has no MX record |
| `429` | Auth rate limit (`BE_RATE_LIMIT_AUTH_PER_MINUTE`) |

---

### `POST /auth/forgot-password/verify`

Check a reset code without using it up (each check counts as one of the 5 tries).

**Request Body** — `EmailOtpDTO`

| Field | Type | Required |
|---|---|---|
| `email` | string | yes |
| `otp` | string (6 digits) | yes |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": { "message": "OTP is Valid" }
}
```

**Responses**

| Status | Description |
|---|---|
| `200` | Code valid |
| `400` | "The code is invalid or has expired" |

---

### `POST /auth/forgot-password/change`

Set a new password with the reset code. Every session started before the change ends (refresh tokens issued earlier
are refused; access tokens run out after `BE_JWT_EXPIRED`).

**Request Body** — `ChangePasswordOTPDTO`

| Field | Type | Required |
|---|---|---|
| `email` | string | yes |
| `otp` | string (6 digits) | yes |
| `newPassword` | string (8+ characters, at most 72 bytes, not a common password) | yes |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": { "message": "Password changed" }
}
```

**Responses**

| Status | Description |
|---|---|
| `200` | Password changed |
| `400` | "The code is invalid or has expired" |
| `422` | Password does not meet the rules |

---

### `POST /auth/verify-email/request`

Request email verification (sends a link to the email).

**Request Body** — `RequestChangeDTO`

| Field | Type | Required |
|---|---|---|
| `email` | string | yes |

**Query Parameters**

| Parameter | Type | Required |
|---|---|---|
| `setting_id` | string | no |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": { "message": "Email request verify email sent" }
}
```

**Responses**

| Status | Description |
|---|---|
| `200` | Verification email sent |
| `400` | Failed to send |

---

### `GET /auth/verify-email`

Verify email via token.

**Query Parameters**

| Parameter | Type | Required |
|---|---|---|
| `token` | string | yes |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": {
    "id": "string",
    "username": "string",
    "email": "string",
    "phone": "string",
    "emailVerified": true,
    "status": "string"
  }
}
```

**Responses**

| Status | Description |
|---|---|
| `200` | Email verified successfully, user object returned |
| `400` | Invalid token |

---

### `POST /auth/2fa/generate`

Generate 2FA QR code or send OTP to email.

**Request Body** — `GenerateTwoFactorDTO`

| Field | Type | Required | Description |
|---|---|---|---|
| `email` | string | yes | User email |
| `password` | string | yes | User password |
| `type` | string | yes | `email` or `google_authenticator` |

**Response `200`** (`type: "email"`)

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": {
    "session_token": "string",
    "message": "string"
  }
}
```

**Response `200`** (`type: "google_authenticator"`)

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": {
    "session_token": "string",
    "qr_image_base64": "string",
    "secret_manual": "string",
    "message": "string"
  }
}
```

**Responses**

| Status | Description |
|---|---|
| `200` | QR code / OTP sent |
| `400` | Failed to generate |

---

### `POST /auth/2fa/verify`

Verify 2FA OTP.

**Request Body** — `TwoFactorVerifyDTO`

| Field | Type | Required |
|---|---|---|
| `session_token` | string | yes |
| `otp` | string | yes |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 12, "responseCode": 200, "message": "Success" },
  "data": {
    "status": "true",
    "message": "Login Granted",
    "user": {
      "id": "string",
      "fullname": "string",
      "username": "string",
      "email": "string",
      "phone": "string",
      "status": "string"
    },
    "auth": {
      "token": "string",
      "refresh_token": "string",
      "expire": 1234567890,
      "multiLogin": false
    }
  }
}
```

**Responses**

| Status | Description |
|---|---|
| `200` | 2FA verified, full login response returned |
| `400` | Invalid OTP |

---

### `POST /auth/2fa/resend`

Resend 2FA OTP.

**Request Body** — `TwoFactorResendDTO`

| Field | Type | Required |
|---|---|---|
| `session_token` | string | yes |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": { "message": "Verification code has been resent to your email." }
}
```

**Responses**

| Status | Description |
|---|---|
| `200` | OTP resent |
| `400` | Failed to resend |

---

> :lock: = Endpoint requires Bearer Token (JWT)