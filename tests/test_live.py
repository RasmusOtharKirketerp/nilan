import asyncio
import os

import pytest

import nilan_comm


RUN_LIVE = os.getenv("RUN_LIVE_TESTS") == "1"


@pytest.mark.live
@pytest.mark.skipif(not RUN_LIVE, reason="Set RUN_LIVE_TESTS=1 to run live tests.")
def test_live_nabto_probe_returns_report():
    settings = nilan_comm._load_settings("settings.json")
    gateway = settings.get("gateway", {})
    auth = settings.get("auth", {})

    email = auth.get("email")
    host = gateway.get("host")
    port = int(gateway.get("port", 5570))
    device_id = gateway.get("device_id") or None

    assert email, "auth.email is required in settings.json"
    assert host, "gateway.host is required in settings.json"

    report = asyncio.run(nilan_comm.run_nabto_probe(email, device_id, host, port))

    assert report["mode"] == "nabto-probe"
    assert "ok" in report
    assert "connection_error" in report
    assert isinstance(report.get("datapoints", {}), dict)
    assert isinstance(report.get("setpoints", {}), dict)

