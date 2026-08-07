"""Binary sensor platform for Swatch."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import (
    SwatchDataUpdateCoordinator,
    SwatchEntity,
    get_audio_monitors,
    get_friendly_name,
    get_swatch_device_identifier,
    get_swatch_entity_unique_id,
    get_zones_and_objects,
)
from .api import SwatchApiClient, SwatchApiClientError
from .const import (
    ATTR_CLIENT,
    ATTR_CONFIG,
    ATTR_COORDINATOR,
    DOMAIN,
    NAME,
    SERVICE_DETECT_OBJECT,
)

_LOGGER: logging.Logger = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Binary sensor entry setup."""
    coordinator = hass.data[DOMAIN][entry.entry_id][ATTR_COORDINATOR]
    swatch_api = hass.data[DOMAIN][entry.entry_id][ATTR_CLIENT]
    swatch_config = hass.data[DOMAIN][entry.entry_id][ATTR_CONFIG]

    # Setup sensors
    async_add_entities(
        [
            SwatchObjectSensor(
                entry,
                coordinator,
                swatch_api,
                swatch_config,
                cam_name,
                zone_name,
                obj_name,
            )
            for cam_name, zone_name, obj_name in get_zones_and_objects(swatch_config)
        ]
        + [
            SwatchAudioMonitorSensor(entry, coordinator, monitor_name)
            for monitor_name in get_audio_monitors(swatch_config)
        ]
    )

    # Setup services
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_DETECT_OBJECT,
        {vol.Optional("image_url"): str},
        "detect_object",
    )


class SwatchObjectSensor(SwatchEntity, BinarySensorEntity, CoordinatorEntity):  # type: ignore[misc]
    """Swatch Object Sensor class."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: SwatchDataUpdateCoordinator,
        swatch_api: SwatchApiClient,
        swatch_config: dict[str, Any],
        cam_name: str,
        zone_name: str,
        obj_name: str,
    ) -> None:
        """Construct a new SwatchObjectSensor."""
        self._cam_name = cam_name
        self._zone_name = zone_name
        self._obj_name = obj_name
        self._is_on = False
        self._api = swatch_api
        self._swatch_config = swatch_config

        SwatchEntity.__init__(self, config_entry)
        CoordinatorEntity.__init__(self, coordinator)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this entity."""
        return get_swatch_entity_unique_id(
            self._config_entry.entry_id,
            "object_sensor",
            f"{self._zone_name}_{self._obj_name}",
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return {
            "identifiers": {
                get_swatch_device_identifier(self._config_entry, self._zone_name)
            },
            "via_device": get_swatch_device_identifier(self._config_entry),
            "name": get_friendly_name(self._zone_name),
            "model": self._get_model(),
            "manufacturer": NAME,
        }

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{get_friendly_name(self._zone_name)} {get_friendly_name(self._obj_name)}".title()

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        if self.coordinator.data:
            data = self.coordinator.data.get(self._obj_name, {}).get("result")
            if data is not None:
                try:
                    self._is_on = bool(data)
                except ValueError:
                    pass

        return self._is_on

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return the device class."""
        return BinarySensorDeviceClass.OCCUPANCY

    async def detect_object(self, image_url=None):
        """Detect an object."""
        try:
            if image_url:
                resp = await self._api.async_detect_camera(self._cam_name, image_url)
            else:
                resp = await self._api.async_detect_camera(self._cam_name)
        except SwatchApiClientError as exc:
            _LOGGER.error("Error detecting object for %s: %s", self._cam_name, exc)
            return

        if resp:
            result = (
                resp.get(self._zone_name, {})
                .get(self._obj_name, {})
                .get("result", False)
            )
            self._is_on = result
        else:
            _LOGGER.error(f"detect_object response: {resp}")


class SwatchAudioMonitorSensor(  # type: ignore[misc]
    SwatchEntity, BinarySensorEntity, CoordinatorEntity
):
    """Swatch Audio Monitor Sensor class.

    Reports whether swatch currently hears sustained, steady loud noise
    (e.g. a kitchen hood fan) on a camera's audio stream. See swatch's
    audio_monitors config for how this is detected -- it's a heuristic
    (loud + spectrally steady), not true sound classification.
    """

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: SwatchDataUpdateCoordinator,
        monitor_name: str,
    ) -> None:
        """Construct a new SwatchAudioMonitorSensor."""
        self._monitor_name = monitor_name

        SwatchEntity.__init__(self, config_entry)
        CoordinatorEntity.__init__(self, coordinator)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this entity."""
        return get_swatch_entity_unique_id(
            self._config_entry.entry_id,
            "audio_monitor",
            self._monitor_name,
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return {
            "identifiers": {
                get_swatch_device_identifier(self._config_entry, self._monitor_name)
            },
            "via_device": get_swatch_device_identifier(self._config_entry),
            "name": get_friendly_name(self._monitor_name),
            "model": self._get_model(),
            "manufacturer": NAME,
        }

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return get_friendly_name(self._monitor_name)

    @property
    def is_on(self) -> bool:
        """Return true if sustained loud, steady noise is currently heard."""
        if self.coordinator.data:
            data = self.coordinator.data.get(self._monitor_name, {}).get("result")
            if data is not None:
                return bool(data)

        return False

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return the device class."""
        return BinarySensorDeviceClass.RUNNING
