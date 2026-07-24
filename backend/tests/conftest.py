"""Shared fixtures and fakes for backend unit tests."""
from __future__ import annotations

import pytest

from tests.helpers import FakeReader, FakeWriter, make_brother_response, make_machine

__all__ = ["FakeReader", "FakeWriter", "make_brother_response", "make_machine"]


@pytest.fixture
def fake_machine():
    return make_machine()


@pytest.fixture
def brother_response():
    return make_brother_response
