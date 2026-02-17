# Single Sign-On (OIDC)

WebMACS supports **OpenID Connect (OIDC)** for centralized authentication via external Identity Providers (IdP) such as Keycloak, Authentik, Azure AD, Google Workspace, or any OIDC-compliant service.

---

## Overview

The SSO integration uses the **Authorization Code flow with PKCE** (Proof Key for Code Exchange — S256). Users click "Sign in with SSO" on the login page and are redirected to the Identity Provider. After authentication the IdP redirects back to WebMACS, which creates or links a local user account automatically.

```
┌──────────┐       ┌──────────────┐       ┌──────────────┐
│  Browser  │──1──▶│  WebMACS API │──2──▶│  Identity    │
│           │      │  /authorize  │      │  Provider    │
│           │◀─5───│  /exchange   │◀─4───│  /callback   │
│           │──3──▶│              │      │              │
└──────────┘       └──────────────┘       └──────────────┘
```

1. User clicks **Sign in with SSO** → frontend redirects to `/api/v1/auth/sso/authorize`
2. Backend generates PKCE challenge + CSRF state token and redirects to the IdP
3. User authenticates at the IdP
4. IdP redirects back to `/api/v1/auth/sso/callback` with an authorization code
5. Backend exchanges the code for tokens, creates/links a local user, issues a one-time code, and redirects the browser to the frontend
6. Frontend exchanges the one-time code for a JWT via `POST /api/v1/auth/sso/exchange`

---

## Configuration

Enable SSO by setting the following environment variables:

| Variable | Required | Default | Description |
|---|---|---|---|
| `OIDC_ENABLED` | No | `false` | Enable OIDC SSO |
| `OIDC_PROVIDER_NAME` | No | `SSO` | Display name on the login button |
| `OIDC_ISSUER_URL` | **Yes** | *(empty)* | Issuer URL of your IdP (e.g. `https://auth.example.com/realms/webmacs`) |
| `OIDC_CLIENT_ID` | **Yes** | *(empty)* | OAuth2 Client ID |
| `OIDC_CLIENT_SECRET` | **Yes** | *(empty)* | OAuth2 Client Secret |
| `OIDC_SCOPES` | No | `openid email profile` | Space-separated scopes |
| `OIDC_REDIRECT_URI` | **Yes** | *(empty)* | Callback URL — must be `https://<your-domain>/api/v1/auth/sso/callback` |
| `OIDC_DEFAULT_ROLE` | No | `viewer` | Role assigned to auto-created SSO users (`admin`, `operator`, `viewer`) |
| `OIDC_AUTO_CREATE_USERS` | No | `true` | Automatically create a local user on first SSO login |
| `OIDC_FRONTEND_URL` | No | *(empty)* | Frontend URL for post-login redirect (e.g. `https://webmacs.example.com`) |

!!! warning "OIDC_REDIRECT_URI"
    This must **exactly** match the redirect URI registered in your Identity Provider. Mismatching URIs will cause the authentication flow to fail.

!!! tip "OIDC_FRONTEND_URL"
    If not set, WebMACS derives the frontend URL from `CORS_ORIGINS`. For production deployments, always set this explicitly.

---

## Setting Up Your Identity Provider

### Keycloak

1. Create a new **Client** in your Keycloak realm
2. Set **Client Protocol** to `openid-connect`
3. Set **Access Type** to `confidential`
4. Set **Valid Redirect URIs** to `https://webmacs.example.com/api/v1/auth/sso/callback`
5. Copy the **Client ID** and **Client Secret** from the Credentials tab
6. The Issuer URL is `https://keycloak.example.com/realms/<your-realm>`

### Authentik

1. Create a new **OAuth2/OpenID Provider**
2. Set **Redirect URIs** to `https://webmacs.example.com/api/v1/auth/sso/callback`
3. Set **Scopes**: `openid`, `email`, `profile`
4. Create an **Application** linked to this provider
5. Copy the **Client ID** and **Client Secret**
6. The Issuer URL is `https://authentik.example.com/application/o/<app-slug>/`

### Azure AD (Entra ID)

1. Register a new **App Registration** in Azure Portal
2. Under **Authentication**, add a redirect URI: `https://webmacs.example.com/api/v1/auth/sso/callback`
3. Under **Certificates & secrets**, create a client secret
4. The Issuer URL is `https://login.microsoftonline.com/<tenant-id>/v2.0`

