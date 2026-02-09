# Nilan Communication Tool

This project is self-contained and uses only code from this repository at runtime.

## Runtime dependencies

None. No external Python packages are required for runtime.

## Run

Direct run (uses `settings.json`):

```bash
python3 nilan_comm.py
```

Explicit Nabto mode:

```bash
python3 nilan_comm.py nabto
```

Optional overrides:

```bash
python3 nilan_comm.py nabto --host 192.168.0.42 --port 5570 --email you@example.com
```

## Output

The script returns JSON with connection status, datapoints, and setpoints.

## Vendored protocol stack

Nabto communication is vendored under `vendor/genvexnabto` and loaded from there.

## Tests

Install test dependencies:

```bash
python3 -m pip install --user -r requirements-dev.txt
```

Run unit tests:

```bash
python3 -m pytest --capture=no -q tests/test_unit.py
```

Run live tests (requires reachable gateway and valid `settings.json`):

```bash
RUN_LIVE_TESTS=1 python3 -m pytest --capture=no -q -m live tests/test_live.py
```
