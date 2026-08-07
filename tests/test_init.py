"""Tests for the swatch integration setup/unload and helper functions."""

import aiohttp
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_URL
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.swatch import (
    get_audio_monitors,
    get_cameras_and_zones,
    get_friendly_name,
    get_swatch_device_identifier,
    get_swatch_entity_unique_id,
    get_zones_and_objects,
)
from custom_components.swatch.const import (
    ATTR_CLIENT,
    ATTR_CONFIG,
    ATTR_COORDINATOR,
    DOMAIN,
)

HOST = "http://192.168.1.10:4500"

SWATCH_API_CONFIG = {
    "cameras": {
        "front_door": {
            "zones": {
                "porch": {
                    "objects": ["person"],
                },
            },
        },
    },
}


def test_get_friendly_name():
    assert get_friendly_name("front_door") == "Front Door"


def test_get_zones_and_objects():
    assert get_zones_and_objects(SWATCH_API_CONFIG) == {
        ("front_door", "porch", "person"),
    }


def test_get_cameras_and_zones():
    assert get_cameras_and_zones(SWATCH_API_CONFIG) == {"front_door", "porch"}


def test_get_audio_monitors():
    config = {**SWATCH_API_CONFIG, "audio_monitors": {"kitchen_hood": {}}}
    assert get_audio_monitors(config) == {"kitchen_hood"}


def test_get_audio_monitors_defaults_to_empty():
    assert get_audio_monitors(SWATCH_API_CONFIG) == set()


def test_get_swatch_entity_unique_id():
    assert (
        get_swatch_entity_unique_id("entry123", "object_sensor", "porch_person")
        == "entry123:object_sensor:porch_person"
    )


def test_get_swatch_device_identifier_without_camera_name():
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_URL: HOST})
    assert get_swatch_device_identifier(entry) == (DOMAIN, entry.entry_id)


def test_get_swatch_device_identifier_with_camera_name():
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_URL: HOST})
    assert get_swatch_device_identifier(entry, "Front Door") == (
        DOMAIN,
        f"{entry.entry_id}:front_door",
    )


async def test_setup_and_unload_entry(hass, aioclient_mock):
    """A full async_setup_entry -> async_unload_entry round trip."""
    aioclient_mock.get(f"{HOST}/api/all/latest", json={})
    aioclient_mock.get(f"{HOST}/api/config", json=SWATCH_API_CONFIG)

    entry = MockConfigEntry(domain=DOMAIN, data={CONF_URL: HOST})
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert ATTR_CLIENT in hass.data[DOMAIN][entry.entry_id]
    assert ATTR_COORDINATOR in hass.data[DOMAIN][entry.entry_id]
    assert hass.data[DOMAIN][entry.entry_id][ATTR_CONFIG] == SWATCH_API_CONFIG

    # the binary_sensor platform should have created one entity for the
    # single camera/zone/object combination in SWATCH_API_CONFIG
    entities = hass.states.async_entity_ids("binary_sensor")
    assert len(entities) == 1

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert entry.entry_id not in hass.data[DOMAIN]


async def test_setup_entry_creates_audio_monitor_entity(hass, aioclient_mock):
    """A config with both zones/objects and audio_monitors should create an
    entity for each."""
    config_with_audio = {**SWATCH_API_CONFIG, "audio_monitors": {"kitchen_hood": {}}}
    aioclient_mock.get(
        f"{HOST}/api/all/latest", json={"kitchen_hood": {"result": True}}
    )
    aioclient_mock.get(f"{HOST}/api/config", json=config_with_audio)

    entry = MockConfigEntry(domain=DOMAIN, data={CONF_URL: HOST})
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entities = hass.states.async_entity_ids("binary_sensor")
    assert len(entities) == 2


async def test_setup_entry_fails_when_config_unreachable(hass, aioclient_mock):
    """If the swatch server can't be reached for /api/config, setup should fail."""
    aioclient_mock.get(f"{HOST}/api/all/latest", json={})
    aioclient_mock.get(f"{HOST}/api/config", exc=aiohttp.ClientConnectionError)

    entry = MockConfigEntry(domain=DOMAIN, data={CONF_URL: HOST})
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
