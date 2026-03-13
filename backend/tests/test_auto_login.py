import asyncio
import time
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from webmacs_backend.models import User
from webmacs_backend.security import hash_password


@pytest.mark.asyncio
async def test_auto_login_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful auto-login"""
    # Create test user
    user = User(
        email="autotest@example.com",
        username="autotest",
        password_hash=hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()

    # Test auto-login
    response = await client.post(
        "/api/v1/auth/auto-login",
        json={
            "email": "autotest@example.com",
            "password": "password123"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Auto-login successful."
    assert "access_token" in data
    assert data["public_id"] == user.public_id


@pytest.mark.asyncio
async def test_auto_login_invalid_credentials(client: AsyncClient, db_session: AsyncSession):
    """Test auto-login with invalid credentials"""
    response = await client.post(
        "/api/v1/auth/auto-login",
        json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_auto_login_rate_limiting(client: AsyncClient, db_session: AsyncSession):
    """Test auto-login rate limiting (10 attempts per 5 minutes)"""
    # Create test user
    user = User(
        email="ratelimit@example.com",
        username="ratelimit",
        password_hash=hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()

    # Make 10 failed attempts (should be allowed)
    for i in range(10):
        response = await client.post(
            "/api/v1/auth/auto-login",
            json={
                "email": "ratelimit@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401

    # 11th attempt should be rate limited
    response = await client.post(
        "/api/v1/auth/auto-login",
        json={
            "email": "ratelimit@example.com",
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == 429
    assert "Too many auto-login attempts" in response.json()["detail"]
    assert "Retry-After" in response.headers


@pytest.mark.asyncio
async def test_regular_vs_auto_login_rate_limits(client: AsyncClient, db_session: AsyncSession):
    """Test that regular login and auto-login have separate rate limits"""
    # Create test user
    user = User(
        email="separate@example.com",
        username="separate",
        password_hash=hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()

    # Make 5 failed regular login attempts (should hit regular limit)
    for i in range(5):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "separate@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401

    # 6th regular login should be rate limited
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "separate@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 429

    # But auto-login should still work (different rate limit)
    response = await client.post(
        "/api/v1/auth/auto-login",
        json={
            "email": "separate@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401  # Wrong password, but not rate limited


@pytest.mark.asyncio
async def test_rate_limit_status_endpoint(
    client: AsyncClient, 
    db_session: AsyncSession,
    admin_user: User,
    auth_headers: dict
):
    """Test rate limit status endpoint"""
    # Make some failed attempts
    for i in range(3):
        await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword"
            }
        )

    for i in range(2):
        await client.post(
            "/api/v1/auth/auto-login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword"
            }
        )

    # Check status as admin
    response = await client.get(
        "/api/v1/auth/rate-limit-status?email=test@example.com",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    
    assert data["email"] == "test@example.com"
    assert data["regular_attempts"]["recent_count"] == 3
    assert data["regular_attempts"]["max_allowed"] == 5
    assert data["auto_login_attempts"]["recent_count"] == 2
    assert data["auto_login_attempts"]["max_allowed"] == 10
    assert not data["regular_attempts"]["is_locked"]
    assert not data["auto_login_attempts"]["is_locked"]


@pytest.mark.asyncio
async def test_clear_rate_limit_endpoint(
    client: AsyncClient,
    db_session: AsyncSession, 
    admin_user: User,
    auth_headers: dict
):
    """Test clearing rate limits"""
    # Create rate limit by failing attempts
    for i in range(5):
        await client.post(
            "/api/v1/auth/login",
            json={
                "email": "cleartest@example.com",
                "password": "wrongpassword"
            }
        )

    # Verify rate limit is active
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "cleartest@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 429

    # Clear rate limit as admin
    response = await client.post(
        "/api/v1/auth/clear-rate-limit?email=cleartest@example.com",
        headers=auth_headers
    )
    assert response.status_code == 200

    # Verify rate limit is cleared
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "cleartest@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401  # Wrong password, but not rate limited


@pytest.mark.asyncio
async def test_rate_limit_cleanup_over_time():
    """Test that rate limit entries are cleaned up over time"""
    from webmacs_backend.api.v1.auth import login_attempts, record_login_attempt, check_rate_limit
    
    email = "cleanup@example.com"
    
    # Record some attempts
    for i in range(3):
        record_login_attempt(email)
    
    assert len(login_attempts[email]) == 3
    
    # Mock time passing (16 minutes)
    with patch('time.time', return_value=time.time() + 16 * 60):
        # This should clean up old attempts
        try:
            check_rate_limit(email)
        except:
            pass  # We don't care about the exception, just the cleanup
    
    # Old attempts should be cleaned up
    assert len(login_attempts.get(email, [])) == 0


@pytest.mark.asyncio
async def test_auto_login_successful_after_failed_attempts(
    client: AsyncClient, 
    db_session: AsyncSession
):
    """Test that successful auto-login clears failed attempts"""
    # Create test user
    user = User(
        email="successafter@example.com",
        username="successafter",
        password_hash=hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()

    # Make some failed attempts
    for i in range(3):
        response = await client.post(
            "/api/v1/auth/auto-login",
            json={
                "email": "successafter@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401

    # Successful login should clear attempts
    response = await client.post(
        "/api/v1/auth/auto-login",
        json={
            "email": "successafter@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 200

    # Should be able to make more failed attempts without being rate limited immediately
    for i in range(5):
        response = await client.post(
            "/api/v1/auth/auto-login",
            json={
                "email": "successafter@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
