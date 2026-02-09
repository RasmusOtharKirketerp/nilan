#!/usr/bin/env python3
import argparse
import asyncio
import json
import socket
import ssl
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DEFAULT_PORTS = [80, 443, 502, 1883, 8883, 8080, 8443]


@dataclass
class PortProbe:
    port: int
    open: bool
    banner: Optional[str] = None
    error: Optional[str] = None


@dataclass
class HttpProbe:
    url: str
    ok: bool
    status: Optional[int] = None
    server: Optional[str] = None
    snippet: Optional[str] = None
    error: Optional[str] = None


def tcp_probe(host: str, port: int, timeout: float) -> PortProbe:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        banner = None
        try:
            s.sendall(b"\n")
            data = s.recv(96)
            if data:
                banner = data.decode("utf-8", errors="replace").strip()
        except Exception:
            pass
        return PortProbe(port=port, open=True, banner=banner)
    except Exception as exc:
        return PortProbe(port=port, open=False, error=str(exc))
    finally:
        s.close()


def http_probe(url: str, timeout: float, insecure: bool) -> HttpProbe:
    req = Request(url, method="GET", headers={"User-Agent": "nilan-comm/0.2"})
    ctx = None
    if urlparse(url).scheme == "https" and insecure:
        ctx = ssl._create_unverified_context()
    try:
        with urlopen(req, timeout=timeout, context=ctx) as resp:
            body = resp.read(200).decode("utf-8", errors="replace")
            return HttpProbe(
                url=url,
                ok=True,
                status=getattr(resp, "status", None),
                server=resp.headers.get("Server"),
                snippet=body.strip().replace("\n", " "),
            )
    except Exception as exc:
        return HttpProbe(url=url, ok=False, error=str(exc))


def modbus_read(host: str, unit: int, address: int, count: int, timeout: float):
    try:
        from pymodbus.client import ModbusTcpClient
    except Exception as exc:
        return {"ok": False, "error": f"pymodbus not installed ({exc})"}

    client = ModbusTcpClient(host=host, port=502, timeout=timeout)
    if not client.connect():
        return {"ok": False, "error": "could not connect to port 502"}

    try:
        result = client.read_holding_registers(address=address, count=count, device_id=unit)
        if result.isError():
            return {"ok": False, "error": str(result)}
        return {"ok": True, "registers": result.registers}
    except TypeError:
        result = client.read_holding_registers(address, count, unit=unit)
        if result.isError():
            return {"ok": False, "error": str(result)}
        return {"ok": True, "registers": result.registers}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        client.close()


def run_local_probe(host: str, ports: List[int], timeout: float, unit: int, register: int, count: int, insecure: bool):
    return {
        "mode": "local-probe",
        "host": host,
        "port_probes": [asdict(tcp_probe(host, p, timeout)) for p in ports],
        "http_probes": [
            asdict(http_probe(f"http://{host}", timeout, insecure)),
            asdict(http_probe(f"https://{host}", timeout, insecure)),
        ],
        "modbus_probe": modbus_read(host, unit, register, count, timeout),
    }


def _hotfix_genvexnabto_syntax() -> Dict[str, str]:
    """Patch known genvexnabto issues in published package on Python 3.10."""
    try:
        import site

        patched_any = False
        notes = []
        for base in site.getsitepackages() + [site.getusersitepackages()]:
            pkg_dir = Path(base) / "genvexnabto"
            if not pkg_dir.exists():
                continue

            p = pkg_dir / "genvexnabto.py"
            text = p.read_text(encoding="utf-8") if p.exists() else ""
            broken = "_LOGGER.debug(f'{self._client_id} Got payload: {''.join(r'\\x'+hex(letter)[2:] for letter in payload)}')"
            if broken in text:
                fixed = (
                    "hex_payload = ''.join('\\\\x' + format(letter, '02x') for letter in payload)\n"
                    "                _LOGGER.debug(f'{self._client_id} Got payload: {hex_payload}')"
                )
                text = text.replace(broken, fixed)
                p.write_text(text, encoding="utf-8")
                patched_any = True
                notes.append(f"patched syntax in {p}")

            base_model = pkg_dir / "models" / "basemodel.py"
            if base_model.exists():
                bm_text = base_model.read_text(encoding="utf-8")
                old_import = "from typing import Dict, List, TypedDict, NotRequired"
                new_import = (
                    "from typing import Dict, List, TypedDict\n"
                    "try:\n"
                    "    from typing import NotRequired\n"
                    "except ImportError:\n"
                    "    from typing_extensions import NotRequired"
                )
                if old_import in bm_text:
                    bm_text = bm_text.replace(old_import, new_import)
                    base_model.write_text(bm_text, encoding="utf-8")
                    patched_any = True
                    notes.append(f"patched NotRequired import in {base_model}")

            adapter_file = pkg_dir / "genvexnabto_modeladapter.py"
            if adapter_file.exists():
                adapter_text = adapter_file.read_text(encoding="utf-8")
                fix1_old = "responceLength = int.from_bytes(responcePayload[0:2])"
                fix1_new = "responceLength = int.from_bytes(responcePayload[0:2], 'big')"
                fix2_old = "responceLength = int.from_bytes(responcePayload[1:3])"
                fix2_new = "responceLength = int.from_bytes(responcePayload[1:3], 'big')"
                changed = False
                if fix1_old in adapter_text:
                    adapter_text = adapter_text.replace(fix1_old, fix1_new)
                    changed = True
                if fix2_old in adapter_text:
                    adapter_text = adapter_text.replace(fix2_old, fix2_new)
                    changed = True
                if changed:
                    adapter_file.write_text(adapter_text, encoding="utf-8")
                    patched_any = True
                    notes.append(f"patched from_bytes byteorder in {adapter_file}")

            if patched_any:
                return {"patched": "true", "path": str(pkg_dir), "reason": "; ".join(notes)}
            return {"patched": "false", "path": str(pkg_dir), "reason": "not_needed_or_unknown_version"}
    except Exception as exc:
        return {"patched": "false", "reason": str(exc)}

    return {"patched": "false", "reason": "genvexnabto_not_found"}


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


