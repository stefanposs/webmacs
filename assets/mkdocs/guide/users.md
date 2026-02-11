# User Management

WebMACS supports multiple user accounts with two roles: **Operator** and **Admin**. Admins can create, manage, and delete user accounts.

!!! info "Admin only"
    The Users page is only visible to admin accounts.

---

## User Roles

| Role | Access |
|---|---|
| **Operator** | Dashboard, Events, Experiments, Datapoints, CSV Export, Logs |
| **Admin** | Everything above **+** Rules, Webhooks, OTA Updates, User Management |

The sidebar automatically hides admin-only pages for operator accounts.

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

New users are created as **Operators** by default.

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

## Security Best Practices

!!! tip "Recommendations"
    - **Change the default admin password** immediately after first login
    - **Use strong passwords** — minimum 8 characters, mix of letters, numbers, and symbols
    - **Set a strong `SECRET_KEY`** — in production, must be at least 32 characters
    - **Create operator accounts** for regular users — don't share admin credentials
    - **Use HTTPS** in production — tokens are sent in HTTP headers and must be protected in transit

---

## Next Steps

- [Configuration](../getting-started/configuration.md) — environment variables for auth settings
- [Dashboard](dashboard.md) — get started monitoring data
- [API Reference](../api/rest.md) — full user and auth endpoint documentation