### Google Workspace

1. Create **OAuth 2.0 credentials** in Google Cloud Console
2. Add `https://webmacs.example.com/api/v1/auth/sso/callback` as an authorized redirect URI
3. The Issuer URL is `https://accounts.google.com`

---

## Example `.env`

```dotenv
# Enable SSO
OIDC_ENABLED=true
OIDC_PROVIDER_NAME=Company SSO
OIDC_ISSUER_URL=https://auth.example.com/realms/webmacs
OIDC_CLIENT_ID=webmacs-client
OIDC_CLIENT_SECRET=your-client-secret-here
OIDC_SCOPES=openid email profile
OIDC_REDIRECT_URI=https://webmacs.example.com/api/v1/auth/sso/callback
OIDC_DEFAULT_ROLE=operator
OIDC_AUTO_CREATE_USERS=true
OIDC_FRONTEND_URL=https://webmacs.example.com
```

---

## How It Works

### User Creation & Linking

When a user authenticates via SSO for the first time:

1. WebMACS checks that the IdP confirmed `email_verified: true`
2. If a local user with the same email exists and is **not** an admin, the SSO identity is linked
3. If no local user exists and `OIDC_AUTO_CREATE_USERS` is `true`, a new user is created with the configured `OIDC_DEFAULT_ROLE`
4. The username is derived from the IdP's `preferred_username` claim (sanitized to `[a-zA-Z0-9._-]`)

!!! danger "Admin Safety"
    SSO logins **cannot** auto-link to existing admin accounts. An administrator must manually set the `sso_provider` and `sso_subject_id` fields on the admin user record to enable SSO for admin accounts. This prevents privilege escalation via IdP account takeover.

### Security Controls

| Control | Implementation |
|---|---|
| **PKCE S256** | Prevents authorization code interception |
| **Signed state token** | CSRF protection via HMAC-signed JWT with 10-minute expiry |
| **One-time auth code** | Backend issues a short-lived (60 s) one-time code instead of putting JWTs in URLs |
| **email_verified** | Rejects SSO logins where the IdP has not verified the email |
| **Admin linking refusal** | Auto-linking is blocked for admin accounts |
| **Username sanitization** | Only `[a-zA-Z0-9._-]` characters are allowed |
| **TTL-based discovery cache** | OIDC discovery metadata is cached for 1 hour |
| **Frontend URL validation** | Post-login redirect uses a dedicated config setting, not user-controlled data |

### Role Assignment

SSO users receive the role specified by `OIDC_DEFAULT_ROLE` (default: `viewer`). Administrators can change user roles after creation via the Users page or the API.

---

## Disabling SSO

Set `OIDC_ENABLED=false` (or remove the variable). The SSO button disappears from the login page. Existing SSO-linked users can still log in with username/password if they have a password set.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| SSO button not visible | `OIDC_ENABLED` is `false` or the `/sso/config` endpoint returns `enabled: false` | Set `OIDC_ENABLED=true` and verify `OIDC_ISSUER_URL` is reachable |
| "Email not verified" error | IdP did not set `email_verified: true` in the token | Verify the user's email in the IdP or adjust IdP configuration |
| Redirect mismatch error | `OIDC_REDIRECT_URI` does not match the URI registered in the IdP | Ensure exact match including protocol and path |
| "Auto-creation disabled" error | `OIDC_AUTO_CREATE_USERS=false` and no local user exists for this email | Create the user manually first, or enable auto-creation |
| Admin cannot SSO login | Auto-linking is refused for admin accounts | Manually set `sso_provider` and `sso_subject_id` on the admin user in the database |
| 500 on callback | Cannot reach the IdP's token endpoint | Check network connectivity and `OIDC_ISSUER_URL` |

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/auth/sso/config` | Public | Returns SSO status and provider name |
| `GET` | `/api/v1/auth/sso/authorize` | Public | Redirects to IdP for authentication |
| `GET` | `/api/v1/auth/sso/callback` | Public | Handles IdP callback (server-side) |
| `POST` | `/api/v1/auth/sso/exchange` | Public | Exchanges one-time code for JWT |

See the [REST API Reference](../api/rest.md#sso-single-sign-on) for full request/response details.

---

## Next Steps

- [Users & Auth](users.md) — roles and user management
- [Security](security.md) — full security controls reference
- [Environment Variables](../deployment/env-vars.md) — complete variable reference
