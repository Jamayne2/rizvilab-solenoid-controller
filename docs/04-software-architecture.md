# 4. Software architecture

## Runtime and imports

`main.py` is a Python 2 application using:

- `PyQt4.QtGui` and `PyQt4.QtCore` for the touchscreen interface, timers, and animation.
- `Adafruit_BBIO.GPIO` for BeagleBone GPIO control.
- `Adafruit_BBIO.ADC` and `Adafruit_GPIO.I2C` imports retained from the legacy application.
- `serial` and standard-library modules retained by the original application.
- `constants.py`, `system_constants.py`, and `directory_constants.py` for configuration and legacy values.

The exact package versions are not pinned. Record the actual deployed environment rather than assuming a generic current Debian/Python environment will support Python 2 and PyQt4.

## Important functions in `main.py`

### Module-level hardware and startup functions

| Function | Responsibility |
|---|---|
| `setup_gpio()` | Configure the three solenoid pins as outputs and command LOW |
| `initialize_system()` | Call `setup_gpio()` before creating the GUI |
| `set_gpio(pin, state)` | Translate a boolean state to GPIO HIGH/LOW |
| `set_nozzle_solenoid(...)` | Command one solenoid or all mapped solenoids |
| `main()` | Initialize hardware, create QApplication and GUI, start Qt event loop |

### `IceCreamGUI` initialization

`IceCreamGUI.__init__()` is large because the legacy interface builds many widgets in one place. It initializes the current pulse settings and cutoff timer, sets the shutdown latch false, resets outputs, creates old and current widgets, and calls `initUI()`.

`initUI()` wires button signals and timer callbacks, shows Welcome, enters fullscreen, and calls `scale_ui_to_screen()`. The order of widget construction and signal wiring matters. Avoid casually moving statements inside `__init__()` or `initUI()`.

### Current operator-path methods

| Method | Responsibility |
|---|---|
| `show_w1()` / `w1_continue_button_callback()` | Welcome and transition to startup title |
| `show_instruction_intro(mode)` | Shared startup/shutdown title page; Back is only shown for startup |
| `instruction_intro_continue_clicked()` | Enter W4 startup images or W13 shutdown images |
| `show_w4()` / `update_startup_image()` | Load and display the five startup images |
| `w4_continue_button_callback()` | Advance startup; on final step command all OFF, clear latch, show controls |
| `w4_back_button_callback()` | Previous startup image or startup title |
| `show_w9()` / `hide_w9()` | Show/hide current solenoid controls |
| `edit_nozzle_duration(n)` | Edit only solenoid `n`'s duration (1–5 seconds) |
| `w9_fire_nozzle_button_callback(n)` | Block if latched; otherwise transition to dispensing |
| `show_w9a(n)` | Command selected solenoid ON, start cutoff timer and progress animation |
| `hide_w9a()` | Stop timing/animation, command all solenoids OFF, return to controls if not latched |
| `all_solenoids_off()` | Stop relevant timers/animations and request LOW for all three outputs |
| `w9_shutdown_button_callback()` | Set latch, command all OFF, show shutdown title |
| `show_w13()` / `update_shutdown_image()` | Load and display shutdown illustrations |
| `w13_continue_button_callback()` | Advance shutdown; final step enters standby |
| `w13_back_button_callback()` | Previous shutdown image or shutdown title; does not return to controls |
| `enter_standby()` / `wake_from_standby()` | Display dark overlay and return to Welcome without clearing latch |

The root README includes a broader function index for retained legacy functions. Search the method name in `main.py` if line numbers change.

## Timers and animations

| Object | Role |
|---|---|
| `solenoid_cutoff_timer` | Single-shot software pulse cutoff; timeout calls `hide_w9a()` |
| `w9a_dispensing_animation` | Visual progress animation; range 0–1000, duration matches selected pulse |
| `cycle_nozzle_solenoid_timer` | Retained legacy timer; not the normal per-nozzle pulse cutoff path |
| Other timers | Several startup, shutdown, temperature, and system-state timers are retained from the legacy controller; do not assume they are active in the current workflow |

## Configuration modules

### `constants.py`

Contains `SOLENOID_NUMBER_PIN`, the `IMAGES_FOLDER` path, GUI style strings, legacy pressure command lookup values, and old heater pin constants. The active solenoid mapping is the dictionary shown in [Hardware and GPIO](03-hardware-and-gpio.md).

### `system_constants.py`

Contains historical operating ranges, safe-shutdown ranges, and default temperature/pressure/blast setpoints. These values are not proof that current pressure/temperature interlocks are active.

### `directory_constants.py`

Contains legacy absolute paths for setpoint and data-log storage under `/home/debian/controller-final`. The current independent solenoid pulse durations are held in RAM and are not saved using these paths.

## Retained helper files

- `preview_original.py` is intended as a read-only preview utility. Review its safety comments before running; it is not the production launcher.
- `bus.py` is a standalone I2C pressure-reading experiment. It calls `read_pressure()` at module import time, so importing it can perform an I2C transaction. It is not imported by the current `main.py` path. Do not import it casually or treat it as a required runtime dependency.

## Legacy code boundary

Old W2–W15 screens, heater control, pressure/Alicat functions, sensor readers, setpoint storage, and CSV logging remain in `main.py`. Some legacy Qt signals are still connected. Their presence is for retained compatibility/reference, not a guarantee that those features are safe or active. Review the call path and hardware before enabling any legacy page or timer.
