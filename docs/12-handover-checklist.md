# 12. Project handover checklist

Use this checklist during transfer to the next maintainer. Do not place passwords or private keys in this document or GitHub.

## Repository and software

- [ ] Incoming maintainer has access to the GitHub repository.
- [ ] The deployed BeagleBone commit hash is recorded.
- [ ] The working branch and release/tag process are understood.
- [ ] `main.py`, `constants.py`, `system_constants.py`, `directory_constants.py`, and `start.sh` are present and understood.
- [ ] Python 2, PyQt4, Adafruit_BBIO, Adafruit_GPIO, and serial dependencies are recorded from the actual device.
- [ ] The current image path configuration has been verified on the BeagleBone.
- [ ] The LXQt autostart file and desktop user are documented.
- [ ] The previous controller's autostart entry is disabled.
- [ ] Backup and rollback steps have been tested.

## Hardware

- [ ] Approved electrical schematic is linked or stored in the approved repository.
- [ ] Relay board manufacturer, model, and revision recorded.
- [ ] GPIO/header pin to relay channel mapping verified.
- [ ] Solenoid valve manufacturer/model and electrical ratings recorded.
- [ ] Power supply and protection ratings recorded.
- [ ] Connector part numbers and pinouts recorded.
- [ ] Harness/wiring drawing revision recorded.
- [ ] Grounding/isolation and suppression strategy documented.
- [ ] Emergency stop and hardwired interlocks tested and documented.
- [ ] Safe behavior during power loss, reboot, process crash, and GPIO reinitialization verified.

## Operator procedure

- [ ] Startup image sequence reviewed against approved SOP.
- [ ] Shutdown image sequence reviewed against approved SOP.
- [ ] Displayed regulator settings verified by the responsible owner.
- [ ] Independent pulse duration behavior tested for each nozzle.
- [ ] Actual pulse cutoff verified with a safe test setup.
- [ ] Shutdown latch and standby/wake behavior tested.
- [ ] Physical valve closure and pressure isolation method documented.

## Incoming maintainer training

- [ ] Can explain application startup and GPIO initialization.
- [ ] Can locate the per-nozzle duration code.
- [ ] Can explain the cutoff timer and why it is not a hardware safety cutoff.
- [ ] Can explain the shutdown latch and how it is reset.
- [ ] Can restart the GUI without starting duplicate processes.
- [ ] Can diagnose missing image paths and GPIO setup failures.
- [ ] Knows which functions and screens are legacy and must not be enabled casually.
- [ ] Knows how to create a backup, commit a change, and roll back a deployment.

## Handover record

| Field | Record |
|---|---|
| Outgoing maintainer |  |
| Incoming maintainer |  |
| Handover date |  |
| GitHub repository URL |  |
| Deployed commit hash |  |
| BeagleBone hostname / asset tag |  |
| Debian image/version |  |
| Python version |  |
| Display model/resolution |  |
| Approved schematic revision |  |
| Approved operating procedure revision |  |
| Known open issues |  |
