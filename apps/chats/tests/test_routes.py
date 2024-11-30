import sys
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from pathlib import Path
import logging
from datetime import timedelta

from main import app

from apps.auth.services.dependencies import TokenService

sys.path.append(str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


@pytest.mark.asyncio
async def test_chat_activities():
    test_user_id = uuid4()
    test_chat = f"test_channel_{uuid4()}"

    token_service = TokenService(session=None)
    access_token = token_service.create_access_token(test_user_id, expires_delta=timedelta(minutes=30))
    headers = {"Authorization": f"Bearer {access_token}"}

    logger.debug(f"Generated Token: {access_token}")
    logger.debug(f"Authorization header: {headers}")

    mock_chat_service = AsyncMock()
    mock_user_service = AsyncMock()

    mock_create_chat = AsyncMock()
    mock_create_chat.return_value = AsyncMock(id=uuid4(), name=test_chat)
    mock_chat_service.create_chat = mock_create_chat

    mock_user_service.get_user_by_id.return_value = AsyncMock(id=test_user_id, username="test_user")
    mock_create_user_chat_link = AsyncMock()
    mock_create_user_chat_link.return_value = None

    
    logger.debug(f"Mocked User: id={mock_user_service.get_user_by_id.return_value.id}, username={mock_user_service.get_user_by_id.return_value.username}")

    with patch("apps.users.services.users.Service.get_user_by_id", return_value=mock_user_service.get_user_by_id.return_value), \
         patch("apps.chats.services.chats.get_service", return_value=mock_chat_service), \
         \
         patch("apps.chats.services.chats.Service.create_user_chat_link", mock_create_user_chat_link), \
         patch("apps.auth.services.dependencies.TokenService.create_access_token", return_value=access_token):

        client = TestClient(app)

        try:
            with client.websocket_connect(f"/chats/api/v1/ws/{test_chat}", headers=headers) as websocket:
                logger.debug("WebSocket connection established.")       
    
                join_message = websocket.receive_text()
                logger.debug(f"Received message: {join_message}")

                assert "Вы вошли в чат" in join_message, f"Expected 'Вы вошли в чат', but got: {join_message}"

                test_message = "Hello, World!"
                websocket.send_text(test_message)

                for connection in mock_chat_service.active_channels[test_chat]:
                    message = websocket.receive_text()
                    assert test_message in message, f"Expected message '{test_message}' but got {message}"

                logger.debug("Test message successfully sent.")

        except Exception as e:
            logger.error(f"Error during WebSocket connection: {str(e)}")
            raise e