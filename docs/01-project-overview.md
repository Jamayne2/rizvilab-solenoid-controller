# 1. Project overview

## Purpose

`rizvilab-solenoid-controller` is a touchscreen application for operating three solenoid relay outputs from a BeagleBone Black. The application is written in Python 2 using PyQt4 and `Adafruit_BBIO.GPIO`.

The current operator workflow provides:

- A Welcome screen.
- A guided startup sequence with five illustrated pages.
- A control screen with one GO button and one pulse-time button for each of three solenoids.
- An independent 1–5 second pulse-duration setting for each solenoid.
- A timed dispensing screen with a progress animation.
- A shutdown sequence with a title page and five illustrated pages.
- A dark standby screen after the final shutdown instruction. Tapping it returns to Welcome without unlocking the solenoids.

## Intended platform

| Item | Current project configuration |
|---|---|
| Target computer | BeagleBone Black |
| Operating environment | Debian-based graphical desktop; LXQt autostart is used in the current deployment |
| Runtime | Python 2 (`/usr/bin/python2`) |
| GUI toolkit | PyQt4 |
| GPIO library | Adafruit_BBIO.GPIO |
| Main entry point | `main.py` → `main()` |
| Launcher | `start.sh` |
| Active outputs | Three solenoid relay outputs |
| UI reference geometry | 480 × 272; scaled to detected display resolution |

The exact Debian image/version, Python patch version, PyQt4 package version, display model, and installed library versions must be recorded from the deployed BeagleBone. They are not pinned in a dependency lock file.

## Scope of the current release

The active operator path is the three-solenoid workflow described above. The codebase is an evolved legacy controller: older screens and routines for pressure, temperature, heaters, Alicat communication, and data logging remain in `main.py` and supporting modules. Their presence does not mean they are active or validated for the current solenoid-only operation.

Do not reactivate legacy screens, timers, heater outputs, analog reads, pressure control, or power-down routines without a separate code review and hardware validation.

## Main files

| File / folder | Role |
|---|---|
| `main.py` | GUI, application state, screen navigation, pulse logic, GPIO commands, and retained legacy functions |
| `constants.py` | GPIO mapping, image path constant, styles, pressure codes, and legacy constants |
| `system_constants.py` | Legacy operating ranges and setpoint defaults |
| `directory_constants.py` | Legacy absolute paths for setpoint and data-log files |
| `start.sh` | Exports Linux GPIO sysfs numbers, sets `DISPLAY`, and launches Python 2 |
| `window-background-images/` | Welcome, startup, shutdown, and background images |
| `preview_original.py` | Historical read-only UI preview utility; not the live launcher |
| `bus.py` | Standalone I2C pressure-read experiment; not imported by `main.py` and has an import-time read side effect |
| `REFACTOR_VERIFICATION.json` | Static comparison record for the method-order/documentation refactor |

## Project ownership

The incoming maintainer should own the GitHub repository, the BeagleBone deployment, the approved wiring/hardware drawings, and the operational procedure. Do not put passwords, SSH private keys, Wi-Fi credentials, or other secrets in GitHub. Transfer access using the organization's approved account-management process.
