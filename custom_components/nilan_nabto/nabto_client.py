from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from .vendor.genvexnabto import GenvexNabto
from .vendor.genvexnabto.models import GenvexNabtoDatapointKey, GenvexNabtoSetpointKey


def _all_class_values(cls) -> list[str]:
    values: list[str] = []
    for name, value in cls.__dict__.items():
        if name.startswith("_"):
            continue
        if isinstance(value, str):
            values.append(value)
    return values


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def run_nabto_probe(email: str, device_id: str | None, host: str | None, port: int) -> dict[str, Any]:
    n = GenvexNabto(email)
    report: dict[str, Any] = {
        "mode": "nabto-probe",
        "timestamp_utc": _utc_now_iso(),
        "ok": False,
        "discovered_devices": {},
        "selected_device": None,
        "connection_error": None,
        "datapoints": {},
        "setpoints": {},
    }

    try:
        discovered = await n.discoverDevices(clear=True)
        report["discovered_devices"] = {k: [v[0], v[1]] for k, v in discovered.items()}

        if host:
            n.setManualIP(host, port)
            report["selected_device"] = {"mode": "manual_ip", "host": host, "port": port}
        elif device_id:
            n.setDevice(device_id)
            found = await n.waitForDiscovery()
            report["selected_device"] = {"mode": "device_id", "device_id": device_id, "found": found}
            if not found:
                report["connection_error"] = "device_not_discovered"
                return report
        elif discovered:
            first = next(iter(discovered.items()))
            n.setDevice(first[0])
            report["selected_device"] = {
                "mode": "first_discovered",
                "device_id": first[0],
                "host": first[1][0],
                "port": first[1][1],
            }
        else:
            report["connection_error"] = "no_devices_discovered"
            return report

        n.connectToDevice()
        await n.waitForConnection()
        if n._connection_error:  # noqa: SLF001
            report["connection_error"] = n._connection_error  # noqa: SLF001
            return report

        got_data = await n.waitForData()
        if not got_data:
            report["connection_error"] = "connected_but_no_data"
            return report

        for key in _all_class_values(GenvexNabtoDatapointKey):
            if n.providesValue(key) and n.hasValue(key):
                report["datapoints"][key] = n.getValue(key)

        for key in _all_class_values(GenvexNabtoSetpointKey):
            if n.providesValue(key) and n.hasValue(key):
                report["setpoints"][key] = {
                    "value": n.getValue(key),
                    "min": n.getSetpointMinValue(key),
                    "max": n.getSetpointMaxValue(key),
                    "step": n.getSetpointStep(key),
                }

        report["ok"] = True
        return report
    finally:
        try:
            n.stopListening()
        except Exception:
            pass


async def run_nabto_setpoint(
    email: str,
    device_id: str | None,
    host: str | None,
    port: int,
    key: str,
    value: float,
) -> dict[str, Any]:
    n = GenvexNabto(email)
    report: dict[str, Any] = {
        "mode": "nabto-setpoint",
        "timestamp_utc": _utc_now_iso(),
        "ok": False,
        "selected_device": None,
        "connection_error": None,
        "key": key,
        "requested_value": value,
        "readback_value": None,
    }

    try:
        discovered = await n.discoverDevices(clear=True)

        if host:
            n.setManualIP(host, port)
            report["selected_device"] = {"mode": "manual_ip", "host": host, "port": port}
        elif device_id:
            n.setDevice(device_id)
            found = await n.waitForDiscovery()
            report["selected_device"] = {"mode": "device_id", "device_id": device_id, "found": found}
            if not found:
                report["connection_error"] = "device_not_discovered"
                return report
        elif discovered:
            first = next(iter(discovered.items()))
            n.setDevice(first[0])
            report["selected_device"] = {
                "mode": "first_discovered",
                "device_id": first[0],
                "host": first[1][0],
                "port": first[1][1],
            }
        else:
            report["connection_error"] = "no_devices_discovered"
            return report

        n.connectToDevice()
        await n.waitForConnection()
        if n._connection_error:  # noqa: SLF001
            report["connection_error"] = n._connection_error  # noqa: SLF001
            return report

        got_data = await n.waitForData()
        if not got_data:
            report["connection_error"] = "connected_but_no_data"
            return report

        if not n.providesValue(key):
            report["connection_error"] = "setpoint_not_supported"
            return report

        min_value = n.getSetpointMinValue(key)
        max_value = n.getSetpointMaxValue(key)
        if value < min_value or value > max_value:
            report["connection_error"] = "setpoint_out_of_range"
            report["min"] = min_value
            report["max"] = max_value
            return report

        n.setSetpoint(key, value)
        await asyncio.sleep(1.0)
        n.sendSetpointStateRequest(201)
        await asyncio.sleep(1.0)
        report["readback_value"] = n.getValue(key)
        report["ok"] = report["readback_value"] == value
        if not report["ok"]:
            report["connection_error"] = "setpoint_readback_mismatch"
        return report
    finally:
        try:
            n.stopListening()
        except Exception:
            pass
