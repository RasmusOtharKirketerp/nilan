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

## Local Testing Before Publish

Use local install to test changes without HACS/GitHub download limits.

Linux/HA container host:

```bash
./scripts/sync_local.sh /path/to/ha_config
```

Windows:

```bat
scripts\\sync_local.bat C:\\path\\to\\ha_config
```

Or use the root publisher shortcut:

```bat
publish_to_ha.bat C:\\path\\to\\ha_config
```

On Windows, if `local_settings.json` has `ha.config_path`, you can run without arguments:

```bat
scripts\\sync_local.bat
publish_to_ha.bat
```

### SSH Deploy To Raspberry Pi / HA Host

If your Home Assistant runs on a Pi and is reachable by SSH, use:

Linux/WSL:

```bash
./scripts/deploy_ha_ssh.sh
```

Windows:

```bat
scripts\\deploy_ha_ssh.bat
```

These commands read SSH target details from `local_settings.json`:
- `ha.host`
- `ha.port`
- `ha.username`
- `ha.auth.method` (`password` or `key`)
- `ha.auth.password` (when using password auth)
- `ha.auth.private_key_path` (optional)
- `ha.config_path` (usually `/config`)
- `deploy.integration_src` (default `custom_components/nilan_nabto`)
- `deploy.integration_name` (default `nilan_nabto`)
- `deploy.restart_after_deploy` (`true` to send restart command automatically)

Password auth notes:
- `deploy_ha_ssh.sh` uses `sshpass` when `ha.auth.method=password`.
- `deploy_ha_ssh.bat` uses PuTTY tools (`plink` + `pscp`) when `ha.auth.method=password`.

After syncing:
1. Restart Home Assistant.
2. Go to `Settings -> Devices & Services`.
3. Reload `Nilan CodeWizard` integration.

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
- number entities for writable setpoints (e.g. fan speed), where supported by the device model

`timestamp_utc` is exposed on the status sensor attributes.

## Repository layout

- `custom_components/nilan_nabto`: Home Assistant integration
- `custom_components/nilan_nabto/vendor/genvexnabto`: vendored Nabto protocol stack

## Versioning

- Integration version is tracked only in:
  - `custom_components/nilan_nabto/manifest.json` (`version`)
- Release notes are tracked in `CHANGELOG.md`.

## HACS Update Notifications

HACS is configured to track releases (not every commit) via `hacs.json`:
- `hide_default_branch: true`

When you publish a new version:
1. Update `custom_components/nilan_nabto/manifest.json` `version`.
2. Update `CHANGELOG.md`.
3. Push to GitHub (and publish a release if you want release notes in HACS).

After this, HACS will show an available update to users on older versions.
