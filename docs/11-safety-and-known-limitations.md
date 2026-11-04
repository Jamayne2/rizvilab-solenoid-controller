# 11. Safety and known limitations

> **This document describes software behavior. It is not a risk assessment, operating procedure, or safety certification. Use the approved RIZVILAB test-stand procedures and hardware interlocks.**

## Software OFF is not physical confirmation

`all_solenoids_off()` sends LOW commands to the three GPIO outputs and updates software bookkeeping. The application does not read an independent valve-position sensor to prove that a valve physically closed. A relay output, wiring fault, welded contact, failed driver, or valve fault can make physical behavior differ from the software state.

## QTimer is not a hardware safety cutoff

`solenoid_cutoff_timer` is a Qt/Python single-shot timer. It depends on the BeagleBone operating system, Python process, and Qt event loop continuing to run. It cannot guarantee cutoff if the process crashes, the event loop blocks, the OS hangs, or the controller loses power.

The progress animation is only a visual indication. It is not the cutoff mechanism. Any required fail-safe cutoff must be designed and validated independently in hardware under the system risk assessment.

## Shutdown and standby are not power isolation

The shutdown flow sends OFF commands and displays illustrated instructions. The final dark standby screen leaves the BeagleBone and application running. It is not equivalent to powering down the computer or isolating electrical/pneumatic energy.

Follow approved procedures for isolating compressed gas, electrical supplies, stored energy, and any other hazards. Verify safe physical state using approved instruments and procedures.

## Legacy code is retained

The application still contains older pressure, temperature, heater, Alicat, setpoint, logging, and operating-state routines. Their code presence does not mean their sensors are connected, calibrated, active, or interlocked in the current solenoid-only flow. Do not use legacy screens or routines for operational decisions without a separate review.

`system_constants.py` includes historical operating and shutdown ranges. These values must not be treated as current approved operating limits unless the responsible hardware/safety owner confirms them.

## Startup/shutdown images must be approved

The image files include equipment-specific steps and at least one displayed regulator setting. Verify all text, values, equipment labels, and sequence against the current approved test-stand procedure. Update the procedure and images under controlled review if the physical setup changes.

## Hardware facts requiring confirmation

Before the controller is handed over for operation, confirm and record:

- Relay board part number/revision and active polarity.
- Valve model, rated coil voltage/current, and actual wiring.
- Output power source and return path.
- Fuses/protection and wiring ratings.
- Connector pinouts and cable identification.
- Hardwired interlocks and emergency-stop behavior.
- Safe state during boot, shutdown, process crash, and power loss.
- Physical method for verifying valve closure and pressure isolation.

See [hardware verification template](hardware-verification-template.md).

## Operational test restriction

For software-only testing, disconnect solenoid loads and isolate pneumatic supplies. Use an approved test setup to verify relay behavior. Do not use a successful GUI test as authorization to operate pressurized equipment.
