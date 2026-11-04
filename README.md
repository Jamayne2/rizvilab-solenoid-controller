# RIZVILAB Solenoid Controller — BeagleBone Black

**Controller:** Python 2 / PyQt4 touchscreen application (`main.py`) using `Adafruit_BBIO.GPIO`.
**Hardware:** BeagleBone Black, touchscreen, and three active-high solenoid relay outputs.
**Entry point:** [`main()`](main.py#L4668) calls `initialize_system()` and starts the Qt event loop.

> **Scope of this refactor:** Function definitions in `main.py` have been reorganized by responsibility and each function has an explanatory comment. All **155 method bodies** and all top-level executable definitions/statements are identical to the uploaded version; the current UI layout, timing, wiring, state transitions, and relay commands have **not** been redesigned or modified. `start.sh`, `constants.py`, assets, and other project files are unchanged. See [Verification](#refactor-verification) below.

## Quick navigation

- [Application flow](#application-flow)
- [How pulsing works](#how-pulsing-works)
- [Shutdown and dark standby](#shutdown-and-dark-standby)
- [Where widgets and images are defined](#where-widgets-and-images-are-defined)
- [Function index (all functions and methods)](#function-index-all-functions-and-methods)
- [Run, autostart, and diagnostics](#run-autostart-and-diagnostics)
- [Legacy features and hardware caution](#legacy-features-and-hardware-caution)
- [Refactor verification](#refactor-verification)


## Handover documentation

The detailed maintainer and operator handover guides are in [`docs/`](docs/README.md). Start with the [project overview](docs/01-project-overview.md), then review the [hardware/GPIO map](docs/03-hardware-and-gpio.md), [software architecture](docs/04-software-architecture.md), [deployment](docs/07-installation-and-deployment.md), and [safety limitations](docs/11-safety-and-known-limitations.md). The [handover checklist](docs/12-handover-checklist.md) lists what must be verified before transferring ownership.

## Application flow

```text
Power applied / Python starts
  main() -> initialize_system() -> setup_gpio() -> IceCreamGUI.__init__()
  -> initUI() -> show_w1() -> FULLSCREEN WELCOME
       |
       v
  STARTUP INSTRUCTIONS title (BACK available)
       |
       v
  W4: five startup images (BACK/CONTINUE)
       |
       +-- final CONTINUE -> all_solenoids_off()
       |                      -> shutdown_latched = False
       v
  W9: three GO buttons + an individual TIME button per solenoid
       |
       +-- TIME N -> edit_nozzle_duration(N) -> 1..5 seconds, only N changes
       +-- GO N   -> W9a -> energize N -> cutoff timer + progress animation
       |                      -> hide_w9a() -> command OFF -> W9
       |
       +-- SHUTDOWN -> shutdown_latched = True -> all_solenoids_off()
                          |
                          v
                 SHUTDOWN INSTRUCTIONS title (NO BACK)
                          |
                          v
                 W13: five shutdown images (BACK/CONTINUE)
                          |
                          v
                 enter_standby() -> dark tap-anywhere overlay
                          |
                          v
                 wake_from_standby() -> WELCOME
                 (latch stays set until startup completes again)
```

**Fresh power cycle:** The running program does not persist the standby screen. A new process starts at Welcome. **Standby is not a power-off:** the software remains running.

### Screen / state reference

| State | What the operator sees | Main entry/exit code |
| --- | --- | --- |
| `w1` | Welcome graphic and Continue | [`show_w1()`](main.py#L2142), [`w1_continue_button_callback()`](main.py#L2155) |
| `startup_intro` | Startup Instructions title, Back / Continue | [`show_instruction_intro()`](main.py#L2161), [`instruction_intro_back_clicked()`](main.py#L2206) |
| `w4` | Five startup illustrations, Back / Continue | [`show_w4()`](main.py#L2242), [`w4_continue_button_callback()`](main.py#L2331) |
| `w9` | Three GO buttons and independent TIME buttons, Shutdown | [`show_w9()`](main.py#L2384), [`edit_nozzle_duration()`](main.py#L2425) |
| `w9a` | Dispensing text and animated progress | [`show_w9a()`](main.py#L2593), [`hide_w9a()`](main.py#L2640) |
| `shutdown_intro` | Shutdown Instructions title, Continue only | [`show_instruction_intro()`](main.py#L2161), [`w9_shutdown_button_callback()`](main.py#L2730) |
| `w13` | Five shutdown illustrations, Back / Continue | [`show_w13()`](main.py#L2765), [`w13_continue_button_callback()`](main.py#L2825) |
| `standby` | Fullscreen dark screen, tap to wake | [`enter_standby()`](main.py#L2854), [`wake_from_standby()`](main.py#L2885) |

## How pulsing works

1. `pulse_durations = {1: 1, 2: 1, 3: 1}` is initialized in [`__init__()`](main.py#L305). These durations are independent and live in memory (they are not written to disk).
2. W9's per-nozzle TIME buttons are constructed in [`__init__()`](main.py#L305) and opened through [`edit_nozzle_duration(nozzle_number)`](main.py#L2425). The editor offers **1–5 seconds** and changes only the chosen number.
3. GO invokes [`w9_fire_nozzle_button_callback(nozzle_number)`](main.py#L2577). A true `shutdown_latched` prevents a pulse.
4. [`show_w9a(nozzle_number)`](main.py#L2593) commands that relay **ON**, starts `solenoid_cutoff_timer` for `duration_ms`, and animates the visual bar across **0–1000** steps.
5. The cutoff timer is created and connected to [`hide_w9a()`](main.py#L2640) inside [`__init__()`](main.py#L305); the progress animation also has its own finished callback to the same method. `hide_w9a()` stops timing and requests **OFF** for all three relays.
6. [`all_solenoids_off()`](main.py#L2678) stops relevant timers and animations and issues an OFF request to every solenoid. This is used on shutdown and before re-enabling controls at the end of startup.

**Timing caveat:** The timer and animation run in the Python/Qt process. A Python crash, blocked event loop, or loss of power to the controller can interrupt software timing. An OFF command is not feedback confirming physical valve closure; hardware-level fail-safe design and physical isolation must be evaluated separately.

### GPIO output mapping

The active mapping comes from [`SOLENOID_NUMBER_PIN`](constants.py) and is used by [`set_nozzle_solenoid()`](main.py#L128). The `start.sh` pre-export script uses the corresponding Linux GPIO numbers.

| Device | Header pin | Linux GPIO | OFF / ON request |
| --- | --- | --- | --- |
| Solenoid 1 | `P9_16` | 51 | `GPIO.LOW` / `GPIO.HIGH` |
| Solenoid 2 | `P9_25` | 117 | `GPIO.LOW` / `GPIO.HIGH` |
| Solenoid 3 | `P9_12` | 60 | `GPIO.LOW` / `GPIO.HIGH` |

## Shutdown and dark standby

- [`w9_shutdown_button_callback()`](main.py#L2730) sets `shutdown_latched`, requests all outputs OFF, and enters the shared Shutdown Instructions title page.
- That **title page does not have a Back button**. Individual shutdown illustration pages do have Back/Continue; their first Back returns to the title, never directly to W9.
- After the last image, [`w13_continue_button_callback()`](main.py#L2825) calls [`enter_standby()`](main.py#L2854). It keeps the shutdown latch and displays a dark, fullscreen `standby_button` overlay.
- Tapping anywhere runs [`wake_from_standby()`](main.py#L2885), restores the Welcome image, and does **not** re-enable the relays.
- Only the final startup illustration's [`w4_continue_button_callback()`](main.py#L2331) clears the latch after requesting outputs OFF. A fresh process starts at Welcome with default pulse durations.

## Where widgets and images are defined

This legacy UI constructs widgets in one large [`IceCreamGUI.__init__()`](main.py#L305) function. **Do not move statements inside `__init__` casually:** timers, signal connections, and widgets are created in an order needed by initialization.

| To change | Look for | Defined / handled in |
| --- | --- | --- |
| GO nozzle button position/size | `w9_fire_nozzle1_button` / `2` / `3` `.move`, `.resize`, `.setGeometry` | [`__init__()`](main.py#L305) |
| Individual TIME button geometry | `pulse_time_buttons`, `button.setGeometry` | [`__init__()`](main.py#L305) |
| Time-selection dialog styling | `QtGui.QDialog`, `TimeOption`, `Save` | [`edit_nozzle_duration()`](main.py#L2425) |
| Pulse duration / cutoff | `duration_ms`, `solenoid_cutoff_timer` | [`show_w9a()`](main.py#L2593), [`__init__()`](main.py#L305) |
| Pulse animation appearance | `w9a_dispensing_progressbar`, `w9a_dispensing_animation` | [`__init__()`](main.py#L305), [`show_w9a()`](main.py#L2593) |
| Startup title BACK / CONTINUE | `instruction_intro_back`, `instruction_intro_continue` | [`__init__()`](main.py#L305), [`show_instruction_intro()`](main.py#L2161) |
| Startup image BACK / CONTINUE | `w4_back_button`, `w4_continue_button` | [`__init__()`](main.py#L305), [`show_w4()`](main.py#L2242) |
| Shutdown image BACK / CONTINUE | `w13_back_button`, `w13_continue_button` | [`__init__()`](main.py#L305), [`show_w13()`](main.py#L2765) |
| Startup images | `self.startup_images` | [`show_w4()`](main.py#L2242); files under `window-background-images/` |
| Shutdown images | `self.shutdown_images` | [`show_w13()`](main.py#L2765); files under `window-background-images/` |
| Dark standby overlay | `standby_button` and `setGeometry(self.rect())` | [`__init__()`](main.py#L305), [`enter_standby()`](main.py#L2854) |
| Fullscreen resizing | `showFullScreen`, `scale_ui_to_screen` | [`initUI()`](main.py#L1910), [`scale_ui_to_screen()`](main.py#L2021) |
| Qt signal and timer wiring | `.clicked.connect`, `.timeout.connect`, `.finished.connect` | [`__init__()`](main.py#L305) and [`initUI()`](main.py#L1910) |

**Position syntax:** `setGeometry(x, y, width, height)`; `move(x, y)` changes position; `resize(width, height)` changes size. The GUI scales the original **480 × 272** design coordinates to the touchscreen resolution, and background graphics are expanded to fill the screen. The five historic startup illustrations include procedures/pressure values from an earlier setup: check those against approved equipment procedures before use.

## Project files

| File | Purpose |
| --- | --- |
| [`main.py`](main.py) | UI, state/navigation, pulse settings, relay commands, historical helpers |
| [`constants.py`](constants.py) | GPIO mappings, operating ranges, defaults |
| [`system_constants.py`](system_constants.py) | Additional historical controller constants |
| [`directory_constants.py`](directory_constants.py) | Directories and legacy data-file paths |
| [`start.sh`](start.sh) | Exports Linux GPIO 51, 117, 60, sets DISPLAY, launches `python2 main.py` |
| [`bus.py`](bus.py) | Retained I2C-related helper file |
| [`preview_original.py`](preview_original.py) | Historical/preview helper, not the autostart entrypoint |
| [`window-background-images/`](window-background-images/) | Splash, CALS backgrounds, startup/shutdown illustrations |
| `*.pyc`, `log.txt`, `window-background-images/t5*.py` | Files carried through from the original archive unchanged; not required to understand current `main.py` flow |

## Function index (all functions and methods)

Every definition in `main.py` is listed below with its **line location in this refactored file**. Use these links rather than old line numbers; method positions changed deliberately.

### Module-level functions

| Location | Function | Responsibility |
| --- | --- | --- |
| [`L82`](main.py#L82) | `setup_gpio()` | Initialize only the three solenoid GPIO outputs and command LOW; raise errors on setup failure. |
| [`L106`](main.py#L106) | `setup_analog_inputs()` | Retained legacy thermocouple input assignments; not called by initialize_system(). |
| [`L117`](main.py#L117) | `initialize_system()` | Invoke setup_gpio() (analog setup is commented out). |
| [`L122`](main.py#L122) | `set_gpio()` | Translate Boolean requested output state into HIGH/LOW GPIO.output. |
| [`L128`](main.py#L128) | `set_nozzle_solenoid()` | Command one specified solenoid, or (one-argument form) all solenoids. |
| [`L141`](main.py#L141) | `set_nozzle_vessel_heater()` | Retained legacy heater GPIO setter; not part of normal solenoid path. |
| [`L145`](main.py#L145) | `set_pressure_vessel_heater()` | Retained legacy heater GPIO setter; not part of normal solenoid path. |
| [`L149`](main.py#L149) | `read_vessel_pressure()` | Retained I2C ADC121 vessel-pressure conversion. |
| [`L185`](main.py#L185) | `get_alicat_pressure_code()` | Format a legacy Alicat command from a supported pressure setpoint. |
| [`L222`](main.py#L222) | `set_alicat_pressure()` | Send the historical Alicat pressure setting over serial. |
| [`L253`](main.py#L253) | `read_alicat_downstream_pressure()` | Read the historical Alicat pressure response over serial. |
| [`L4668`](main.py#L4668) | `main()` | Initialize outputs, create QApplication + IceCreamGUI, run the Qt event loop. |

### `IceCreamGUI` methods (grouped in source order)

#### 1. Construction, settings, UI wiring, and scaling

Startup objects, Qt signals, timing, legacy initialization, and the 480-by-272 scaling pass.

| Location | Method | Responsibility |
| --- | --- | --- |
| [`L305`](main.py#L305) | `__init__()` | Build the complete widget tree, initialize GPIO-facing software state, create timers and animations, then call initUI. Statement order inside is unchanged. |
| [`L1698`](main.py#L1698) | `_set_variables()` | Copy constants, file paths, operating ranges, and legacy defaults into instance attributes. |
| [`L1749`](main.py#L1749) | `initialize_setpoints()` | Load or initialize historical operating setpoints. |
| [`L1758`](main.py#L1758) | `adjust_operating_ranges()` | Derive allowable legacy operating ranges from current setpoints. |
| [`L1775`](main.py#L1775) | `initialize_scrollbars()` | Initialize legacy setpoint scrollbar ranges and widget values. |
| [`L1811`](main.py#L1811) | `initialize_logging_and_timing_controls()` | Initialize historical timing/logging values; disabled at current initialization call site. |
| [`L1822`](main.py#L1822) | `initialize_system_state()` | Initialize historical controller state flags and screen timing. |
| [`L1835`](main.py#L1835) | `initialize_control_variables()` | Initialize legacy control and sensor state variables. |
| [`L1854`](main.py#L1854) | `create_solenoid_relay_ui()` | Construct the legacy subsystem-test label, status checkbox, and test button. |
| [`L1910`](main.py#L1910) | `initUI()` | Connect button signals and QTimer callbacks, display Welcome, enter fullscreen, then scale controls. |
| [`L2021`](main.py#L2021) | `scale_ui_to_screen()` | Scale widgets and font styling from reference 480x272 geometry to the actual display. |

#### 2. Welcome and startup instruction workflow

Main operator path: Welcome -> Startup title -> five images -> unlocked nozzle controls.

| Location | Method | Responsibility |
| --- | --- | --- |
| [`L2142`](main.py#L2142) | `show_w1()` | Show the Welcome Continue button and set current_screen to w1. |
| [`L2148`](main.py#L2148) | `hide_w1()` | Hide the Welcome button and set the neutral CALS background. |
| [`L2155`](main.py#L2155) | `w1_continue_button_callback()` | Leave Welcome and open the Startup Instructions title screen. |
| [`L2161`](main.py#L2161) | `show_instruction_intro()` | Display the shared startup/shutdown heading; allow Back on startup title only. |
| [`L2198`](main.py#L2198) | `hide_instruction_intro()` | Hide shared title and navigation controls. |
| [`L2206`](main.py#L2206) | `instruction_intro_back_clicked()` | From Startup Instructions, restore the Welcome splash and show W1. |
| [`L2227`](main.py#L2227) | `instruction_intro_continue_clicked()` | Open first illustration of startup (W4) or shutdown (W13) and reset step index. |
| [`L2242`](main.py#L2242) | `show_w4()` | Load five startup illustration paths and display W4 Back/Continue. |
| [`L2282`](main.py#L2282) | `update_startup_image()` | Draw the current startup image and set the last-step Continue label. |
| [`L2306`](main.py#L2306) | `hide_w4()` | Hide W4 controls, restore neutral background, and hide optional review warning. |
| [`L2331`](main.py#L2331) | `w4_continue_button_callback()` | Advance the startup sequence; after last step send OFF commands, clear shutdown latch, and show controls. |
| [`L2365`](main.py#L2365) | `w4_back_button_callback()` | Go to preceding startup image, or to the Startup Instructions title from step one. |

#### 3. Current nozzle controls and pulse lifecycle

Individual pulse setting, on/off command, visual animation, cutoff, shutdown latch.

| Location | Method | Responsibility |
| --- | --- | --- |
| [`L2384`](main.py#L2384) | `show_w9()` | Show three GO buttons and three time buttons, enabling them only when not shutdown-latched. |
| [`L2414`](main.py#L2414) | `hide_w9()` | Hide nozzle, duration, Admin, and shutdown buttons. |
| [`L2425`](main.py#L2425) | `edit_nozzle_duration()` | Open the custom five-option popup and update only the selected nozzle duration and label. |
| [`L2577`](main.py#L2577) | `w9_fire_nozzle_button_callback()` | Block a pulse if latched; otherwise transition W9 -> W9a for selected nozzle. |
| [`L2593`](main.py#L2593) | `show_w9a()` | Start one selected solenoid, run its independent cutoff timer, and animate progress on a 0..1000 scale. |
| [`L2640`](main.py#L2640) | `hide_w9a()` | Stop cutoff and animation, command all solenoids OFF, then return to controls if not shutdown-latched. |
| [`L2678`](main.py#L2678) | `all_solenoids_off()` | Stop relevant timers/animations and request LOW on all three relays; raise on failed OFF commands. |
| [`L2730`](main.py#L2730) | `w9_shutdown_button_callback()` | Latch shutdown, request all outputs OFF, hide controls, open Shutdown Instructions title; show OFF errors. |

#### 4. Shutdown instructions and standby/wake

Shutdown title -> illustrated steps -> dark standby overlay -> tap to return to Welcome.

| Location | Method | Responsibility |
| --- | --- | --- |
| [`L2765`](main.py#L2765) | `show_w13()` | Load five shutdown illustration filenames, display first image and Back/Continue controls. |
| [`L2787`](main.py#L2787) | `update_shutdown_image()` | Load current shutdown illustration, fall back on missing file, update Continue label. |
| [`L2817`](main.py#L2817) | `hide_w13()` | Hide shutdown illustration controls and restore neutral CALS background. |
| [`L2825`](main.py#L2825) | `w13_continue_button_callback()` | Advance the shutdown slideshow; after last step enter standby instead of returning Home. |
| [`L2842`](main.py#L2842) | `w13_back_button_callback()` | Return to prior shutdown image or the Shutdown Instructions title; never to controls. |
| [`L2854`](main.py#L2854) | `enter_standby()` | Latch shutdown, command all outputs OFF, then show full-screen dark tap-to-wake overlay. |
| [`L2885`](main.py#L2885) | `wake_from_standby()` | Hide dark overlay and restore Welcome without clearing shutdown latch. |

#### 5. Shared/historical screen views and widget visibility

Retained historical screens; the normal operator path uses W1/W4/W9/W9a/W13 instead.

| Location | Method | Responsibility |
| --- | --- | --- |
| [`L2916`](main.py#L2916) | `show_confirmation_screen()` | Retained helper for show confirmation screen. |
| [`L2925`](main.py#L2925) | `hide_confirmation_screen()` | Retained helper for hide confirmation screen. |
| [`L2935`](main.py#L2935) | `hide_controller_subsystem_status_widgets()` | Retained helper for hide controller subsystem status widgets. |
| [`L2950`](main.py#L2950) | `show_controller_subsystem_status_widgets()` | Retained helper for show controller subsystem status widgets. |
| [`L2965`](main.py#L2965) | `show_w2()` | Display the historical W2 screen and its associated widgets. |
| [`L2975`](main.py#L2975) | `hide_w2()` | Hide the historical W2 widgets and restore/hide associated screen elements. |
| [`L2983`](main.py#L2983) | `show_w2a()` | Display the historical W2A screen and its associated widgets. |
| [`L2992`](main.py#L2992) | `hide_w2a()` | Hide the historical W2A widgets and restore/hide associated screen elements. |
| [`L2999`](main.py#L2999) | `show_w2b()` | Display the historical W2B screen and its associated widgets. |
| [`L3006`](main.py#L3006) | `hide_w2b()` | Hide the historical W2B widgets and restore/hide associated screen elements. |
| [`L3012`](main.py#L3012) | `show_w3()` | Display the historical W3 screen and its associated widgets. |
| [`L3022`](main.py#L3022) | `hide_w3()` | Hide the historical W3 widgets and restore/hide associated screen elements. |
| [`L3029`](main.py#L3029) | `show_w5()` | Display the historical W5 screen and its associated widgets. |
| [`L3037`](main.py#L3037) | `hide_w5()` | Hide the historical W5 widgets and restore/hide associated screen elements. |
| [`L3045`](main.py#L3045) | `show_w5a()` | Display the historical W5A screen and its associated widgets. |
| [`L3053`](main.py#L3053) | `hide_w5a()` | Hide the historical W5A widgets and restore/hide associated screen elements. |
| [`L3061`](main.py#L3061) | `show_w5b()` | Display the historical W5B screen and its associated widgets. |
| [`L3069`](main.py#L3069) | `hide_w5b()` | Hide the historical W5B widgets and restore/hide associated screen elements. |
| [`L3077`](main.py#L3077) | `hide_system_startup_widgets()` | Retained helper for hide system startup widgets. |
| [`L3098`](main.py#L3098) | `show_system_startup_widgets()` | Retained helper for show system startup widgets. |
| [`L3118`](main.py#L3118) | `show_w6()` | Display the historical W6 screen and its associated widgets. |
| [`L3131`](main.py#L3131) | `hide_w6()` | Hide the historical W6 widgets and restore/hide associated screen elements. |
| [`L3140`](main.py#L3140) | `show_w6a()` | Display the historical W6A screen and its associated widgets. |
| [`L3150`](main.py#L3150) | `hide_w6a()` | Hide the historical W6A widgets and restore/hide associated screen elements. |
| [`L3158`](main.py#L3158) | `show_w7()` | Display the historical W7 screen and its associated widgets. |
| [`L3168`](main.py#L3168) | `hide_w7()` | Hide the historical W7 widgets and restore/hide associated screen elements. |
| [`L3175`](main.py#L3175) | `show_w8()` | Display the historical W8 screen and its associated widgets. |
| [`L3184`](main.py#L3184) | `hide_w8()` | Hide the historical W8 widgets and restore/hide associated screen elements. |
| [`L3192`](main.py#L3192) | `show_w8a()` | Display the historical W8A screen and its associated widgets. |
| [`L3203`](main.py#L3203) | `hide_w8a()` | Hide the historical W8A widgets and restore/hide associated screen elements. |
| [`L3213`](main.py#L3213) | `show_w10()` | Display the historical W10 screen and its associated widgets. |
| [`L3221`](main.py#L3221) | `hide_w10()` | Hide the historical W10 widgets and restore/hide associated screen elements. |
| [`L3228`](main.py#L3228) | `show_w11()` | Display the historical W11 screen and its associated widgets. |
| [`L3277`](main.py#L3277) | `hide_w11()` | Hide the historical W11 widgets and restore/hide associated screen elements. |
| [`L3285`](main.py#L3285) | `show_w12()` | Display the historical W12 screen and its associated widgets. |
| [`L3294`](main.py#L3294) | `hide_w12()` | Hide the historical W12 widgets and restore/hide associated screen elements. |
| [`L3301`](main.py#L3301) | `show_w13a()` | Display the historical W13A screen and its associated widgets. |
| [`L3309`](main.py#L3309) | `hide_w13a()` | Hide the historical W13A widgets and restore/hide associated screen elements. |
| [`L3316`](main.py#L3316) | `show_w13b()` | Display the historical W13B screen and its associated widgets. |
| [`L3324`](main.py#L3324) | `hide_w13b()` | Hide the historical W13B widgets and restore/hide associated screen elements. |
| [`L3331`](main.py#L3331) | `show_w14()` | Display the historical W14 screen and its associated widgets. |
| [`L3339`](main.py#L3339) | `hide_w14()` | Hide the historical W14 widgets and restore/hide associated screen elements. |
| [`L3346`](main.py#L3346) | `show_w15()` | Display the historical W15 screen and its associated widgets. |
| [`L3355`](main.py#L3355) | `hide_w15()` | Hide the historical W15 widgets and restore/hide associated screen elements. |

#### 6. Retained legacy screen-event callbacks

Existing legacy callbacks, some still wired to historical widgets; not part of current usual workflow.

| Location | Method | Responsibility |
| --- | --- | --- |
| [`L3369`](main.py#L3369) | `w2_back_button_callback()` | Handle the historical w2 back button event; see method body for its exact UI actions. |
| [`L3376`](main.py#L3376) | `w2_abort_button_callback()` | Handle the historical w2 abort button event; see method body for its exact UI actions. |
| [`L3386`](main.py#L3386) | `solenoid_status_test_button_callback()` | Historical W2 relay test: energizes selected relay and starts legacy cycle timer. |
| [`L3393`](main.py#L3393) | `w2_continue_button_callback()` | Handle the historical w2 continue button event; see method body for its exact UI actions. |
| [`L3403`](main.py#L3403) | `w2_continue_confirm_callback()` | Handle the historical w2 continue confirm event; see method body for its exact UI actions. |
| [`L3411`](main.py#L3411) | `w2a_shutdown_button_callback()` | Handle the historical w2a shutdown button event; see method body for its exact UI actions. |
| [`L3418`](main.py#L3418) | `w3_continue_button_callback()` | Handle the historical w3 continue button event; see method body for its exact UI actions. |
| [`L3424`](main.py#L3424) | `w5_turn_on_button_callback()` | Handle the historical w5 turn on button event; see method body for its exact UI actions. |
| [`L3430`](main.py#L3430) | `w5a_power_button_callback()` | Handle the historical w5a power button event; see method body for its exact UI actions. |
| [`L3436`](main.py#L3436) | `turn_on_water_bath_timer_callback()` | Handle the historical turn on water bath timer event; see method body for its exact UI actions. |
| [`L3443`](main.py#L3443) | `w5b_continue_button_callback()` | Handle the historical w5b continue button event; see method body for its exact UI actions. |
| [`L3449`](main.py#L3449) | `w6_abort_button_callback()` | Handle the historical w6 abort button event; see method body for its exact UI actions. |
| [`L3455`](main.py#L3455) | `w6_shutdown_button_callback()` | Handle the historical w6 shutdown button event; see method body for its exact UI actions. |
| [`L3461`](main.py#L3461) | `w6a_back_button_callback()` | Handle the historical w6a back button event; see method body for its exact UI actions. |
| [`L3467`](main.py#L3467) | `w6a_shutdown_button_callback()` | Handle the historical w6a shutdown button event; see method body for its exact UI actions. |
| [`L3473`](main.py#L3473) | `w6_continue_button_callback()` | Handle the historical w6 continue button event; see method body for its exact UI actions. |
| [`L3479`](main.py#L3479) | `w7_continue_button_callback()` | Handle the historical w7 continue button event; see method body for its exact UI actions. |
| [`L3485`](main.py#L3485) | `w8_continue_button_callback()` | Handle the historical w8 continue button event; see method body for its exact UI actions. |
| [`L3491`](main.py#L3491) | `w8_purge_nozzle_button_callback()` | Handle the historical w8 purge nozzle button event; see method body for its exact UI actions. |
| [`L3497`](main.py#L3497) | `w10_yes_button_callback()` | Handle the historical w10 yes button event; see method body for its exact UI actions. |
| [`L3503`](main.py#L3503) | `w10_no_button_callback()` | Handle the historical w10 no button event; see method body for its exact UI actions. |
| [`L3509`](main.py#L3509) | `w11_continue_button_callback()` | Handle the historical w11 continue button event; see method body for its exact UI actions. |
| [`L3515`](main.py#L3515) | `w12_continue_button_callback()` | Handle the historical w12 continue button event; see method body for its exact UI actions. |
| [`L3521`](main.py#L3521) | `w13a_continue_button_callback()` | Handle the historical w13a continue button event; see method body for its exact UI actions. |
| [`L3527`](main.py#L3527) | `w13b_continue_button_callback()` | Handle the historical w13b continue button event; see method body for its exact UI actions. |
| [`L3533`](main.py#L3533) | `w14_continue_button_callback()` | Historical W14 continuation that starts the old powerdown timer; not used in current W13-to-standby path. |

#### 7. Retained administrative/alternative pulse controls

Old Admin and alternate pulse editor retained unchanged; W9 currently shows per-nozzle TIME buttons.

| Location | Method | Responsibility |
| --- | --- | --- |
| [`L3546`](main.py#L3546) | `edit_pulse_durations()` | Retained dialog to edit all three independent durations (the normal W9 Admin button is hidden). |
| [`L3595`](main.py#L3595) | `update_pulse_labels()` | Retained alternate label formatter that writes durations onto GO buttons. |
| [`L3617`](main.py#L3617) | `w9_admin_button_callback()` | Open historical W9c admin screen (not invoked by W9 per-nozzle time controls). |
| [`L3623`](main.py#L3623) | `show_w9b()` | Display the historical W9B screen and its associated widgets. |
| [`L3643`](main.py#L3643) | `hide_w9b()` | Hide the historical W9B widgets and restore/hide associated screen elements. |
| [`L3651`](main.py#L3651) | `show_w9c()` | Display the historical W9C screen and its associated widgets. |
| [`L3680`](main.py#L3680) | `hide_w9c()` | Hide the historical W9C widgets and restore/hide associated screen elements. |
| [`L3708`](main.py#L3708) | `w9b_try_again_button_callback()` | Handle the historical w9b try again button event; see method body for its exact UI actions. |
| [`L3714`](main.py#L3714) | `w9c_blast_sec_scrollbar_callback()` | Handle the historical w9c blast sec scrollbar event; see method body for its exact UI actions. |
| [`L3727`](main.py#L3727) | `w9c_nozzle_t_scrollbar_callback()` | Handle the historical w9c nozzle t scrollbar event; see method body for its exact UI actions. |
| [`L3740`](main.py#L3740) | `w9c_nozzle_psi_scrollbar_callback()` | Handle the historical w9c nozzle psi scrollbar event; see method body for its exact UI actions. |
| [`L3754`](main.py#L3754) | `w9c_vessel_t_scrollbar_callback()` | Handle the historical w9c vessel t scrollbar event; see method body for its exact UI actions. |
| [`L3764`](main.py#L3764) | `w9c_load_startup_sp_button_callback()` | Handle the historical w9c load startup sp button event; see method body for its exact UI actions. |
| [`L3843`](main.py#L3843) | `w9c_save_new_startup_sp_button_callback()` | Handle the historical w9c save new startup sp button event; see method body for its exact UI actions. |
| [`L3855`](main.py#L3855) | `w9c_run_changed_sp_button_callback()` | Handle the historical w9c run changed sp button event; see method body for its exact UI actions. |

#### 8. Legacy timers, monitoring, and shutdown helpers

Historical monitoring, heater/pressure control, elapsed-time labels, and power-down callbacks.

| Location | Method | Responsibility |
| --- | --- | --- |
| [`L3927`](main.py#L3927) | `system_startup_time_update()` | Update retained startup time update logic or display. |
| [`L3937`](main.py#L3937) | `system_startup_final_time()` | Update retained startup final time logic or display. |
| [`L3949`](main.py#L3949) | `system_shutdown_time_update()` | Update retained shutdown time update logic or display. |
| [`L3959`](main.py#L3959) | `system_shutdown_final_time()` | Update retained shutdown final time logic or display. |
| [`L3971`](main.py#L3971) | `system_shutdown_powerdown()` | Historical callback that shuts down the OS and controls old heaters; not used by current standby flow. |
| [`L3987`](main.py#L3987) | `read_nozzle_temperature_C_timer_callback()` | Update legacy nozzle thermocouple samples on timer events. |
| [`L4002`](main.py#L4002) | `read_vessel_temperature_C_timer_callback()` | Update legacy vessel thermocouple samples on timer events. |
| [`L4017`](main.py#L4017) | `set_nozzle_pressure_to_current_setpoint_timer_callback()` | Legacy Alicat pressure setpoint callback (not active in normal startup). |
| [`L4026`](main.py#L4026) | `control_vessel_and_nozzle_vessel_temperature_timer_callback()` | Legacy heater control callback (not enabled in normal startup). |
| [`L4101`](main.py#L4101) | `system_state_time_update()` | Update the legacy system state and related display values. |

#### 9. Stored setpoints and data logging

Legacy file-backed defaults, CSV headers, records, and log numbering.

| Location | Method | Responsibility |
| --- | --- | --- |
| [`L4351`](main.py#L4351) | `_construct_data_logging_filename()` | Build the numbered legacy CSV log filename. |
| [`L4360`](main.py#L4360) | `load_startup_setpoint_vessel_temperature_C()` | Load the legacy setpoint vessel temperature C setting from its stored startup setpoint file. |
| [`L4367`](main.py#L4367) | `save_startup_setpoint_vessel_temperature_C()` | Save the legacy setpoint vessel temperature C startup setpoint. |
| [`L4376`](main.py#L4376) | `load_startup_setpoint_vessel_pressure_PSI()` | Load the legacy setpoint vessel pressure PSI setting from its stored startup setpoint file. |
| [`L4383`](main.py#L4383) | `load_startup_setpoint_nozzle_temperature_C()` | Load the legacy setpoint nozzle temperature C setting from its stored startup setpoint file. |
| [`L4390`](main.py#L4390) | `save_startup_setpoint_nozzle_temperature_C()` | Save the legacy setpoint nozzle temperature C startup setpoint. |
| [`L4399`](main.py#L4399) | `load_startup_setpoint_nozzle_pressure_PSI()` | Load the legacy setpoint nozzle pressure PSI setting from its stored startup setpoint file. |
| [`L4406`](main.py#L4406) | `save_startup_setpoint_nozzle_pressure_PSI()` | Save the legacy setpoint nozzle pressure PSI startup setpoint. |
| [`L4415`](main.py#L4415) | `load_startup_blast_sec()` | Load the legacy blast sec setting from its stored startup setpoint file. |
| [`L4422`](main.py#L4422) | `save_startup_blast_sec()` | Save the legacy blast sec startup setpoint. |
| [`L4431`](main.py#L4431) | `load_pressure_vessel_heater_on_duration_seconds()` | Load the historical pressure vessel heater on duration seconds value from configured storage. |
| [`L4438`](main.py#L4438) | `load_nozzle_vessel_heater_on_duration_seconds()` | Load the historical nozzle vessel heater on duration seconds value from configured storage. |
| [`L4445`](main.py#L4445) | `load_pressure_vessel_heater_seconds_to_wait_after_heating()` | Load the historical pressure vessel heater seconds to wait after heating value from configured storage. |
| [`L4455`](main.py#L4455) | `load_nozzle_vessel_heater_seconds_to_wait_after_heating()` | Load the historical nozzle vessel heater seconds to wait after heating value from configured storage. |
| [`L4465`](main.py#L4465) | `write_header_to_data_logging_file()` | Write header to data logging file for the retained CSV data logging workflow. |
| [`L4498`](main.py#L4498) | `write_column_labels_to_data_logging_file()` | Write column labels to data logging file for the retained CSV data logging workflow. |
| [`L4527`](main.py#L4527) | `write_machine_state_to_data_logging_file()` | Write machine state to data logging file for the retained CSV data logging workflow. |
| [`L4557`](main.py#L4557) | `load_data_logging_file_number()` | Load the historical data logging file number value from configured storage. |
| [`L4568`](main.py#L4568) | `increment_data_logging_filename_number()` | Advance the stored data logging filename number counter. |

#### 10. Legacy sensor and system-readiness utilities

Legacy thermocouple conversions and operating-range/readiness checks.

| Location | Method | Responsibility |
| --- | --- | --- |
| [`L4582`](main.py#L4582) | `get_nozzle_vessel_temperature()` | Read/average the nozzle analog temperature input (legacy routine). |
| [`L4617`](main.py#L4617) | `get_pressure_vessel_temperature()` | Read/average the vessel analog temperature input (legacy routine). |
| [`L4654`](main.py#L4654) | `test_system()` | Evaluate historical sensor/system readiness conditions. |

## Run, autostart, and diagnostics

These commands are run from a **Mac or other computer** on the same network as the BeagleBone. `start.sh` is the launch script; there is **no need to create a second launcher** for each code update.

```bash
# Copy the edited file from your Mac (run from the folder containing main.py).
scp main.py debian@192.168.6.2:/home/debian/pratyush-controller-working/

# Syntax-check before restarting. (Does not verify GPIO behavior.)
ssh debian@192.168.6.2 'python2 -m py_compile /home/debian/pratyush-controller-working/main.py'

# Launch, with previous controller process stopped and actuator loads isolated.
ssh -t debian@192.168.6.2 'cd /home/debian/pratyush-controller-working && bash start.sh'
```

`start.sh` is unchanged by this refactor. It changes into its own directory, pre-exports Linux GPIO 51/117/60 and waits for writable sysfs nodes, sets `DISPLAY` (default `:0.0`), then executes `/usr/bin/python2 main.py`. It assumes a graphical BeagleBone desktop session and its existing GPIO permissions.

**Autostart:** On systems configured in earlier deployment, the LXQt desktop's external file `~/.config/autostart/pratyush-controller.desktop` runs `/bin/bash /home/debian/pratyush-controller-working/start.sh`. That `.desktop` file is **not in this ZIP**. Verify it on the device rather than assuming a fresh installation autostarts. Ensure any older GUI autostart entry remains disabled to avoid competing GPIO controllers.

```bash
ssh debian@192.168.6.2
cat ~/.config/autostart/pratyush-controller.desktop
pgrep -af 'python2.*main.py'
# After isolating hardware and commanding OFF, stop a known process by its PID:
# kill <PID>
```

**Power-cycle smoke test, with solenoid loads and pneumatic supplies isolated:** New boot opens Welcome; startup images unlock controls; independent TIME selections work; a 1-second animation fills; commanded output turns OFF after selected interval; shutdown follows title and five images to dark standby; tap returns to Welcome, but controls only unlock after completing startup. Do not perform this test with pressurized equipment connected.

## Legacy features and hardware caution

The repository is an **evolved 2024 legacy application**. Several old W2–W15 screens, pressure/temperature/Alicat routines, CSV logging helpers, and timer callbacks remain in `main.py`. Their presence **does not mean they run** in the current normal operator flow. Some are still connected as Qt callbacks or available through methods, so **do not enable old screens/timers** without a separate review.

- Only `setup_gpio()` is invoked from `initialize_system()` in the current startup path; analog setup is commented out.
- The old W9 Admin control is hidden in `show_w9()`; the displayed TIME buttons use `edit_nozzle_duration()` instead.
- The historical `system_shutdown_powerdown()` includes heater controls and an OS shutdown command. The normal shutdown slideshow ends in **software standby**, not that routine.
- Pressure/temperature interlocks are **not reinstated** by this refactor. The shutdown latch and software QTimer are application logic, not hardware safety certification.
- The startup/shutdown graphics may show legacy equipment-specific procedural steps and numerical settings; follow your current approved operating procedures.

## Refactor verification

- All **155** `IceCreamGUI` method names are present exactly once and their **full source bodies match** the uploaded original.
- All module-level executable statements and functions (imports, pin mapping references, `initialize_system`, `main`, and entrypoint) have unchanged Python abstract syntax trees.
- All class methods have unchanged Python abstract syntax trees. Only their **order in the class** changed; documentation comments were inserted *outside* each method body.
- The refactored `main.py` passed Python 3 grammar parsing/compilation (for static checking) and a Python 2 grammar parse could not be confirmed in this environment.
- **Not run on the BeagleBone in this environment:** There is no connected GPIO hardware, Python 2/PyQt4/Adafruit_BBIO runtime, or touchscreen for end-to-end validation. The **existing working release should remain backed up**, and the refactored file should be smoke-tested with actuator loads isolated before deployment.

No GPIO/relay pin assignment, Qt signal connection, timer duration, UI geometry, image filename, `start.sh`, or operating behavior was intentionally altered.
