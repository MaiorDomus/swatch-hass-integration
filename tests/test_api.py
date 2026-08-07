"""Tests for the swatch API client."""

import aiohttp
import pytest

from custom_components.swatch.api import SwatchApiClient, SwatchApiClientError

HOST = "http://192.168.1.10:4500"


@pytest.fixture
async def client(hass, aioclient_mock):
    """A SwatchApiClient backed by a mocked aiohttp session, closed after use."""
    session = aioclient_mock.create_session(hass.loop)
    try:
        yield SwatchApiClient(HOST, session)
    finally:
        await session.close()


async def test_async_get_config(aioclient_mock, client):
    """A successful GET should return the decoded JSON body."""
    aioclient_mock.get(f"{HOST}/api/config", json={"cameras": {}})

    result = await client.async_get_config()

    assert result == {"cameras": {}}


async def test_async_get_version_returns_text(aioclient_mock, client):
    """async_get_version doesn't decode JSON, it returns raw text."""
    aioclient_mock.get(f"{HOST}/api/version", text="1.2.3")

    result = await client.async_get_version()

    assert result == "1.2.3"


async def test_async_get_object_state(aioclient_mock, client):
    """async_get_object_state should hit the /api/<object>/latest endpoint."""
    aioclient_mock.get(f"{HOST}/api/all/latest", json={"person": {"result": True}})

    result = await client.async_get_object_state("all")

    assert result == {"person": {"result": True}}


async def test_async_detect_camera_without_image_url(aioclient_mock, client):
    """POST without an image_url should still hit the detect endpoint."""
    aioclient_mock.post(f"{HOST}/api/front/detect", json={"front": {}})

    result = await client.async_detect_camera("front")

    assert result == {"front": {}}


async def test_async_detect_camera_with_image_url(aioclient_mock, client):
    """POST with an image_url should still hit the detect endpoint."""
    aioclient_mock.post(f"{HOST}/api/front/detect", json={"front": {}})

    result = await client.async_detect_camera("front", "http://camera/snap.jpg")

    assert result == {"front": {}}


async def test_api_wrapper_raises_on_connection_error(aioclient_mock, client):
    """An aiohttp.ClientError should be converted to SwatchApiClientError."""
    aioclient_mock.get(f"{HOST}/api/config", exc=aiohttp.ClientConnectionError)

    with pytest.raises(SwatchApiClientError):
        await client.async_get_config()


async def test_api_wrapper_raises_on_timeout(aioclient_mock, client):
    """A request that raises TimeoutError should be converted to SwatchApiClientError."""
    aioclient_mock.get(f"{HOST}/api/config", exc=TimeoutError)

    with pytest.raises(SwatchApiClientError):
        await client.async_get_config()
