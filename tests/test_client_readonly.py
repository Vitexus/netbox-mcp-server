"""Tests for NetBoxRestClient read-only write protection.

The client implements the full CRUD interface even though this project
exposes no write tools. `readonly` (default True) rejects write operations
before any HTTP request is made.
"""

from unittest.mock import MagicMock

import pytest

from netbox_mcp_server.netbox_client import NetBoxRestClient


@pytest.fixture
def readonly_client():
    """Create a client with the default (read-only) settings."""
    return NetBoxRestClient(url="https://netbox.example.com", token="test-token")


@pytest.fixture
def writable_client():
    """Create a client with write operations explicitly allowed."""
    return NetBoxRestClient(
        url="https://netbox.example.com", token="test-token", readonly=False
    )


def test_client_defaults_to_readonly():
    """Test that readonly defaults to True when not specified."""
    client = NetBoxRestClient(url="https://netbox.example.com", token="test-token")

    assert client.readonly is True


def test_client_accepts_readonly_false():
    """Test that readonly can be explicitly disabled."""
    client = NetBoxRestClient(
        url="https://netbox.example.com", token="test-token", readonly=False
    )

    assert client.readonly is False


@pytest.mark.parametrize(
    ("method_name", "args"),
    [
        ("create", ("dcim/sites", {"name": "Test"})),
        ("update", ("dcim/sites", 1, {"name": "Test"})),
        ("delete", ("dcim/sites", 1)),
        ("bulk_create", ("dcim/sites", [{"name": "Test"}])),
        ("bulk_update", ("dcim/sites", [{"id": 1, "name": "Test"}])),
        ("bulk_delete", ("dcim/sites", [1, 2])),
    ],
)
def test_write_operations_rejected_when_readonly(readonly_client, method_name, args):
    """Every write method must reject the call before touching the network."""
    readonly_client.session = MagicMock()  # would fail the test if called

    method = getattr(readonly_client, method_name)
    with pytest.raises(PermissionError, match=method_name):
        method(*args)

    readonly_client.session.post.assert_not_called()
    readonly_client.session.patch.assert_not_called()
    readonly_client.session.delete.assert_not_called()


@pytest.mark.parametrize(
    ("method_name", "args", "session_method"),
    [
        ("create", ("dcim/sites", {"name": "Test"}), "post"),
        ("update", ("dcim/sites", 1, {"name": "Test"}), "patch"),
        ("delete", ("dcim/sites", 1), "delete"),
        ("bulk_create", ("dcim/sites", [{"name": "Test"}]), "post"),
        ("bulk_update", ("dcim/sites", [{"id": 1, "name": "Test"}]), "patch"),
        ("bulk_delete", ("dcim/sites", [1, 2]), "request"),
    ],
)
def test_write_operations_allowed_when_not_readonly(
    writable_client, method_name, args, session_method
):
    """When readonly=False, write methods proceed to make the HTTP request."""
    response = MagicMock()
    response.status_code = 204
    response.raise_for_status = MagicMock()
    response.json.return_value = {"id": 1}
    writable_client.session = MagicMock()
    getattr(writable_client.session, session_method).return_value = response

    method = getattr(writable_client, method_name)
    method(*args)

    getattr(writable_client.session, session_method).assert_called_once()
