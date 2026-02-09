#!/usr/bin/env python3
import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


def _all_class_values(cls) -> List[str]:
    vals = []
    for name, value in cls.__dict__.items():
        if name.startswith("_"):
            continue
        if isinstance(value, str):
            vals.append(value)
    return vals


def _load_settings(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _prefer_vendored_genvexnabto() -> dict:
    vendor_path = Path(__file__).resolve().parent / "vendor"
    package_path = vendor_path / "genvexnabto"
    if package_path.exists():
        sp = str(vendor_path)
        if sp not in sys.path:
            sys.path.insert(0, sp)
        return {"used": True, "path": "vendor/genvexnabto"}
    return {"used": False, "reason": "vendored_package_not_found"}


async def run_nabto_probe(email: str, device_id: Optional[str], host: Optional[str], port: int):
    vendor_info = _prefer_vendored_genvexnabto()
    if not vendor_info.get("used"):
        return {"mode": "nabto-probe", "ok": False, "vendor": vendor_info, "error": "Vendored genvexnabto missing"}

    try:
        from genvexnabto import GenvexNabto
        from genvexnabto.models import GenvexNabtoDatapointKey, GenvexNabtoSetpointKey
    except Exception as exc:
        return {
            "mode": "nabto-probe",
            "ok": False,
            "vendor": vendor_info,
            "error": f"Failed importing genvexnabto: {exc}",
        }

    n = GenvexNabto(email)
    report = {
        "mode": "nabto-probe",
        "timestamp_utc": _utc_now_iso(),
        "ok": False,
        "vendor": vendor_info,
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
            report["selected_device"] = {"mode": "first_discovered", "device_id": first[0], "host": first[1][0], "port": first[1][1]}
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


def parse_args():
    parser = argparse.ArgumentParser(description="Nilan CodeWizard communication helper")
    parser.add_argument("--settings", default="settings.json", help="Path to settings JSON file")
    sub = parser.add_subparsers(dest="mode")

    p_nabto = sub.add_parser("nabto", help="Probe using community genvexnabto protocol")
    p_nabto.add_argument("--email", help="Authorized email configured in Nilan app")
    p_nabto.add_argument("--device-id", help="Device id (often contains remote.lscontrol.dk)")
    p_nabto.add_argument("--host", help="Manual device IP")
    p_nabto.add_argument("--port", type=int, help="Manual device port")

    return parser.parse_args()


def _resolve_nabto_params(args, gateway: dict, auth: dict):
    email = getattr(args, "email", None) or auth.get("email")
    if not email:
        raise SystemExit("Email missing. Provide --email or set auth.email in settings.json")

    host = getattr(args, "host", None) or gateway.get("host")
    port = getattr(args, "port", None)
    port = port if port is not None else int(gateway.get("port", 5570))
    device_id = getattr(args, "device_id", None)
    device_id = device_id if device_id is not None else (gateway.get("device_id") or None)
    return email, device_id, host, port


def main():
    args = parse_args()
    settings = {}
    try:
        settings = _load_settings(args.settings)
    except FileNotFoundError:
        settings = {}

    gateway = settings.get("gateway", {})
    auth = settings.get("auth", {})
    if args.mode == "nabto":
        email, device_id, host, port = _resolve_nabto_params(args, gateway, auth)
        report = asyncio.run(run_nabto_probe(email, device_id, host, port))
        print(json.dumps(report, indent=2))
        return

    # Direct run mode: no subcommand -> use settings.json mode toggles.
    mode_cfg = settings.get("mode", {})
    run_nabto = bool(mode_cfg.get("run_nabto", True))
    combined = {"mode": "direct-run", "settings": args.settings, "nabto": None}
    combined["timestamp_utc"] = _utc_now_iso()

    if run_nabto:
        email, device_id, host, port = _resolve_nabto_params(args, gateway, auth)
        combined["nabto"] = asyncio.run(run_nabto_probe(email, device_id, host, port))

    print(json.dumps(combined, indent=2))
    return


if __name__ == "__main__":
    main()
