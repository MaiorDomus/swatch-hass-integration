"""Tests for the swatch config flow."""

from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_URL
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.swatch.config_flow import get_config_entry_title
from custom_components.swatch.const import DOMAIN

HOST = "http://192.168.1.10:4500"


def test_get_config_entry_title_strips_scheme():
    """The entry title should drop the http:// scheme to save space in the UI."""
    assert get_config_entry_title(HOST) == "192.168.1.10:4500"


async def test_show_user_form(hass):
    """The first step with no input should show the user form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_user_flow_success_creates_entry(hass, requests_mock):
    """A reachable host should create a config entry.

    Creating the entry triggers Home Assistant to call async_setup_entry for
    real; that's covered separately in test_init.py, so it's stubbed out here
    to keep this test focused on the flow itself.
    """
    requests_mock.get(HOST, status_code=200)

    with patch("custom_components.swatch.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_URL: HOST}
        )
        await hass.async_block_till_done()

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "192.168.1.10:4500"
    assert result["data"] == {CONF_URL: HOST}


async def test_user_flow_cannot_connect(hass, requests_mock):
    """An unreachable host should show a cannot_connect error and stay on the form."""
    requests_mock.get(HOST, status_code=500)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: HOST}
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_aborts_on_duplicate_host(hass, requests_mock):
    """Adding the same host twice should abort instead of creating a duplicate."""
    requests_mock.get(HOST, status_code=200)
    existing_entry = MockConfigEntry(
        domain=DOMAIN, unique_id=HOST, data={CONF_URL: HOST}
    )
    existing_entry.add_to_hass(hass)

    with patch("custom_components.swatch.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_URL: HOST}
        )
        await hass.async_block_till_done()

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_flow_unexpected_exception(hass, requests_mock):
    """An unexpected exception talking to the host should show an unknown error."""
    requests_mock.get(HOST, exc=ConnectionResetError)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: HOST}
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}
