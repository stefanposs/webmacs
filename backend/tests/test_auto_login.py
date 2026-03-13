import asyncio
import time
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from webmacs_backend.models import User
from webmacs_backend.security import get_password_hash


@pytest.mark.asyncio
async def test_auto_login_success(client: AsyncClient, session: AsyncSession):
    """Test successful auto-login"""
    # Create test user
    user = User(
        email="autotest@example.com",
        username="autotest",
        hashed_password=get_password_hash("password123"),
        admin=False
    )
    session.add(user)
    await session.commit()

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
async def test_auto_login_invalid_credentials(client: AsyncClient, session: AsyncSession):
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
async def test_auto_login_rate_limiting(client: AsyncClient, session: AsyncSession):
    """Test auto-login rate limiting (10 attempts per 5 minutes)"""
    # Create test user
    user = User(
        email="ratelimit@example.com",
        username="ratelimit",
        hashed_password=get_password_hash("password123"),
        admin=False
    )
    session.add(user)
    await session.commit()

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
async def test_regular_vs_auto_login_rate_limits(client: AsyncClient, session: AsyncSession):
    """Test that regular login and auto-login have separate rate limits"""
    # Create test user
    user = User(
        email="separate@example.com",
        username="separate",
        hashed_password=get_password_hash("password123"),
        admin=False
    )
    session.add(user)
    await session.commit()

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
