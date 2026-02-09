#!/usr/bin/env python3
import argparse
import asyncio
import json
import sys
from pathlib import Path


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _prefer_vendored_genvexnabto(repo_root: Path) -> None:
    candidates = [
        repo_root / "vendor",
        repo_root / "custom_components" / "nilan_nabto" / "vendor",
    ]
    for p in candidates:
        pkg = p / "genvexnabto"
        if pkg.exists():
            sp = str(p)
            if sp not in sys.path:
                sys.path.insert(0, sp)
            return
    raise RuntimeError("Could not find vendored genvexnabto package")


async def _run(email: str, host: str | None, port: int, device_id: str | None, value: int) -> int:
    from genvexnabto import GenvexNabto
    from genvexnabto.models import GenvexNabtoSetpointKey

    n = GenvexNabto(email)
    try:
        discovered = await n.discoverDevices(clear=True)

        if host:
            n.setManualIP(host, port)
            target = f"manual_ip={host}:{port}"
        elif device_id:
            n.setDevice(device_id)
            found = await n.waitForDiscovery()
            if not found:
                print(f"ERROR: device_id not discovered: {device_id}")
                return 2
            target = f"device_id={device_id}"
        elif discovered:
            first = next(iter(discovered.items()))
            n.setDevice(first[0])
            target = f"first_discovered={first[0]}@{first[1][0]}:{first[1][1]}"
        else:
            print("ERROR: no devices discovered and no host/device_id provided")
            return 2

        print(f"Connecting to {target}")
        n.connectToDevice()
        await n.waitForConnection()
        if n._connection_error:  # noqa: SLF001
            print(f"ERROR: connection failed: {n._connection_error}")  # noqa: SLF001
            return 2

        got_data = await n.waitForData()
        if not got_data:
            print("ERROR: connected but no data received")
            return 2

        key = GenvexNabtoSetpointKey.FAN_SPEED
        if not n.providesValue(key):
            print("ERROR: FAN_SPEED is not provided by this model")
            return 2

        before = n.getValue(key)
        min_v = n.getSetpointMinValue(key)
        max_v = n.getSetpointMaxValue(key)
        step = n.getSetpointStep(key)

        print(f"FAN_SPEED before={before} allowed=[{min_v}..{max_v}] step={step}")

        if value < min_v or value > max_v:
            print(f"ERROR: requested value {value} outside allowed range [{min_v}..{max_v}]")
            return 2

        n.setSetpoint(key, value)
        await asyncio.sleep(1.0)

        # Request a fresh setpoint read instead of relying only on cached value.
        n.sendSetpointStateRequest(201)
        await asyncio.sleep(2.0)

        after = n.getValue(key)
        print(f"FAN_SPEED after={after}")

        if after == value:
            print("SUCCESS: fan speed write verified")
            return 0

        print("WARNING: write sent, but readback did not match requested value")
        return 1
    finally:
        try:
            n.stopListening()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Nabto write: set FAN_SPEED")
    parser.add_argument("--settings", default="settings.json", help="Path to settings JSON")
    parser.add_argument("--email", default=None, help="Authorized email")
    parser.add_argument("--host", default=None, help="Gateway host/IP")
    parser.add_argument("--port", type=int, default=None, help="Gateway port")
    parser.add_argument("--device-id", default=None, help="Gateway device id")
    parser.add_argument("--value", type=int, default=4, help="Fan speed target value")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    _prefer_vendored_genvexnabto(repo_root)

    cfg = _load_json((repo_root / args.settings) if not Path(args.settings).is_absolute() else Path(args.settings))
    gateway = cfg.get("gateway", {})
    auth = cfg.get("auth", {})

    email = args.email or auth.get("email")
    host = args.host or gateway.get("host")
    port = args.port if args.port is not None else int(gateway.get("port", 5570))
    device_id = args.device_id or gateway.get("device_id")

    if not email:
        print("ERROR: email missing (use --email or auth.email in settings)")
        return 2

    return asyncio.run(_run(email=email, host=host, port=port, device_id=device_id, value=args.value))


if __name__ == "__main__":
    raise SystemExit(main())
