import random
import sys
import uuid
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import status
from apps.users.schemas.users import UserCreateResponse
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from main import app

client = TestClient(app)

@pytest.fixture
def mock_service():
    mock = AsyncMock()
    mock.create_user.return_value = UserCreateResponse(
        id="123e4567-e89b-12d3-a456-426614174000",
        username="testuser",
        email="testuser@example.com",
        phone="+79119422134",
        role="user",
        created_at="2024-08-31T12:34:56",
        updated_at="2024-08-31T12:34:56"
    )
    return mock

@pytest.fixture
def mock_dependencies(mock_service):
    with patch("apps.users.services.users.get_service", return_value=mock_service):
        yield

def test_create_user_success(mock_dependencies):
    username = f"testuser_{uuid.uuid4()}"
    email = f"testuser_{uuid.uuid4()}@example.com"
    phone_number = "+79" + ''.join(random.choices("0123456789", k=9)) 

    user_data = {
        "username": username,
        "email": email,
        "hashed_pass": "securepassword",
        "role": "user",
        "phone": phone_number
    }

    response = client.post("/users/api/v1/create", json=user_data)

    assert response.status_code == status.HTTP_201_CREATED, f"Response error: {response.json()}"
    
    data = response.json()
    
    assert isinstance(data["id"], str)
    assert len(data["id"]) == 36

    assert data["username"] == username
    assert data["email"] == email
    assert data["role"] == "user"
    assert data["phone"] == phone_number
    
    assert "created_at" in data
    assert "updated_at" in data


def test_create_user_validation_error(mock_dependencies):
    user_data = {
        "username": "testuser",
        "password": "securepassword",
        "role": "user",
        "phone": "+79119223456"
    }

    response = client.post("/users/api/v1/create", json=user_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert "email" in str(data)