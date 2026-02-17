# User Management

WebMACS supports multiple user accounts with three roles: **Admin**, **Operator**, and **Viewer**. Admins can create, manage, and delete user accounts and generate API tokens.

!!! info "Admin only"
    The Users page is only visible to admin accounts.

---

## User Roles

WebMACS uses a hierarchical RBAC model: **Admin > Operator > Viewer**.

| Role | Access |
|---|---|
| **Viewer** | Dashboard (read-only), Events, Experiments, Datapoints, CSV Export, Logs |
| **Operator** | Everything Viewer can do **+** create/edit experiments, events, and datapoints |
| **Admin** | Everything above **+** Rules, Webhooks, OTA Updates, User Management, API Tokens, Plugin Management |

The sidebar automatically hides pages that the current user's role does not permit.

### Role Hierarchy

Roles are compared hierarchically — an admin can perform any action an operator or viewer can, and an operator can perform any action a viewer can:

```
admin (3) > operator (2) > viewer (1)
```

When creating a user via the UI, you select one of the three roles. The default role for new users is **Viewer**.

### SSO Users

Users created via [OIDC SSO](sso.md) receive the role configured by `OIDC_DEFAULT_ROLE` (default: `viewer`). Admins can change SSO user roles via the Users page.

---

## Default Admin Account

On first startup, WebMACS creates an initial admin account from environment variables:

| Variable | Default |
|---|---|
| `INITIAL_ADMIN_EMAIL` | `admin@webmacs.io` |
| `INITIAL_ADMIN_USERNAME` | `admin` |
| `INITIAL_ADMIN_PASSWORD` | `admin123` |

!!! danger "Change the default password immediately"
    The default credentials are publicly documented. Change them as soon as the system is deployed, especially in production environments.

---

## Managing Users via the UI

### Viewing Users

Navigate to **Users** in the sidebar. The table shows:

| Column | Description |
|---|---|
| **Username** | Login name |
| **Email** | Email address |
| **Role** | :material-shield-lock: Admin or :material-account: User badge |
| **Registered** | Account creation date |
| **Actions** | Delete button |

### Creating a User

1. Click **Add User**
2. Fill in:
    - **Username** — 2–50 characters
    - **Email** — must be unique
    - **Password** — minimum 8 characters
3. Click **Create**

New users are created as **Viewers** by default. You can select a different role during creation.

### Deleting a User

Click the :material-delete: delete button on a user row and confirm.

!!! warning "Cannot delete yourself"
    You cannot delete the account you're currently logged in with.

---

## Managing Users via API

### List All Users (Admin Only)

```bash
curl http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer $TOKEN"
```

### Create a User (Admin Only)

```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "operator1",
    "email": "operator1@example.com",
    "password": "securepassword123"
  }'
```

### Update a User (Self or Admin)

```bash
curl -X PUT http://localhost:8000/api/v1/users/$USER_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"password": "new-secure-password"}'
```

### Delete a User (Admin Only)

```bash
curl -X DELETE http://localhost:8000/api/v1/users/$USER_ID \
  -H "Authorization: Bearer $TOKEN"
```

---

## Authentication

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@webmacs.io",
    "password": "admin123"
  }'
```

Returns:

```json
{
  "access_token": "eyJhbGci...",
  "public_id": "usr_abc123",
  "username": "admin"
}
```

### Using the Token

Include the token in all subsequent requests:

```bash
-H "Authorization: Bearer eyJhbGci..."
```

Tokens expire after **24 hours** by default (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`).

### Logout

```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer $TOKEN"
```

Logout **blacklists** the token — it cannot be reused even before expiry. Expired blacklisted tokens are cleaned up automatically.

---

## API Tokens

API tokens provide long-lived, machine-friendly authentication for scripts, CI pipelines, and integrations. Unlike JWTs, API tokens do not expire automatically (unless an expiry date is set) and are bound to a specific user.

### Token Format

API tokens use the prefix `wm_` followed by 43 random characters:

```
wm_Ab3Cd5Ef7Gh9Ij1Kl3Mn5Op7Qr9St1Uv3Wx5Yz7Ab3
```

Only the **SHA-256 hash** of the token is stored in the database. The plaintext token is shown **only once** at creation time.

### Creating an API Token

1. Navigate to **API Tokens** in the sidebar (Admin only)
2. Click **Create Token**
3. Enter a descriptive **name** (e.g. "CI Pipeline")
4. Optionally set an **expiration date**
5. Click **Create** — copy the displayed token immediately

Via API:

```bash
curl -X POST http://localhost:8000/api/v1/tokens \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"name": "CI Pipeline", "expires_at": "2026-12-31T23:59:59Z"}'
```

### Using an API Token

Include the token in the `Authorization` header just like a JWT:

```bash
curl http://localhost:8000/api/v1/events \
  -H "Authorization: Bearer wm_Ab3Cd5Ef7Gh9..."
```

API tokens inherit the **role and permissions** of the user who created them.

### Listing & Deleting Tokens

- Users see their own tokens; admins see all tokens
- Delete a token via the UI or `DELETE /api/v1/tokens/{public_id}`

!!! warning "Token Security"
    Treat API tokens like passwords. Never commit them to version control or share them in plain text.

---

## Security Best Practices

!!! tip "Recommendations"
    - **Change the default admin password** immediately after first login
    - **Use strong passwords** — minimum 8 characters, mix of letters, numbers, and symbols
    - **Set a strong `SECRET_KEY`** — in production, must be at least 32 characters
    - **Create operator/viewer accounts** for regular users — don't share admin credentials
    - **Use HTTPS** in production — tokens are sent in HTTP headers and must be protected in transit
    - **Use API tokens** for automation — they can be revoked independently without affecting user sessions
    - **Enable SSO** for enterprise environments — centralized authentication with OIDC

---

## Next Steps

- [Single Sign-On (OIDC)](sso.md) — configure SSO with your Identity Provider
- [Configuration](../getting-started/configuration.md) — environment variables for auth settings
- [Dashboard](dashboard.md) — get started monitoring data
- [API Reference](../api/rest.md) — full user and auth endpoint documentation
