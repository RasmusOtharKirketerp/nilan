import argparse
import json
from pathlib import Path

import nilan_comm


class _DummyKeys:
    TEMP = "temp"
    FAN = "fan"
    _PRIVATE = "ignore"
    NUMBER = 42


def test_all_class_values_only_public_strings():
    values = nilan_comm._all_class_values(_DummyKeys)
    assert "temp" in values
    assert "fan" in values
    assert "ignore" not in values
    assert 42 not in values


def test_load_settings_reads_json(tmp_path: Path):
    p = tmp_path / "settings.json"
    expected = {"gateway": {"host": "192.168.0.42"}, "auth": {"email": "x@y.z"}}
    p.write_text(json.dumps(expected), encoding="utf-8")
    assert nilan_comm._load_settings(str(p)) == expected


def test_resolve_nabto_params_prefers_cli_values():
    args = argparse.Namespace(
        email="cli@example.com",
        host="192.168.0.10",
        port=9999,
        device_id="abc123",
    )
    email, device_id, host, port = nilan_comm._resolve_nabto_params(
        args,
        gateway={"host": "192.168.0.42", "port": 5570, "device_id": "from_settings"},
        auth={"email": "settings@example.com"},
    )
    assert email == "cli@example.com"
    assert device_id == "abc123"
    assert host == "192.168.0.10"
    assert port == 9999


def test_resolve_nabto_params_uses_settings_fallbacks():
    args = argparse.Namespace(email=None, host=None, port=None, device_id=None)
    email, device_id, host, port = nilan_comm._resolve_nabto_params(
        args,
        gateway={"host": "192.168.0.42", "port": 5570, "device_id": "from_settings"},
        auth={"email": "settings@example.com"},
    )
    assert email == "settings@example.com"
    assert device_id == "from_settings"
    assert host == "192.168.0.42"
    assert port == 5570


def test_resolve_nabto_params_requires_email():
    args = argparse.Namespace(email=None, host=None, port=None, device_id=None)
    try:
        nilan_comm._resolve_nabto_params(args, gateway={}, auth={})
    except SystemExit as exc:
        assert "Email missing" in str(exc)
        return
    raise AssertionError("Expected SystemExit for missing email")

