from types import SimpleNamespace

from app.utils.machine_endpoints import (
    DEFAULT_TELNET_PORT,
    get_endpoint_summary,
    get_ftp_endpoint,
    get_http_endpoint,
    get_telnet_endpoint,
)


def test_endpoints_fall_back_to_primary_host():
    machine = SimpleNamespace(
        ip_address="192.168.1.135",
        telnet_host=None,
        telnet_port=None,
        ftp_host=None,
        ftp_port=21,
        http_host=None,
        http_port=80,
    )

    assert get_telnet_endpoint(machine) == ("192.168.1.135", DEFAULT_TELNET_PORT)
    assert get_ftp_endpoint(machine) == ("192.168.1.135", 21)
    assert get_http_endpoint(machine) == ("192.168.1.135", 80)


def test_endpoints_use_protocol_specific_overrides():
    machine = SimpleNamespace(
        ip_address="192.168.1.135",
        telnet_host="host.docker.internal",
        telnet_port=11000,
        ftp_host="192.168.1.135",
        ftp_port=2121,
        http_host="machine-http.local",
        http_port=8080,
    )

    assert get_telnet_endpoint(machine) == ("host.docker.internal", 11000)
    assert get_ftp_endpoint(machine) == ("192.168.1.135", 2121)
    assert get_http_endpoint(machine) == ("machine-http.local", 8080)

    assert get_endpoint_summary(machine) == {
        "primary": {"host": "192.168.1.135"},
        "telnet": {"host": "host.docker.internal", "port": 11000},
        "ftp": {"host": "192.168.1.135", "port": 2121},
        "http": {"host": "machine-http.local", "port": 8080},
    }