def _prefer_vendored_genvexnabto() -> Dict[str, str]:
    vendor_path = Path(__file__).resolve().parent / "vendor"
    package_path = vendor_path / "genvexnabto"
    if package_path.exists():
        sp = str(vendor_path)
        if sp not in sys.path:
            sys.path.insert(0, sp)
        return {"used": "true", "path": str(package_path)}
    return {"used": "false", "reason": "vendored_package_not_found"}


async def run_nabto_probe(email: str, device_id: Optional[str], host: Optional[str], port: int):
    vendor_info = _prefer_vendored_genvexnabto()
    hotfix = _hotfix_genvexnabto_syntax()

    try:
        from genvexnabto import GenvexNabto
        from genvexnabto.models import GenvexNabtoDatapointKey, GenvexNabtoSetpointKey
    except Exception as exc:
        return {
            "mode": "nabto-probe",
            "ok": False,
            "vendor": vendor_info,
            "hotfix": hotfix,
            "error": f"Failed importing genvexnabto: {exc}",
        }

    n = GenvexNabto(email)
    report = {
        "mode": "nabto-probe",
        "ok": False,
        "vendor": vendor_info,
        "hotfix": hotfix,
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
    parser = argparse.ArgumentParser(description="Nilan communication helper")
    parser.add_argument("--settings", default="settings.json", help="Path to settings JSON file")
    sub = parser.add_subparsers(dest="mode", required=True)

    p_local = sub.add_parser("local", help="Probe local ports/http/modbus")
    p_local.add_argument("host", nargs="?", help="Gateway/device IP or hostname")
    p_local.add_argument("--ports", help="Comma-separated TCP ports")
    p_local.add_argument("--timeout", type=float, help="Timeout per probe in seconds")
    p_local.add_argument("--unit", type=int, help="Modbus unit id")
    p_local.add_argument("--register", type=int, help="Holding register address")
    p_local.add_argument("--count", type=int, help="Number of registers to read")
    p_local.add_argument("--insecure", action="store_true", help="Skip TLS cert validation for HTTPS probe")

    p_nabto = sub.add_parser("nabto", help="Probe using community genvexnabto protocol")
    p_nabto.add_argument("--email", help="Authorized email configured in Nilan app")
    p_nabto.add_argument("--device-id", help="Device id (often contains remote.lscontrol.dk)")
    p_nabto.add_argument("--host", help="Manual device IP")
    p_nabto.add_argument("--port", type=int, help="Manual device port")

    return parser.parse_args()


def main():
    args = parse_args()
    settings = {}
    try:
        settings = _load_settings(args.settings)
    except FileNotFoundError:
        settings = {}

    gateway = settings.get("gateway", {})
    auth = settings.get("auth", {})
    probes = settings.get("probes", {})

    if args.mode == "local":
        host = args.host or gateway.get("host")
        if not host:
            raise SystemExit("Host missing. Provide it as CLI arg or in settings.json under gateway.host")

        ports_raw = args.ports or probes.get("ports") or DEFAULT_PORTS
        if isinstance(ports_raw, str):
            ports = [int(p.strip()) for p in ports_raw.split(",") if p.strip()]
        else:
            ports = [int(p) for p in ports_raw]

        timeout = args.timeout if args.timeout is not None else float(probes.get("timeout_seconds", 2.0))
        unit = args.unit if args.unit is not None else int(gateway.get("modbus_unit", 1))
        register = args.register if args.register is not None else int(gateway.get("modbus_register", 0))
        count = args.count if args.count is not None else int(gateway.get("modbus_count", 10))
        insecure = args.insecure or bool(probes.get("insecure_https", False))

        report = run_local_probe(host, ports, timeout, unit, register, count, insecure)
        print(json.dumps(report, indent=2))
        return

    if args.mode == "nabto":
        email = args.email or auth.get("email")
        if not email:
            raise SystemExit("Email missing. Provide --email or set auth.email in settings.json")

        host = args.host or gateway.get("host")
        port = args.port if args.port is not None else int(gateway.get("port", 5570))
        device_id = args.device_id if args.device_id is not None else (gateway.get("device_id") or None)

        report = asyncio.run(run_nabto_probe(email, device_id, host, port))
        print(json.dumps(report, indent=2))
        return


if __name__ == "__main__":
    main()
