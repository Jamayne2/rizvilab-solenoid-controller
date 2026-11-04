# 2. System architecture

## High-level architecture

```text
Touchscreen operator
        |
        v
PyQt4 GUI (main.py / IceCreamGUI)
        |
        +--> Startup / shutdown navigation
        |
        +--> Per-solenoid pulse-duration settings (RAM)
        |
        +--> QTimer cutoff + progress animation
        |
        v
Adafruit_BBIO.GPIO
        |
        v
BeagleBone Black header GPIO pins
        |
        v
Relay inputs / relay modules
        |
        v
Solenoid valve electrical loads
```

The GUI is the operator interface. The Python application commands the three BeagleBone GPIO outputs through `Adafruit_BBIO.GPIO`. The physical relay module, valve wiring, power distribution, protection, and any hardwired safety circuit are external hardware and must be documented separately using the approved electrical drawings.

## Application startup sequence

The executable entry point is at the bottom of `main.py`:

1. `main()` calls `initialize_system()`.
2. `initialize_system()` calls `setup_gpio()`.
3. `setup_gpio()` configures the three solenoid GPIO pins as outputs and commands them LOW.
4. A `QApplication` is created.
5. `IceCreamGUI()` is instantiated.
6. `IceCreamGUI.__init__()` initializes application state, pulse durations, the cutoff timer, widgets, signal connections, and UI initialization.
7. `initUI()` displays Welcome, switches to fullscreen, and calls `scale_ui_to_screen()`.
8. The Qt event loop runs through `app.exec_()`.

The exact deployed GUI launch also depends on `start.sh` and the graphical desktop session. See [Installation and deployment](07-installation-and-deployment.md) and [Autostart](08-autostart-and-startup.md).

## Output command path

The active pin mapping is held in `constants.py` as `SOLENOID_NUMBER_PIN`. `main.py` derives `NOZZLE_SOLENOID1_RELAY`, `NOZZLE_SOLENOID2_RELAY`, and `NOZZLE_SOLENOID3_RELAY` from that dictionary.

`set_nozzle_solenoid(number, state)` selects one mapped pin and calls `set_gpio()`. `set_gpio()` sends `GPIO.HIGH` for a true state and `GPIO.LOW` for a false state. The software therefore treats HIGH as the ON command and LOW as the OFF command. Verify the relay module's actual input polarity and power-up behavior against the hardware documentation before connecting valves.

## State management

The important state variables are:

| Variable | Meaning |
|---|---|
| `current_screen` | Current GUI page/state identifier, such as `w1`, `w4`, `w9`, `w9a`, `w13`, or `standby` |
| `pulse_durations` | Dictionary of seconds for solenoids 1, 2, and 3; initialized to 1 second each |
| `shutdown_latched` | Blocks new pulses after shutdown begins; cleared only at the end of the startup image sequence after OFF commands are sent |
| `nozzle_solenoid_on` | Software bookkeeping of commanded solenoid states; not physical position feedback |
| `startup_step` / `shutdown_step` | Current index in the respective illustrated sequence |

## Timing architecture

`solenoid_cutoff_timer` is a single-shot `QtCore.QTimer`. Its timeout is connected to `hide_w9a()`. The progress animation is a separate visual indicator. Both completion paths lead to `hide_w9a()`, which requests all three solenoids OFF and returns to the control page unless shutdown is latched.

This is software timing. It is not a hardware watchdog or safety-rated cutoff. See [Safety and known limitations](11-safety-and-known-limitations.md).
