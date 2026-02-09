# Changelog

## 0.1.1 - 2026-02-09

- Added consistent integration versioning.
- Exposed `integration_version` on `sensor.nilan_status` attributes.
- Stabilized sensor creation to include all known datapoint/setpoint keys.

## 0.1.0 - 2026-02-09

- Initial HACS custom integration release (`Nilan CodeWizard`).
- Config flow, coordinator polling, status sensor, datapoint/setpoint sensors.
- Vendored Nabto protocol stack for self-contained runtime.
