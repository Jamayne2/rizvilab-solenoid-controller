# 3. Hardware and GPIO

## Software pin mapping

The current `constants.py` defines the active solenoid mapping:

| Solenoid | BeagleBone header pin | Linux GPIO number used by `start.sh` | Python constant |
|---|---|---:|---|
| 1 | `P9_16` | 51 | `SOLENOID_NUMBER_PIN[1]` |
| 2 | `P9_25` | 117 | `SOLENOID_NUMBER_PIN[2]` |
| 3 | `P9_12` | 60 | `SOLENOID_NUMBER_PIN[3]` |

The Linux GPIO numbers in `start.sh` correspond to the header pins in `constants.py` in the current project snapshot. Do not change one side without checking the other side and verifying the BeagleBone pinmux / GPIO mapping on the deployed OS.

## Command semantics in software

| Python call | GPIO command |
|---|---|
| `set_nozzle_solenoid(n, True)` | `GPIO.HIGH` on solenoid `n`'s mapped pin |
| `set_nozzle_solenoid(n, False)` | `GPIO.LOW` on solenoid `n`'s mapped pin |
| `set_nozzle_solenoid(False)` | LOW command to every pin in `SOLENOID_NUMBER_PIN` |

The code assumes HIGH means relay ON and LOW means relay OFF. Verify this on the actual relay board with the valve loads disconnected. Confirm whether the relay input is active-high, whether it is isolated, and what state it assumes during BeagleBone boot, process exit, or loss of GPIO configuration.

## What this repository does not specify

The Python source is not a wiring diagram. Before handing over the system, add verified information for:

- Exact relay board / Grove Cape model and revision.
- Relay channel-to-nozzle mapping and terminal labels (COM, NO, NC).
- Solenoid valve manufacturer, model, rated voltage, current, and polarity requirements.
- External valve power-supply voltage/current and return wiring.
- Fuse / breaker part numbers and ratings, where fitted.
- Connector manufacturer, series, pin numbers, wire gauge, and mating part numbers.
- Grounding, isolation, flyback suppression, and cable-routing details.
- Emergency stop, pressure isolation, and other hardwired interlocks.

Use the electrical schematic, harness drawing, bill of materials, and physical inspection to fill in [the hardware verification template](hardware-verification-template.md). Do not infer these details from GPIO names.

## Initial hardware verification procedure

Perform this only under the team's approved lab/test-stand procedure:

1. Isolate pneumatic supplies and disconnect solenoid loads.
2. Verify the BeagleBone pin mapping and relay input wiring against the approved drawing.
3. Start the application and confirm the initial GPIO OFF commands.
4. Test one relay channel at a time using a safe, current-limited/isolated test arrangement approved by the hardware lead.
5. Confirm commanded ON and OFF behavior at the relay input/output with suitable instruments.
6. Verify power-up, process termination, and controller reboot behavior. Do not assume software shutdown guarantees a safe hardware state.
7. Record results, date, operator, instrument, and drawing revision in the hardware verification record.

Do not connect pressurized equipment based solely on a successful GUI test.
