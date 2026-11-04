# RIZVILAB Solenoid Controller — Handover Documentation

This folder is the maintainer's guide to the BeagleBone Black solenoid controller. It complements the root [`README.md`](../README.md), which includes the current application flow and a function index for `main.py`.

## Read these documents in order

1. [Project overview](01-project-overview.md) — purpose, scope, and system at a glance.
2. [System architecture](02-system-architecture.md) — how the BeagleBone, GUI, GPIO, and relay outputs interact.
3. [Hardware and GPIO](03-hardware-and-gpio.md) — verified software pin mapping and hardware details that must be confirmed from the team's drawings.
4. [Software architecture](04-software-architecture.md) — modules, entry point, initialization, timers, and legacy code boundaries.
5. [GUI and operator workflow](05-gui-and-operator-workflow.md) — every current screen and navigation transition.
6. [Solenoid pulse control](06-solenoid-pulse-control.md) — per-nozzle durations, ON/OFF path, timer, animation, and latch.
7. [Installation and deployment](07-installation-and-deployment.md) — prerequisites, file placement, syntax check, and manual launch.
8. [Autostart and startup](08-autostart-and-startup.md) — LXQt autostart and reboot behavior.
9. [Troubleshooting](09-troubleshooting.md) — common software and deployment symptoms.
10. [Maintenance and change control](10-maintenance-and-change-control.md) — safe workflow for future modifications.
11. [Safety and known limitations](11-safety-and-known-limitations.md) — what the software does not guarantee.
12. [Handover checklist](12-handover-checklist.md) — information to collect before transferring ownership.
13. [Hardware verification record](hardware-verification-template.md) — fill in the actual wiring, relay, valve, and power details from approved drawings and inspection.

## Source of truth and documentation status

These documents describe the repository snapshot used to create this handover package. Before using them on a replacement controller, compare the deployed BeagleBone files with the repository's current `main` branch and record the deployed commit hash.

Some physical details (relay board model, valve coil specification, connector pinout, fuse ratings, power supply details, and hardwired interlocks) are not defined by the Python source. They are intentionally marked **verify from the approved hardware drawings / physical inspection** rather than guessed.

## Important distinction

The software's `OFF` command is a GPIO command. It is not independent feedback that a valve physically closed. The QTimer pulse cutoff is software-based and depends on the Python process and Qt event loop continuing to run. Read [Safety and known limitations](11-safety-and-known-limitations.md) before operating hardware.
