# Nilan CodeWizard Home Assistant Integration

HACS custom integration for reading Nilan data via Nabto, branded as Nilan CodeWizard.

## Developer

- CodeWizard: https://github.com/RasmusOtharKirketerp

## Compatibility

Tested with:
- Home Assistant OS: `17.0`
- Home Assistant Core: `2026.2.1`
- Home Assistant Supervisor: `2026.01.1`
- Home Assistant Frontend: `20260128.6`

Minimum supported Home Assistant Core version is set to `2026.2.1` in integration metadata.

## Installation (Home Assistant OS via HACS)

1. In Home Assistant, install HACS first if it is not already installed.
2. Go to `HACS -> Integrations -> 3 dots -> Custom repositories`.
3. Add your repository URL and set category to `Integration`.
4. Install `Nilan by CodeWizard` from HACS.
5. Restart Home Assistant.
6. Go to `Settings -> Devices & Services -> Add Integration`.
7. Search for `Nilan CodeWizard` and complete setup.

## Configuration

You will be asked for:
- Authorized email
- Gateway host/IP
- Gateway port (default `5570`)
- Optional device ID
- Scan interval in seconds

## Entities

The integration creates:
- `sensor.nilan_status`
- sensors for available datapoints
- sensors for available setpoints (`min/max/step` as attributes)

`timestamp_utc` is exposed on the status sensor attributes.

## Repository layout

- `custom_components/nilan_nabto`: Home Assistant integration
- `custom_components/nilan_nabto/vendor/genvexnabto`: vendored Nabto protocol stack

## Versioning

- Integration version is tracked in:
  - `custom_components/nilan_nabto/manifest.json` (`version`)
  - `custom_components/nilan_nabto/const.py` (`INTEGRATION_VERSION`)
- Keep these in sync for each release.
- Release notes are tracked in `CHANGELOG.md`.

## HACS Update Notifications

HACS is configured to track releases (not every commit) via `hacs.json`:
- `hide_default_branch: true`

When you publish a new version:
1. Bump version in:
   - `custom_components/nilan_nabto/manifest.json`
   - `custom_components/nilan_nabto/const.py`
2. Update `CHANGELOG.md`.
3. Create and push a matching git tag: `vX.Y.Z`.
4. Publish a GitHub Release from that tag.

After this, HACS will show an available update to users on older versions.
