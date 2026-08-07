"""Tests for the swatch binary_sensor platform."""

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import ATTR_MODEL, CONF_URL
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.swatch import SwatchDataUpdateCoordinator
from custom_components.swatch.api import SwatchApiClient, SwatchApiClientError
from custom_components.swatch.binary_sensor import (
    SwatchAudioMonitorSensor,
    SwatchObjectSensor,
)
from custom_components.swatch.const import DOMAIN

HOST = "http://192.168.1.10:4500"


@pytest.fixture
async def make_sensor(hass, aioclient_mock):
    """Factory for a SwatchObjectSensor, closing its session after the test."""
    sessions = []

    def _factory(coordinator_data=None):
        entry = MockConfigEntry(domain=DOMAIN, data={CONF_URL: HOST})
        entry.add_to_hass(hass)

        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = {ATTR_MODEL: "1.0.0/1.0.0"}

        session = aioclient_mock.create_session(hass.loop)
        sessions.append(session)
        client = SwatchApiClient(HOST, session)
        coordinator = SwatchDataUpdateCoordinator(hass, client=client)
        coordinator.data = coordinator_data

        sensor = SwatchObjectSensor(
            entry,
            coordinator,
            client,
            swatch_config={"cameras": {}},
            cam_name="front_door",
            zone_name="porch",
            obj_name="person",
        )
        sensor.hass = hass
        return sensor

    try:
        yield _factory
    finally:
        for session in sessions:
            await session.close()


async def test_unique_id(make_sensor):
    sensor = make_sensor()
    assert sensor.unique_id.endswith(":object_sensor:porch_person")


async def test_name(make_sensor):
    sensor = make_sensor()
    assert sensor.name == "Porch Person"


async def test_device_class_is_occupancy(make_sensor):
    sensor = make_sensor()
    assert sensor.device_class == BinarySensorDeviceClass.OCCUPANCY


async def test_device_info(make_sensor):
    sensor = make_sensor()
    info = sensor.device_info
    assert info["name"] == "Porch"
    assert info["model"] == "1.0.0/1.0.0"
    assert info["manufacturer"] == "Swatch"


async def test_is_on_true_when_coordinator_reports_result(make_sensor):
    sensor = make_sensor(coordinator_data={"person": {"result": True}})
    assert sensor.is_on is True


async def test_is_on_false_when_coordinator_reports_no_result(make_sensor):
    sensor = make_sensor(coordinator_data={"person": {"result": False}})
    assert sensor.is_on is False


async def test_is_on_defaults_false_with_no_coordinator_data(make_sensor):
    sensor = make_sensor(coordinator_data=None)
    assert sensor.is_on is False


async def test_detect_object_sets_is_on_from_response(aioclient_mock, make_sensor):
    aioclient_mock.post(
        f"{HOST}/api/front_door/detect",
        json={"porch": {"person": {"result": True}}},
    )
    sensor = make_sensor()

    await sensor.detect_object()

    assert sensor.is_on is True


async def test_detect_object_swallows_api_errors(aioclient_mock, make_sensor):
    aioclient_mock.post(f"{HOST}/api/front_door/detect", exc=SwatchApiClientError)
    sensor = make_sensor()

    # should not raise
    await sensor.detect_object()


@pytest.fixture
async def make_audio_sensor(hass, aioclient_mock):
    """Factory for a SwatchAudioMonitorSensor, closing its session after the test."""
    sessions = []

    def _factory(coordinator_data=None):
        entry = MockConfigEntry(domain=DOMAIN, data={CONF_URL: HOST})
        entry.add_to_hass(hass)

        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = {ATTR_MODEL: "1.0.0/1.0.0"}

        session = aioclient_mock.create_session(hass.loop)
        sessions.append(session)
        client = SwatchApiClient(HOST, session)
        coordinator = SwatchDataUpdateCoordinator(hass, client=client)
        coordinator.data = coordinator_data

        sensor = SwatchAudioMonitorSensor(entry, coordinator, "kitchen_hood")
        sensor.hass = hass
        return sensor

    try:
        yield _factory
    finally:
        for session in sessions:
            await session.close()


async def test_audio_monitor_unique_id(make_audio_sensor):
    sensor = make_audio_sensor()
    assert sensor.unique_id.endswith(":audio_monitor:kitchen_hood")


async def test_audio_monitor_name(make_audio_sensor):
    sensor = make_audio_sensor()
    assert sensor.name == "Kitchen Hood"


async def test_audio_monitor_device_class_is_running(make_audio_sensor):
    sensor = make_audio_sensor()
    assert sensor.device_class == BinarySensorDeviceClass.RUNNING


async def test_audio_monitor_device_info(make_audio_sensor):
    sensor = make_audio_sensor()
    info = sensor.device_info
    assert info["name"] == "Kitchen Hood"
    assert info["model"] == "1.0.0/1.0.0"
    assert info["manufacturer"] == "Swatch"


async def test_audio_monitor_is_on_true_when_coordinator_reports_result(
    make_audio_sensor,
):
    sensor = make_audio_sensor(coordinator_data={"kitchen_hood": {"result": True}})
    assert sensor.is_on is True


async def test_audio_monitor_is_on_false_when_coordinator_reports_no_result(
    make_audio_sensor,
):
    sensor = make_audio_sensor(coordinator_data={"kitchen_hood": {"result": False}})
    assert sensor.is_on is False


async def test_audio_monitor_is_on_defaults_false_with_no_coordinator_data(
    make_audio_sensor,
):
    sensor = make_audio_sensor(coordinator_data=None)
    assert sensor.is_on is False
