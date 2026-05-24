"""Tests for Heidenhain OPC UA endpoint URL resolution."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.controllers.heidenhain.endpoint import (
    DEFAULT_HEIDENHAIN_ENDPOINT_PATH,
    apply_connect_host,
    build_endpoint_url,
    pick_nc_endpoint_url,
    resolve_endpoint_url,
)


def test_build_endpoint_url_without_path():
    assert build_endpoint_url("192.168.1.10", 4840) == "opc.tcp://192.168.1.10:4840"


def test_build_endpoint_url_with_path():
    assert (
        build_endpoint_url("192.168.1.10", 4840, "/HEIDENHAIN/NC")
        == "opc.tcp://192.168.1.10:4840/HEIDENHAIN/NC"
    )


def test_build_endpoint_url_normalizes_path_without_leading_slash():
    assert (
        build_endpoint_url("192.168.1.10", 4840, "HEIDENHAIN/NC")
        == "opc.tcp://192.168.1.10:4840/HEIDENHAIN/NC"
    )


def test_apply_connect_host_replaces_hostname():
    url = "opc.tcp://SHAT_CHAMPION-340595:4840/HEIDENHAIN/NC"
    assert apply_connect_host(url, "192.168.86.73") == "opc.tcp://192.168.86.73:4840/HEIDENHAIN/NC"


def test_pick_nc_endpoint_url_selects_nc_path():
    ep1 = MagicMock()
    ep1.EndpointUrl = "opc.tcp://HOST:4840/"
    ep2 = MagicMock()
    ep2.EndpointUrl = "opc.tcp://HOST:4840/HEIDENHAIN/NC"
    chosen = pick_nc_endpoint_url([ep1, ep2], "192.168.86.73")
    assert chosen == "opc.tcp://192.168.86.73:4840/HEIDENHAIN/NC"


def test_pick_nc_endpoint_url_case_insensitive():
    ep = MagicMock()
    ep.EndpointUrl = "opc.tcp://HOST:4840/heidenhain/nc"
    chosen = pick_nc_endpoint_url([ep], "10.0.0.5")
    assert chosen == "opc.tcp://10.0.0.5:4840/heidenhain/nc"


def test_pick_nc_endpoint_url_returns_none_when_missing():
    ep = MagicMock()
    ep.EndpointUrl = "opc.tcp://HOST:4840/"
    assert pick_nc_endpoint_url([ep], "10.0.0.5") is None


@pytest.mark.asyncio
async def test_resolve_endpoint_url_uses_explicit_url():
    resolved = await resolve_endpoint_url(
        "192.168.1.10",
        4840,
        endpoint_url="opc.tcp://custom:4840/HEIDENHAIN/NC",
        auto_discover=True,
    )
    assert resolved == "opc.tcp://custom:4840/HEIDENHAIN/NC"


@pytest.mark.asyncio
async def test_resolve_endpoint_url_discovers_when_auto_discover():
    with patch(
        "app.controllers.heidenhain.endpoint.discover_nc_endpoint_url",
        new_callable=AsyncMock,
        return_value="opc.tcp://192.168.1.10:4840/HEIDENHAIN/NC",
    ) as mock_discover:
        resolved = await resolve_endpoint_url("192.168.1.10", 4840, auto_discover=True)
    mock_discover.assert_awaited_once_with("192.168.1.10", 4840, timeout=10.0)
    assert resolved == "opc.tcp://192.168.1.10:4840/HEIDENHAIN/NC"


@pytest.mark.asyncio
async def test_resolve_endpoint_url_falls_back_to_constructed_path():
    with patch(
        "app.controllers.heidenhain.endpoint.discover_nc_endpoint_url",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resolved = await resolve_endpoint_url(
            "192.168.1.10",
            4840,
            endpoint_path="/HEIDENHAIN/NC",
            auto_discover=True,
        )
    assert resolved == "opc.tcp://192.168.1.10:4840/HEIDENHAIN/NC"


@pytest.mark.asyncio
async def test_resolve_endpoint_url_default_path_when_discovery_disabled():
    resolved = await resolve_endpoint_url(
        "192.168.1.10",
        4840,
        auto_discover=False,
    )
    assert resolved == build_endpoint_url("192.168.1.10", 4840, DEFAULT_HEIDENHAIN_ENDPOINT_PATH)
