# Nilan Communication Tool

This project now supports two paths:

- `local`: checks if your gateway exposes anything directly on LAN (ports/HTTP/Modbus TCP)
- `nabto`: uses the community `genvexnabto` protocol (same family used by HA integrations), vendored in this repo under `vendor/genvexnabto`

## Setup

```bash
python3 -m pip install --user -r requirements.txt
python3 -m pip check
```

Copy `settings.example.json` to `settings.json` and fill in your gateway IP and app email.

## 1) Local probe (official LAN exposure check)

```bash
python3 nilan_comm.py local <gateway-ip> --insecure
```

## 2) Community Nabto probe (practical read path)

```bash
python3 nilan_comm.py nabto --email you@example.com
```

Optional selectors:

```bash
python3 nilan_comm.py nabto --email you@example.com --device-id <device-id>
python3 nilan_comm.py nabto --email you@example.com --host 192.168.1.50 --port 5570
```

## Output

Both modes return JSON so you can pipe into files/tools.

## Note about `genvexnabto`

The project uses a vendored `genvexnabto` copy to avoid upstream packaging issues and keep behavior reproducible.
