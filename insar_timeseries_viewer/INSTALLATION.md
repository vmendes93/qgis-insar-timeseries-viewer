# Installation

## Install from a release ZIP

1. Download the release ZIP from the GitHub Releases page.
2. Open QGIS.
3. Go to **Plugins → Manage and Install Plugins**.
4. Open **Install from ZIP**.
5. Select the downloaded archive and install it.
6. Enable **InSAR Time Series Viewer** if required.

The ZIP must contain exactly one top-level directory named `insar_timeseries_viewer`.

## Development installation on Linux

Clone the repository and create a symbolic link from the plugin source directory to the active QGIS profile:

```bash
ln -s /path/to/qgis-insar-timeseries-viewer/insar_timeseries_viewer \
  ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/insar_timeseries_viewer
```

Restart QGIS or reload the plugin with Plugin Reloader.

## Development installation on Windows

Create a directory junction or copy the `insar_timeseries_viewer` directory into:

```text
%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\
```

For active development, a directory junction avoids repeated copying:

```powershell
cmd /c mklink /J `
  "$env:APPDATA\QGIS\QGIS3\profiles\default\python\plugins\insar_timeseries_viewer" `
  "$PWD\insar_timeseries_viewer"
```

## Verify the installation

Open **Vector → Time Series Viewer**. If the panel cannot be created, check **View → Panels → Log Messages** and consult `TROUBLESHOOTING.md`.
