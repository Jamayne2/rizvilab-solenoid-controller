# Hardware verification record — template

Complete this record from the approved schematic, bill of materials, physical inspection, and controlled bench tests. Do not infer missing values from Python constants.

## Controller and relay hardware

| Field | Verified value | Evidence / drawing reference |
|---|---|---|
| BeagleBone Black board revision |  |  |
| Grove Cape / relay board model and revision |  |  |
| Relay channel 1 part / channel |  |  |
| Relay channel 2 part / channel |  |  |
| Relay channel 3 part / channel |  |  |
| Relay input active polarity |  |  |
| Relay contact form (COM/NO/NC) |  |  |
| Isolation details |  |  |

## GPIO mapping

| Solenoid | BeagleBone header pin | Linux GPIO | Relay channel | Verified by / date |
|---|---|---:|---|---|
| 1 | P9_16 (software mapping) | 51 (launcher mapping) |  |  |
| 2 | P9_25 (software mapping) | 117 (launcher mapping) |  |  |
| 3 | P9_12 (software mapping) | 60 (launcher mapping) |  |  |

## Valve and power information

| Field | Solenoid 1 | Solenoid 2 | Solenoid 3 |
|---|---|---|---|
| Manufacturer / model |  |  |  |
| Rated coil voltage |  |  |  |
| Rated / inrush current |  |  |  |
| AC or DC |  |  |  |
| Polarity requirement |  |  |  |
| Connector and pinout |  |  |  |
| Cable gauge / length |  |  |  |
| Fuse / protection |  |  |  |

| Shared power detail | Verified value | Evidence |
|---|---|---|
| Valve power supply |  |  |
| Supply current rating |  |  |
| Return / grounding |  |  |
| Flyback / transient suppression |  |  |
| Emergency stop / interlock |  |  |
| Physical isolation point |  |  |

## Test record

| Test | Setup / instruments | Result | Date / operator | Evidence |
|---|---|---|---|---|
| GPIO OFF state at boot | Loads disconnected |  |  |  |
| Solenoid 1 relay ON/OFF | Approved isolated test setup |  |  |  |
| Solenoid 2 relay ON/OFF | Approved isolated test setup |  |  |  |
| Solenoid 3 relay ON/OFF | Approved isolated test setup |  |  |  |
| 1-second cutoff | Approved isolated test setup |  |  |  |
| 5-second cutoff | Approved isolated test setup |  |  |  |
| Shutdown during pulse | Approved isolated test setup |  |  |  |
| Python process termination | Approved isolated test setup |  |  |  |
| BeagleBone reboot / power loss | Approved isolated test setup |  |  |  |
| Physical valve closure feedback | Approved procedure |  |  |  |

## Approval

- Hardware owner: __________________________ Date: __________
- Software owner: __________________________ Date: __________
- Operations / safety reviewer: ______________ Date: __________

This record documents observed tests; it does not replace the system risk assessment or approved operating procedure.
