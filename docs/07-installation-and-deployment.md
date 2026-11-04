# 7. Installation and deployment

## Before installing

Collect and verify:

- BeagleBone Black model and board revision.
- Debian image/version and desktop environment.
- Display model, resolution, and touch interface.
- Python 2 interpreter and PyQt4 availability.
- Adafruit_BBIO and Adafruit_GPIO availability.
- Relay board and solenoid wiring from the approved drawing.
- Correct repository commit hash to deploy.
- Correct image directory paths (see below).

The current application is Python 2 / PyQt4. These are legacy dependencies and may not be available in current Debian releases. Do not assume a standard modern Python 3 environment can run the application.

## Required imports to verify

The current `main.py` imports modules including:

- `PyQt4.QtGui`, `PyQt4.QtCore`
- `Adafruit_BBIO.GPIO`
- `Adafruit_BBIO.ADC`
- `Adafruit_GPIO.I2C`
- `serial`

Some imports are retained for legacy functionality even if the current operator path does not actively use those devices. Verify the imports in the exact interpreter used by `start.sh`:

```bash
/usr/bin/python2 -c 'from PyQt4 import QtGui, QtCore; import Adafruit_BBIO.GPIO; import Adafruit_BBIO.ADC; import Adafruit_GPIO.I2C; import serial; print("imports OK")'
```

This checks imports only; it does not test GPIO hardware.

## Suggested deployment directory

The current working deployment used during development was:

```text
/home/debian/pratyush-controller-working/
```

The launcher uses `cd "$(dirname "$0")"`, so it runs relative to its own location. Keep `main.py`, the Python modules, and `window-background-images/` together in the deployed project directory.

## Important image-path verification

The source snapshot contains multiple path styles:

- Startup and shutdown illustration lists use a path relative to `main.py` under `window-background-images/`.
- `constants.py` defines `IMAGES_FOLDER` as `/home/debian/pratyush-controller/window-background-images`.
- `main.py` contains an initial splash-image path `/home/debian/controller/window-background-images/splash-screen-corrected.png` before `initUI()` reloads the splash using `IMAGES_FOLDER`.

These paths are not all the same as `/home/debian/pratyush-controller-working/`. The existing deployment may have additional copies or links. Before a fresh install, inspect the actual BeagleBone filesystem and confirm which path is used. Do not silently change paths as part of a code-only documentation update; make any path correction as a separate tested change.

Useful checks on the BeagleBone:

```bash
ls -l /home/debian/pratyush-controller-working/window-background-images/splash-screen-corrected.png
ls -l /home/debian/pratyush-controller/window-background-images/splash-screen-corrected.png
ls -l /home/debian/controller/window-background-images/splash-screen-corrected.png
```

Only the path(s) actually used by the deployed application need to exist, but all image filenames referenced by the application must resolve.

## Manual launch

From a terminal in the BeagleBone graphical desktop session:

```bash
cd /home/debian/pratyush-controller-working
bash start.sh
```

`start.sh` changes to its own directory, exports Linux GPIO numbers 51, 117, and 60 if needed, waits for their sysfs `direction` files to become writable, sets `DISPLAY` to the existing value or `:0.0`, and executes `/usr/bin/python2 main.py`.

The script's active body does not set GPIO direction; Python's `setup_gpio()` configures the pins using Adafruit_BBIO. The script requires the appropriate permissions to export GPIOs and run the application.

## Syntax and import checks

```bash
cd /home/debian/pratyush-controller-working
/usr/bin/python2 -m py_compile main.py
```

A successful compile check does not prove that Qt can open the display, images load, GPIO setup succeeds, or the relay hardware is wired correctly.

## Updating from a Mac

From the local project directory on the Mac:

```bash
scp main.py debian@<BEAGLEBONE_IP>:/home/debian/pratyush-controller-working/
```

For a full project deployment, use Git on the BeagleBone or transfer the complete tested release, not just `main.py`. Keep the supporting modules and image assets in sync.

Before replacing the working version, back it up on the BeagleBone:

```bash
cp main.py main.py.backup.$(date +%Y%m%d-%H%M%S)
```

Stop the existing GUI safely before launching a second copy. See [Maintenance](10-maintenance-and-change-control.md).
