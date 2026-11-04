# type: ignore
# =============================================================================
# Ice Cream Machine / Pratyush BeagleBone touchscreen controller
# =============================================================================
# Python 2 + PyQt4; GPIO via Adafruit_BBIO on BeagleBone Black.
#
# CURRENT OPERATOR FLOW (details and all function locations: README.md):
#   BeagleBone boot -> main() -> IceCreamGUI.__init__() / initUI()
#   Welcome (W1) -> Startup Instructions -> W4 (five startup images)
#   -> W9 (three independently timed solenoids) -> W9a (dispensing)
#   -> Shutdown Instructions -> W13 (five images) -> dark standby
#   -> tap to return to Welcome. A fresh process opens Welcome, not standby.
#
#
# Historical authors: Pratyush Sudhakar, Bruce McKee.
# =============================================================================

import sys
import serial  # Required for RS-232 communication
import math
import random
import decimal
import time
import os

# Importing PyQt4 modules
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt, QPropertyAnimation

# Importing Adafruit GPIO modules
import Adafruit_BBIO.GPIO as GPIO
import Adafruit_BBIO.ADC as ADC
import Adafruit_GPIO.I2C as I2C

# Importing the system constants
from constants import *
from system_constants import *
from directory_constants import *

# =========================================================================================
# Global Constants
# =========================================================================================
PRESSURE_VESSEL_HEATER_RELAY = Pressure_Vessel_Heater_Relay_Grove_Cape_V2_GPIO_111
NOZZLE_VESSEL_HEATER_RELAY = Nozzle_Vessel_Heater_Relay_Grove_Cape_V2_GPIO_03
NOZZLE_SOLENOID1_RELAY = SOLENOID_NUMBER_PIN[1]
NOZZLE_SOLENOID2_RELAY = SOLENOID_NUMBER_PIN[2]
NOZZLE_SOLENOID3_RELAY = SOLENOID_NUMBER_PIN[3]

PRESSURE_VESSEL_THERMOCOUPLE_AIN = "P9_39"  # Jack labeled AIN0 on the Grove Cape V2
NOZZLE_VESSEL_THERMOCOUPLE_AIN = "P9_37"  # Jack labeled AIN2 on the Grove Cape V2

# =========================================================================================
# Setup Functions
# =========================================================================================


# def setup_gpio():
#     """Initialize GPIO pins as outputs."""
#     # GPIO.setup(PRESSURE_VESSEL_HEATER_RELAY, GPIO.OUT)
#     # GPIO.setup(NOZZLE_VESSEL_HEATER_RELAY, GPIO.OUT)
#     # GPIO.setup(NOZZLE_SOLENOID1_RELAY, GPIO.OUT)
#     # GPIO.setup(NOZZLE_SOLENOID2_RELAY, GPIO.OUT)
#     # GPIO.setup(NOZZLE_SOLENOID3_RELAY, GPIO.OUT)
#     # ADC.setup()

#     for pin in (
#         NOZZLE_SOLENOID1_RELAY,
#         NOZZLE_SOLENOID2_RELAY,
#         NOZZLE_SOLENOID3_RELAY
#     ):
#         GPIO.setup(pin, GPIO.OUT)
#         GPIO.output(pin, GPIO.LOW)

def setup_gpio():
    """Initialize the three solenoid GPIOs only."""

    pins = [
        NOZZLE_SOLENOID1_RELAY,
        NOZZLE_SOLENOID2_RELAY,
        NOZZLE_SOLENOID3_RELAY
    ]

    for pin in pins:
        print("Initializing GPIO pin: {}".format(pin))
        sys.stdout.flush()

        try:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)

            print("SUCCESS: {} initialized".format(pin))

        except Exception as e:
            print("FAILED: {} - {}".format(pin, e))
            sys.stdout.flush()
            raise

def setup_analog_inputs():
    """Initialize Analog Inputs for the thermocouples."""
    # Pressure Vessel Thermocouple setup
    global Pressure_Vessel_Thermocouple_Grove_Cape_V2_AIN_0
    Pressure_Vessel_Thermocouple_Grove_Cape_V2_AIN_0 = PRESSURE_VESSEL_THERMOCOUPLE_AIN

    # Nozzle Vessel Thermocouple setup
    global Nozzle_Vessel_Thermocouple_Grove_Cape_V2_AIN_2
    Nozzle_Vessel_Thermocouple_Grove_Cape_V2_AIN_2 = NOZZLE_VESSEL_THERMOCOUPLE_AIN


def initialize_system():
    setup_gpio()
    #setup_analog_inputs()


def set_gpio(pin, state):
    """Set the specified GPIO pin to the given state."""
    GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)


# Device control functions
def set_nozzle_solenoid(*args):
    if len(args) == 2:
        solenoid_number, state = args
        nozzle_pin = SOLENOID_NUMBER_PIN.get(solenoid_number)
        set_gpio(nozzle_pin, state)
    elif len(args) == 1:
        state = args[0]
        print("setting the state to " + str(state))
        for solenoid_number in SOLENOID_NUMBER_PIN:
            nozzle_pin = SOLENOID_NUMBER_PIN.get(solenoid_number)
            set_gpio(nozzle_pin, state)


def set_nozzle_vessel_heater(state):
    set_gpio(NOZZLE_VESSEL_HEATER_PIN, state)


def set_pressure_vessel_heater(state):
    set_gpio(PRESSURE_VESSEL_HEATER_PIN, state)


def read_vessel_pressure():
    """
    Reads the vessel pressure using the ADC121 sensor connected via I2C.

    The function configures the ADC121 sensor, reads the raw ADC value,
    converts it to a voltage, and then calculates the corresponding pressure.

    Returns:
        float: The calculated pressure in appropriate units (e.g., kPa, psi).
    """
    ADDR_ADC121 = 0x50

    REG_ADDR_RESULT = 0x00
    REG_ADDR_ALERT = 0x01
    REG_ADDR_CONFIG = 0x02
    REG_ADDR_LIMITL = 0x03
    REG_ADDR_LIMITH = 0x04
    REG_ADDR_HYST = 0x05
    REG_ADDR_CONVL = 0x06
    REG_ADDR_CONVH = 0x07

    V_REF = 3.00
    adc = I2C.get_i2c_device(0x50, busnum=2)

    try:
        adc.write8(REG_ADDR_CONFIG, 0x20)
        data_list = adc.readList(REG_ADDR_RESULT, 2)
        data = ((data_list[0] & 0x0F) << 8 | data_list[1]) & 0xFFF
        volts = (data * V_REF * 2) / 4096
        pressure = volts * (2000.0 / 5.0)
    except:
        # print("Error")
        return 0
    return pressure


def get_alicat_pressure_code(pressure):
    """
    Generates command strings for an Alicat pressure controller based on a specified pressure value.

    The function maps integer pressure values to specific command strings required by the Alicat controller.
    These commands include two essential termination characters: the ASCII line feed (\n) and carriage return (\r)
    to denote the end of the command. The function returns a command string which contains a minimum of four
    characters, followed by the termination sequence. If a pressure value is not listed, the function returns an empty string.

    The Alicat device accepts pressures up to 3000 psi, but this function supports up to 2000 psi in anticipation
    of future design limits on the release valve pressure.

    Args:
        pressure (int): The pressure value in PSI (Pounds per Square Inch), must be one of the predefined
                        set values within the range 0 to 2000 psi.

    Returns:
        str: The command string formatted for the Alicat controller. Returns an empty string if the pressure
             value is not supported.

    Example:
        >>> get_alicat_pressure_code(100)
        'A$$W24=2133\n\r'

    References:
        - PySerial Introduction: https://pyserial.readthedocs.io/en/latest/shortintro.html
        - Python String Documentation: https://docs.python.org/2.0/ref/strings.html

    Note:
        For zero pressure, the controller should receive the command 'A$$W24=0000\n\r'.
    """
    command = pressure_codes.get(pressure, "")
    if command:
        command += "\n\r"
    return command


def set_alicat_pressure(pressure_psi):
    """
    Sets the pressure on an Alicat pressure controller by sending the appropriate
    command over a serial interface.

    Args:
        pressure_psi (float): The desired pressure to set in PSI.

    Returns:
        bool: True if the command was successfully sent, False otherwise.
    """
    pressure_code = get_alicat_pressure_code(pressure_psi)

    ser = serial.Serial(
        port="/dev/ttyO4",
        baudrate=19200,
        bytesize=serial.EIGHTBITS,
        stopbits=serial.STOPBITS_ONE,
        xonxoff=False,
        dsrdtr=False,
        parity=serial.PARITY_NONE,
        timeout=0.5,
    )

    if ser.isOpen():
        ser.write(pressure_code)
        ser.close()
        return True
    return False


def read_alicat_downstream_pressure():
    """
    Reads the downstream pressure value from an Alicat device using serial communication.

    This function initializes a serial port connection according to the Alicat device's specifications.
    It sends a command to the device and reads the response to extract the downstream pressure.
    The function returns the pressure as an integer value. If no valid response is received,
    it defaults the pressure to zero.

    Returns:
        int: The downstream pressure read from the Alicat device, or zero if no valid data is received.
    """
    # Initialize serial connection with the Alicat device
    ser = serial.Serial(
        port="/dev/ttyO4",  # Serial port for the device
        baudrate=19200,  # Communication speed
        bytesize=serial.EIGHTBITS,  # Number of data bits
        stopbits=serial.STOPBITS_ONE,  # Number of stop bits
        parity=serial.PARITY_NONE,  # No parity check
        xonxoff=False,  # Disable software flow control
        dsrdtr=False,  # Disable hardware flow control
        timeout=0.5,  # Read timeout in seconds
    )
    # print("Port for RS-232 I/O is: " + ser.name)

    if ser.isOpen():
        ser.write("A\r")
        alicat_response = ser.readline()
        # print("Alicat responded with downstream pressure string %s" % alicat_response)

        # Extract the pressure reading from the response
        response_pressure_string = alicat_response[5:9]
        response_pressure_integer = int(response_pressure_string) if response_pressure_string else 0

    ser.close()
    return response_pressure_integer


# Set up the GUI as a Python class:
# =============================================================================
# IceCreamGUI -- Qt widget implementation
# The sections below are organized by operator workflow first, with historical
# functions grouped afterward. All method bodies are copied verbatim.
# =============================================================================
class IceCreamGUI(QtGui.QWidget):

    # =========================================================================
    # 1. Construction, settings, UI wiring, and scaling
    # Startup objects, Qt signals, timing, legacy initialization, and the 480-by-272 scaling pass.
    # =========================================================================

    # Build the complete widget tree, initialize GPIO-facing software state, create timers and animations, then call initUI. Statement order inside is unchanged.
    def __init__(self):
        super(IceCreamGUI, self).__init__()
        self.solenoid_timer_machine_error = 650  # difference b/w actual time vs expected time to turn on and off
        self.beaglebone_default_directory = BEAGLEBONE_DEFAULT_DIRECTORY
        self.startup_setpoint_directory = STARTUP_SETPOINT_DIRECTORY
        self.data_logging_directory = DATA_LOGGING_DIRECTORY

        self._set_variables()
        self.pulse_durations = {
            1: 1,
            2: 1,
            3: 1
        }

        # Timer to automatically stop an active solenoid pulse
        self.solenoid_cutoff_timer = QtCore.QTimer(self)
        self.solenoid_cutoff_timer.setSingleShot(True)

        # When the timer expires, stop dispensing
        self.solenoid_cutoff_timer.timeout.connect(self.hide_w9a)
        self.shutdown_latched = False

        #self.startup_file_data_logging_file_number = STARTUP_FILE_DATA_LOGGING_FILE_NUMBER
        #self.data_logging_file_name = DATA_LOGGING_FILE_NAME_TEMPLATE
        #self.data_logging_file_number = self.load_data_logging_file_number()
        #self.data_logging_file_name = self._construct_data_logging_filename()
        #self.increment_data_logging_filename_number()

        # Turn off the relays (sometimes they come up in an "on" state)
        set_nozzle_solenoid(1, False)
        set_nozzle_solenoid(2, False)
        set_nozzle_solenoid(3, False)
        # set_nozzle_vessel_heater(False)
        # set_pressure_vessel_heater(False)

        #
        # Load setpoints from the STARTUP_SETPOINTS directory, and adjust the temperature operating ranges based on these values
        # self.load_startup_setpoint_vessel_temperature_C()
        # self.load_startup_setpoint_vessel_pressure_PSI()
        # self.load_startup_setpoint_nozzle_temperature_C()
        # self.load_startup_setpoint_nozzle_pressure_PSI()
        # self.load_startup_blast_sec()

        self.initialize_setpoints()
        self.adjust_operating_ranges()
        self.initialize_scrollbars()
        self.initialize_system_state()
        self.initialize_control_variables()
       # self.initialize_logging_and_timing_controls()

        #
        # *****************************************
        # ***   Window Image Background Label   ***
        # *****************************************
        # First create a label, which will be used to display backgrounds - the widgets
        # will appear over this background.  Have to create the label, THEN the widgets, else
        # the label will hide the widgets.
        #
        # If loading the background image from a file, note that the file must be a .png file
        #
        self.label_background = QtGui.QLabel(self)

        self.pixmap = QtGui.QPixmap("/home/debian/controller/window-background-images/splash-screen-corrected.png")

        self.label_background.setPixmap(self.pixmap)

        #
        # *******************************************************************************************
        #
        #  Create Timers used to:
        #               -Update title labels on System Startup and System Shutdown screen title labels
        #               -Update progress bars, progress bar labels, and setpoint scrollbar labels
        #               -Log system state to an external file
        #
        # *******************************************************************************************

        #
        # *******************************************************************************************
        # ***   Create a timer that executes every second, and whose callback will
        # ***   continually update the w6-system-startup screen text label
        # *******************************************************************************************

        self.system_startup_timer = QtCore.QTimer(self)
        self.system_startup_timer.setInterval(1000)  # Have it execute every second

        #
        # *******************************************************************************************
        # ***   Create a timer that executes every second, and whose callback will
        # ***   continually update the w11-shutdown-in-progress screen text label
        # *******************************************************************************************
        self.system_shutdown_timer = QtCore.QTimer(self)
        self.system_shutdown_timer.setInterval(1000)  # Have it execute every second

        #
        # *******************************************************************************************
        # ***   Create a timer that starts at system startup & executes every second, and whose callback will
        # ***   continually update progress bars; progress bar labels; and setpoint scrollbar labels;
        # *******************************************************************************************
        self.system_state_timer = QtCore.QTimer(self)
        self.system_state_timer.setInterval(1000)  # Have it execute every second

        #
        # *******************************************************************************************
        # ***   Create a timer that cycles the solenoid relay
        # *******************************************************************************************
        self.cycle_nozzle_solenoid_timer = QtCore.QTimer(self)
        self.cycle_nozzle_solenoid_timer.setInterval(1000)  # Have it execute every second
        self.cycle_nozzle_solenoid_timer.setSingleShot(True)

        #
        # *******************************************************************************************
        # ***   Create a timer that TURNS ON the water bath
        # *******************************************************************************************
        #
        self.turn_on_water_bath_timer = QtCore.QTimer(self)
        # Have it execute after 10 seconds
        self.turn_on_water_bath_timer.setInterval(10000)
        self.turn_on_water_bath_timer.setSingleShot(True)

        # *******************************************************************************************
        # ***   Create a timer that SETS the nozzle pressure controller
        # *******************************************************************************************
        self.set_nozzle_pressure_to_current_setpoint_timer = QtCore.QTimer(self)
        self.set_nozzle_pressure_to_current_setpoint_timer.setInterval(100)  # Have it execute after 0.1 seconds
        self.set_nozzle_pressure_to_current_setpoint_timer.setSingleShot(True)

        #
        # *******************************************************************************************
        # ***   Create a timer that controls vessel and nozzle vessel temperature
        # *******************************************************************************************
        self.control_vessel_and_nozzle_vessel_temperature_timer = QtCore.QTimer(self)
        self.control_vessel_and_nozzle_vessel_temperature_timer.setInterval(1000)  # Have it execute every second

        # #
        # #*******************************************************************************************
        # #***   Create a timer that turns on the nozzle vessel heater for n seconds
        # #*******************************************************************************************
        # self.heat_nozzle_vessel_timer = QtCore.QTimer(self)

        # #
        # #*******************************************************************************************
        # #***   Create a timer that turns on the pressure vessel heater for n seconds
        # #*******************************************************************************************
        # self.heat_pressure_vessel_timer = QtCore.QTimer(self)

        #
        # *******************************************************************************************
        # ***   Create timerS FOR reading the vessel and nozzle temperatures
        # *******************************************************************************************
        self.read_vessel_temperature_C_timer = QtCore.QTimer(self)
        self.read_vessel_temperature_C_timer.setInterval(40)  # It will repeat every 40 milliseconds

        self.read_nozzle_temperature_C_timer = QtCore.QTimer(self)
        self.read_nozzle_temperature_C_timer.setInterval(40)  # It will repeat every 40 milliseconds

        #
        # *******************************************************************************************
        # ***   Create a timer for system shutdown and poweroff - shuts down the beaglebone
        # *******************************************************************************************
        self.system_shutdown_timer_powerdown = QtCore.QTimer(self)
        self.system_shutdown_timer_powerdown.setInterval(5000)  # It will shut down the system after five seconds
        self.system_shutdown_timer_powerdown.setSingleShot(True)

        # #
        # #*******************************************************************************************
        # #***   Create a timer for system shutdown and poweroff - shuts down the beaglebone
        # #*******************************************************************************************
        # self.system_shutdown_timer_powerdown = QtCore.QTimer(self)
        # self.system_shutdown_timer_powerdown.setInterval(5000) #It will shut down the system after five seconds
        # self.system_shutdown_timer_powerdown.setSingleShot(True)

        # self.connect( self.system_startup_timer, SIGNAL("timeout()"), self.system_startup_time_update)

        # self.system_shutdown_timer = QTimer(self)
        # self.system_shutdown_timer.setInterval(1000) #Have it execute every second
        # self.connect( self.system_shutdown_timer, SIGNAL("timeout()"), self.system_startup_time_update)

        # *****************************************************
        # Create widgets for window w1-start-splash-screen
        # *****************************************************
        # The Continue Button moves the app to the next screen
        #
        self.w1_continue_button = QtGui.QPushButton("Continue", self)
        self.w1_continue_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w1_continue_button.resize(195, 25)
        self.w1_continue_button.move(273, 235)
        self.w1_continue_button.hide()

        self.pixmap = QtGui.QPixmap(IMAGES_FOLDER + "/splash-screen-corrected.png")
        self.label_background.setPixmap(self.pixmap)

        #
        # ****************************************************************************************************
        # Create the controller subsystem status widgets separately, as they are used in multiple windows
        # ****************************************************************************************************
        #

        # Create Labels & Checkboxes in pairs for the 3 solenoids
        # (3 solenoids, so 3 labels, and 3 buttons)

        # Label for the Solenoids Relays Status
        self.solenoid1_label, self.solenoid1_checkbox, self.solenoid1_test_button = self.create_solenoid_relay_ui(1, 96)
        self.solenoid2_label, self.solenoid2_checkbox, self.solenoid2_test_button = self.create_solenoid_relay_ui(2, 116)
        self.solenoid3_label, self.solenoid3_checkbox, self.solenoid3_test_button = self.create_solenoid_relay_ui(3, 136)

        #
        # ***************************************************************************
        # ***   Create widgets for window confirmation screen                     ***
        # ***************************************************************************
        #
        self.label_confirmation_screen_title = QtGui.QLabel(self)
        self.label_confirmation_screen_title.setStyleSheet("font-size: 15pt; font-family: Lucida Sans Typewriter; font-weight: bold")
        self.label_confirmation_screen_title.resize(465, 31)
        self.label_confirmation_screen_title.move(30, 26)
        self.label_confirmation_screen_title.setWordWrap(True)
        self.label_confirmation_screen_title.hide()

        #
        # ***************************************************************************
        # ***   Create widgets for window w2-check-subsystems                     ***
        # ***************************************************************************
        #
        # Label on Checking Control Subsystems Window
        self.w2_screen_title_label = QtGui.QLabel(self)
        self.w2_screen_title_label.setText("Checking Controller Subsystems...")
        self.w2_screen_title_label.setStyleSheet("font-size: 15pt; font-family: Lucida Sans Typewriter; font-weight: bold")
        self.w2_screen_title_label.resize(465, 31)
        self.w2_screen_title_label.move(30, 26)
        self.w2_screen_title_label.setWordWrap(True)
        self.w2_screen_title_label.hide()

        #
        # Confirmation Modal No (back) button
        #
        self.w2_back_button = QtGui.QPushButton("< Back", self)
        self.w2_back_button.setStyleSheet(button_white_stylesheet)
        self.w2_back_button.resize(75, 25)
        self.w2_back_button.move(180, 235)
        self.w2_back_button.hide()

        #
        # The Abort Button moves to the w2a screen
        #
        self.w2_abort_button = QtGui.QPushButton("Abort", self)
        self.w2_abort_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(255,255,30); color:rgb(51,51,51)"
        )
        self.w2_abort_button.resize(75, 25)
        self.w2_abort_button.move(180, 235)
        self.w2_abort_button.hide()

        #
        # The Continue Button moves the app to the next screen
        #
        self.w2_continue_button = QtGui.QPushButton("Continue", self)
        self.w2_continue_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w2_continue_button.resize(195, 25)
        self.w2_continue_button.move(273, 235)
        self.w2_continue_button.hide()

        self.w2_continue_confirm_button = QtGui.QPushButton("Continue", self)
        self.w2_continue_confirm_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w2_continue_confirm_button.resize(195, 25)
        self.w2_continue_confirm_button.move(273, 235)
        self.w2_continue_confirm_button.hide()

        # Note:  calling the "hide" routine here does not work - the widgets show up anyway - have
        # to hide them right after each is created.

        #
        # ***************************************************************************
        # ***   Create widgets for window w2a-subsystems-offline                  ***
        # ***************************************************************************
        # Label on Checking Control Subsystems Window
        self.w2a_screen_title = QtGui.QLabel(self)
        self.w2a_screen_title.setText("<center>Controller Subsystem(s) are Off-Line!<br>Shut down & Contact Project Engineer</center>")
        self.w2a_screen_title.setStyleSheet("font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; background-color:rgb(255,255,30)")
        self.w2a_screen_title.resize(400, 37)
        self.w2a_screen_title.move(40, 20)
        self.w2a_screen_title.setWordWrap(True)
        self.w2a_screen_title.hide()

        #
        # The Shutdown  Button moves the app to the next screen
        #
        self.w2a_shutdown_button = QtGui.QPushButton("**Shutdown**", self)
        self.w2a_shutdown_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w2a_shutdown_button.resize(195, 25)
        self.w2a_shutdown_button.move(273, 235)
        self.w2a_shutdown_button.hide()

        #
        # ***************************************************************************
        # ***   Create widgets for window w2b-controller-shutdown                 ***
        # ***************************************************************************
        self.w2b_screen_title = QtGui.QLabel(self)
        self.w2b_screen_title.setText("<center>Wait Until Screen Darkens<br>Then<br> Turn Off Power</center>")
        self.w2b_screen_title.setStyleSheet("font-size: 16pt; font-family: Lucida Sans Typewriter; font-weight: bold; background-color:rgb(255,255,30)")
        self.w2b_screen_title.resize(400, 75)
        self.w2b_screen_title.move(40, 60)
        self.w2b_screen_title.setWordWrap(True)
        self.w2b_screen_title.hide()

        # Label on Controller Shutdown Screen
        self.w2b_screen_message = QtGui.QLabel(self)
        self.w2b_screen_message.setText("<center>Shutting Down Controller...</center>")
        self.w2b_screen_message.setStyleSheet("font-size: 16pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic")
        self.w2b_screen_message.resize(400, 125)
        self.w2b_screen_message.move(40, 105)
        self.w2b_screen_message.setWordWrap(True)
        self.w2b_screen_message.hide()

        #
        # *********************************************************************************************
        # Create w3-subsystems-online screen -  the System Screen Text, Progress Bars, and Checkboxes
        # *********************************************************************************************
        #
        # Label on Checking Control Subsystems Window
        self.w3_screen_title_label = QtGui.QLabel(self)
        self.w3_screen_title_label.setText("All Controller Subsystems Online!")
        self.w3_screen_title_label.setStyleSheet("font-size: 15pt; font-family: Lucida Sans Typewriter; font-weight: bold")
        self.w3_screen_title_label.resize(446, 31)
        self.w3_screen_title_label.move(30, 26)
        self.w3_screen_title_label.setWordWrap(True)
        self.w3_screen_title_label.hide()

        #
        # The Continue Button moves the app to the next screen
        self.w3_continue_button = QtGui.QPushButton("Continue", self)
        self.w3_continue_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w3_continue_button.resize(195, 25)
        self.w3_continue_button.move(273, 235)
        self.w3_continue_button.hide()

        # *********************************************************************************************
        # Create w4-open-co2-tank-valve-screen -
        # *********************************************************************************************

        self.w4_continue_button = QtGui.QPushButton("Continue", self)
        self.w4_continue_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w4_continue_button.resize(140, 25)
        self.w4_continue_button.move(330, 240)
        self.w4_continue_button.hide()


        # BACK button for startup instructions
        self.w4_back_button = QtGui.QPushButton("Back", self)

        self.w4_back_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter;"
            "font-weight: bold; font-style: italic;"
            "background-color:rgb(154,218,58);"
            "color:rgb(51,51,51)"
        )

        self.w4_back_button.resize(100, 25)
        self.w4_back_button.move(190, 240)
        self.w4_back_button.hide()


        # *********************************************************************************************
        # Create w5-open-air-pressure-valve
        # *********************************************************************************************
        self.w5_turn_on_button = QtGui.QPushButton("Turn On", self)
        self.w5_turn_on_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w5_turn_on_button.resize(195, 25)
        self.w5_turn_on_button.move(273, 235)
        self.w5_turn_on_button.hide()

        # *********************************************************************************************
        # Create w5a-turn-air-regulator-knob
        # *********************************************************************************************
        self.w5a_label_title = QtGui.QLabel(self)
        self.w5a_label_title.setText("In Stand By...")
        self.w5a_label_title.setStyleSheet("font-size: 23pt; font-family: Lucida Sans Typewriter; font-weight: bold")
        self.w5a_label_title.resize(446, 31)
        self.w5a_label_title.move(50, 40)
        self.w5a_label_title.setWordWrap(True)
        self.w5a_label_title.hide()
        self.w5a_power_button = QtGui.QPushButton("Bypass Standby", self)
        self.w5a_power_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w5a_power_button.resize(200, 31)
        self.w5a_power_button.move(166, 100)
        self.w5a_power_button.hide()

        # *********************************************************************************************
        # Create w5b-set-air-regulator-to-85psi
        # *********************************************************************************************

        self.w5b_continue_button = QtGui.QPushButton("Continue", self)
        self.w5b_continue_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w5b_continue_button.resize(195, 25)
        self.w5b_continue_button.move(273, 235)
        self.w5b_continue_button.hide()

        #
        # **************************************************************************************
        # Create the System Screen Text, Progress Bars, and Checkboxes - used by many screens
        # **************************************************************************************
        #
        # Now create a set of labels to be used as the screen title
        # and the progress bar labels - hide them for now

        # self.operatingRange_vessel_temperature_C =  ( 33,   38)
        # self.operatingRange_vessel_pressure_PSI =  (1050, 1300)
        # self.operatingRange_nozzle_temperature_C = (  22,   26)
        # self.operatingRange_vessel_pressure_PSI = ( 1050, 1300)
        # self.operatingRange_nozzle_pressure_PSI = (  800, 1300)
        # self.current_vessel_temperature_C = 0
        # self.current_vessel_pressure_PSI= 0
        # self.current_nozzle_temperature_C = 0
        # self.current_nozzle_pressure_PSI = 0
        #
        # Label on Vessel pressure progress bar
        self.vessel_psi_text_label = QtGui.QLabel(self)
        new_text = "Vessel PSI =    %4i, min = %4i [OpRng= %4i to %4i]" % (
            self.current_vessel_pressure_PSI,
            self.setpoint_current_vessel_pressure_PSI,
            self.operatingRange_vessel_pressure_PSI[0],
            self.operatingRange_vessel_pressure_PSI[1],
        )
        self.vessel_psi_text_label.setText(new_text)
        self.vessel_psi_text_label.setAlignment(QtCore.Qt.AlignLeft)
        self.vessel_psi_text_label.setStyleSheet("font-size: 10pt; font-family: Lucida Sans Typewriter; font-weight: bold")
        self.vessel_psi_text_label.resize(460, 20)
        self.vessel_psi_text_label.move(15, 60)
        self.vessel_psi_text_label.hide()
        #
        # Label on Vessel Temperature progress bar
        self.vessel_temp_C_text_label = QtGui.QLabel(self)
        self.degree_sign = "\N{DEGREE SIGN}"
        new_text = (
            "Vessel  "
            + self.degree_sign
            + "C =   %4.1f,  sp = %4.1f [OpRng= %4.1f to %4.1f]"
            % (
                self.current_vessel_temperature_C,
                self.setpoint_current_vessel_temperature_C,
                self.operatingRange_vessel_temperature_C[0],
                self.operatingRange_vessel_temperature_C[1],
            )
        )
        self.vessel_temp_C_text_label.setText(new_text)
        self.vessel_temp_C_text_label.setAlignment(QtCore.Qt.AlignLeft)
        self.vessel_temp_C_text_label.setStyleSheet("font-size: 10pt; font-family: Lucida Sans Typewriter; font-weight: bold")
        self.vessel_temp_C_text_label.resize(460, 20)
        self.vessel_temp_C_text_label.move(15, 105)
        self.vessel_temp_C_text_label.hide()

        #
        # Label used to indicatet that the vessel heater is on
        self.vessel_heater_on_indicator_label = QtGui.QLabel(self)
        self.vessel_heater_on_indicator_label.setText("*")
        self.vessel_heater_on_indicator_label.setStyleSheet(label_heating_stylesheet)
        self.vessel_heater_on_indicator_label.resize(10, 15)
        self.vessel_heater_on_indicator_label.move(28, 125)
        self.vessel_heater_on_indicator_label.hide()
        # self.vessel_temp_C_progressbar.setGeometry(40,125,280,15)

        #
        # Label on Nozzle pressure progress bar
        # self.nozzle_psi_text_label = QtGui.QLabel(self)
        # new_text = "Nozzle PSI = %4i  sp = %4i  [OpRng= %4i to %4i]" % (
        #     self.current_nozzle_downstream_pressure_PSI,
        #     self.setpoint_current_nozzle_pressure_PSI,
        #     self.operatingRange_nozzle_pressure_PSI[0],
        #     self.operatingRange_nozzle_pressure_PSI[1],
        # )

        # self.nozzle_psi_text_label.setText(new_text)
        # Nozzle pressure monitoring disabled
        self.nozzle_psi_text_label = QtGui.QLabel(self)
        self.nozzle_psi_text_label.setText(
            "Nozzle pressure monitoring disabled"
        )

        
        self.nozzle_psi_text_label.setAlignment(QtCore.Qt.AlignLeft)
        self.nozzle_psi_text_label.setStyleSheet("font-size: 10pt; font-family: Lucida Sans Typewriter; font-weight: bold")
        self.nozzle_psi_text_label.resize(460, 20)
        self.nozzle_psi_text_label.move(15, 145)
        self.nozzle_psi_text_label.hide()

        # Label on Nozzle Temperature progress bar
        self.nozzle_temp_C_text_label = QtGui.QLabel(self)
        new_text = (
            "Nozzle  "
            + self.degree_sign
            + "C =  %4.1f, sp = %4.1f, [OpRng= %4.1f to %4.1f]"
            % (
                self.current_nozzle_temperature_C,
                self.setpoint_current_nozzle_temperature_C,
                self.operatingRange_nozzle_temperature_C[0],
                self.operatingRange_nozzle_temperature_C[1],
            )
        )
        self.nozzle_temp_C_text_label.setText(new_text)
        self.nozzle_temp_C_text_label.setAlignment(QtCore.Qt.AlignLeft)
        self.nozzle_temp_C_text_label.setStyleSheet("font-size: 10pt; font-family: Lucida Sans Typewriter; font-weight: bold")
        self.nozzle_temp_C_text_label.resize(460, 20)
        self.nozzle_temp_C_text_label.move(15, 185)
        self.nozzle_temp_C_text_label.hide()

        #
        # Label used to indicatet that the nozzle heater is on
        self.nozzle_heater_on_indicator_label = QtGui.QLabel(self)
        self.nozzle_heater_on_indicator_label.setText("*")
        self.nozzle_heater_on_indicator_label.setStyleSheet(label_heating_stylesheet)
        self.nozzle_heater_on_indicator_label.resize(10, 15)
        self.nozzle_heater_on_indicator_label.move(28, 205)
        self.nozzle_heater_on_indicator_label.hide()
        #       self.nozzle_temp_C_progressbar.setGeometry(40,205,280,15)

        #
        # Now create progress bars

        #
        # progress bar for vessel pressure
        self.vessel_pressure_PSI_progressbar = QtGui.QProgressBar(self)
        self.vessel_pressure_PSI_progressbar.setGeometry(40, 80, 280, 15)
        self.vessel_pressure_PSI_progressbar.setMinimum(0)
        self.vessel_pressure_PSI_progressbar.setMaximum(2000)

        self.vessel_pressure_PSI_progressbar.setTextVisible(False)
        self.vessel_pressure_PSI_progressbar.setStyleSheet(progressbar_blue_stylesheet)

        self.vessel_pressure_PSI_progressbar.setValue(0)
        self.vessel_pressure_PSI_progressbar.hide()

        #
        # progress bar for vessel temperature
        self.vessel_temp_C_progressbar = QtGui.QProgressBar(self)
        self.vessel_temp_C_progressbar.setGeometry(40, 125, 280, 15)
        self.vessel_temp_C_progressbar.setMinimum(10)
        self.vessel_temp_C_progressbar.setMaximum(50)

        self.vessel_temp_C_progressbar.setTextVisible(False)
        self.vessel_temp_C_progressbar.setStyleSheet(progressbar_red_stylesheet)

        self.vessel_temp_C_progressbar.setValue(10)
        self.vessel_temp_C_progressbar.hide()

        #
        # Progress bar for nozzle pressure
        self.nozzle_pressure_PSI_progressbar = QtGui.QProgressBar(self)
        self.nozzle_pressure_PSI_progressbar.setGeometry(40, 165, 280, 15)
        self.nozzle_pressure_PSI_progressbar.setMinimum(0)
        #self.nozzle_pressure_PSI_progressbar.setMaximum(self.operatingRange_nozzle_pressure_PSI[1])
        self.nozzle_pressure_PSI_progressbar.setMaximum(1)

        self.nozzle_pressure_PSI_progressbar.setTextVisible(False)
        self.nozzle_pressure_PSI_progressbar.setStyleSheet(progressbar_blue_stylesheet)

        self.nozzle_pressure_PSI_progressbar.setValue(0)
        self.nozzle_pressure_PSI_progressbar.hide()

        #
        # Progress bar for nozzle temperature
        self.nozzle_temp_C_progressbar = QtGui.QProgressBar(self)
        self.nozzle_temp_C_progressbar.setGeometry(40, 205, 280, 15)
        self.nozzle_temp_C_progressbar.setMinimum(10)
        self.nozzle_temp_C_progressbar.setMaximum(50)

        self.nozzle_temp_C_progressbar.setTextVisible(False)
        self.nozzle_temp_C_progressbar.setStyleSheet(progressbar_red_stylesheet)

        self.nozzle_temp_C_progressbar.setValue(10)
        self.nozzle_temp_C_progressbar.hide()

        #
        # Now create the checkboxes associated with the progress bars

        #
        # Checkbox for the vessel pressure
        self.vessel_pressure_checkbox = QtGui.QCheckBox("Pressurizing...", self)
        self.vessel_pressure_checkbox.setGeometry(340, 80, 140, 15)
        self.vessel_pressure_checkbox.setStyleSheet(checkbox_waiting_stylesheet)
        self.vessel_pressure_checkbox.setChecked(False)
        self.vessel_pressure_checkbox.setEnabled(False)
        self.vessel_pressure_checkbox.hide()
        #
        # Checkbox for the vessel temperature
        self.vessel_temp_checkbox = QtGui.QCheckBox("Waiting...", self)
        self.vessel_temp_checkbox.setGeometry(340, 125, 140, 15)
        self.vessel_temp_checkbox.setStyleSheet(checkbox_waiting_stylesheet)
        self.vessel_temp_checkbox.setChecked(False)
        self.vessel_temp_checkbox.setEnabled(False)
        self.vessel_temp_checkbox.hide()

        #
        # Checkbox for the nozzle pressure
        self.nozzle_pressure_checkbox = QtGui.QCheckBox("Pressurizing...", self)
        self.nozzle_pressure_checkbox.setGeometry(340, 165, 140, 15)
        self.nozzle_pressure_checkbox.setStyleSheet(checkbox_waiting_stylesheet)
        self.nozzle_pressure_checkbox.setChecked(False)
        self.nozzle_pressure_checkbox.setEnabled(False)
        self.nozzle_pressure_checkbox.hide()

        #
        # Checkbox for the nozzle temperature
        self.nozzle_temp_checkbox = QtGui.QCheckBox("Waiting...", self)
        self.nozzle_temp_checkbox.setGeometry(340, 205, 140, 15)
        self.nozzle_temp_checkbox.setStyleSheet(checkbox_waiting_stylesheet)
        self.nozzle_temp_checkbox.setChecked(False)
        self.nozzle_temp_checkbox.setEnabled(False)
        self.nozzle_temp_checkbox.hide()

        #
        # *********************************************************************************************
        #  Create w6-system-startup
        # *********************************************************************************************
        #
        # Label on System Startup Window
        self.w6_screen_title_label = QtGui.QLabel(self)
        new_title = "System Startup: etime= %3i min, %2i sec" % (0, 0)
        self.w6_screen_title_label.setText(new_title)
        self.w6_screen_title_label.setStyleSheet("font-size: 14pt; font-family: Lucida Sans Typewriter; font-weight: bold")
        self.w6_screen_title_label.resize(475, 31)
        self.w6_screen_title_label.move(5, 16)
        self.w6_screen_title_label.hide()
        #
        # The Abort Button moves to the w10 screen
        #
        self.w6_abort_button = QtGui.QPushButton("Abort", self)
        self.w6_abort_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(255,255,30); color:rgb(51,51,51)"
        )
        self.w6_abort_button.resize(75, 25)
        self.w6_abort_button.move(180, 235)
        self.w6_abort_button.hide()

        #
        # The w6 continue button
        #
        self.w6_continue_button = QtGui.QPushButton("Continue", self)
        self.w6_continue_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w6_continue_button.resize(195, 25)
        self.w6_continue_button.move(273, 235)
        self.w6_continue_button.hide()

        #
        # *********************************************************************************************
        #  Create w6a-setpoint-not-reached
        # *********************************************************************************************
        #
        # Window Label
        self.w6a_screen_title_label = QtGui.QLabel(self)
        self.w6a_screen_title_label.setText("<center>Warning: Setpoint Not Reached<br>within 10 minutes</center>")
        self.w6a_screen_title_label.setStyleSheet("font-size: 16pt; font-family: Lucida Sans Typewriter; font-weight: bold; background-color:rgb(255,255,30)")
        self.w6a_screen_title_label.resize(400, 70)
        self.w6a_screen_title_label.move(40, 20)
        self.w6a_screen_title_label.setWordWrap(True)
        self.w6a_screen_title_label.hide()

        # Label on Controller Shutdown Screen
        self.w6a_screen_message = QtGui.QLabel(self)
        self.w6a_screen_message.setText("<center>Shut Down System<br>and<br>Consult with Project Engineer!</center>")
        self.w6a_screen_message.setStyleSheet("font-size: 14pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic")
        self.w6a_screen_message.resize(400, 70)
        self.w6a_screen_message.move(40, 120)
        self.w6a_screen_message.setWordWrap(True)
        self.w6a_screen_message.hide()

        #
        # The Back Button returns to the w6 screen
        #
        self.w6a_back_button = QtGui.QPushButton("< Back", self)
        self.w6a_back_button.setStyleSheet(button_white_stylesheet)
        self.w6a_back_button.resize(75, 25)
        self.w6a_back_button.move(180, 235)
        self.w6a_back_button.hide()

        #
        # The Shutdown  Button moves the app to the next screen
        self.w6a_shutdown_button = QtGui.QPushButton("**Shutdown**", self)
        self.w6a_shutdown_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w6a_shutdown_button.resize(195, 25)
        self.w6a_shutdown_button.move(273, 235)
        self.w6a_shutdown_button.hide()

        #
        # *********************************************************************************************
        #  Create w7-setpoint-reached screen
        # *********************************************************************************************
        #

        # Window Label

        self.w7_screen_title_label = QtGui.QLabel(self)
        self.w7_screen_title_label.setText("<center>System Startup took 3 min, 35 sec</center>")
        self.w7_screen_title_label.setStyleSheet("font-size: 14pt; font-family: Lucida Sans Typewriter; font-weight: bold")
        self.w7_screen_title_label.resize(465, 31)
        self.w7_screen_title_label.move(10, 16)
        self.w7_screen_title_label.hide()

        #
        # The w7 continue button
        #
        self.w7_continue_button = QtGui.QPushButton("Continue", self)
        self.w7_continue_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w7_continue_button.resize(195, 25)
        self.w7_continue_button.move(273, 235)
        self.w7_continue_button.hide()

        #
        # *********************************************************************************************
        #  Create w8-purge-nozzle-question screen
        # *********************************************************************************************
        #
        # Create the Purge Nozzle 1? and Continue Button
        self.w8_purge_nozzle_button1 = QtGui.QPushButton("Purge Nozzle 1?", self)
        self.w8_purge_nozzle_button1.setStyleSheet(
            "font-size: 18pt; font-family: Lucida Sans Typewriter;  font-style: italic;  background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w8_purge_nozzle_button1.resize(260, 40)
        self.w8_purge_nozzle_button1.move(107, 15)
        self.w8_purge_nozzle_button1.hide()

        # Create the Purge Nozzle 1? and Continue Button
        self.w8_purge_nozzle_button2 = QtGui.QPushButton("Purge Nozzle 2?", self)
        self.w8_purge_nozzle_button2.setStyleSheet(
            "font-size: 18pt; font-family: Lucida Sans Typewriter;  font-style: italic;  background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w8_purge_nozzle_button2.resize(260, 40)
        self.w8_purge_nozzle_button2.move(107, 60)
        self.w8_purge_nozzle_button2.hide()

        # Create the Purge Nozzle 1? and Continue Button
        self.w8_purge_nozzle_button3 = QtGui.QPushButton("Purge Nozzle 3?", self)
        self.w8_purge_nozzle_button3.setStyleSheet(
            "font-size: 18pt; font-family: Lucida Sans Typewriter;  font-style: italic;  background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w8_purge_nozzle_button3.resize(260, 40)
        self.w8_purge_nozzle_button3.move(107, 105)
        self.w8_purge_nozzle_button3.hide()
        #
        # The w8 continue button
        #
        self.w8_continue_button = QtGui.QPushButton("Continue", self)
        self.w8_continue_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w8_continue_button.resize(195, 25)
        self.w8_continue_button.move(273, 235)
        self.w8_continue_button.hide()

        #
        # *******************************************************************
        # ***   Create w8a-dispensing screen                              ***
        # *******************************************************************
        #
        # Create the big "Dispense" button and the progress bar

        self.w8a_dispensing_text_label = QtGui.QLabel(self)
        self.w8a_dispensing_text_label.setText("<center>Purging Nozzle...</center>")
        self.w8a_dispensing_text_label.setStyleSheet(
            "font-size: 28pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(59,120,255); color:rgb(255,255,255)"
        )
        self.w8a_dispensing_text_label.resize(396, 64)
        self.w8a_dispensing_text_label.move(42, 52)
        self.w8a_dispensing_text_label.hide()

        #
        # progress bar for dispensing
        self.w8a_dispensing_progressbar = QtGui.QProgressBar(self)
        self.w8a_dispensing_progressbar.setGeometry(120, 145, 240, 24)
        self.w8a_dispensing_progressbar.setMinimum(0)
        self.w8a_dispensing_progressbar.setMaximum(self.setpoint_current_blast_sec)
        self.w8a_dispensing_progressbar.setValue(0)
        self.w8a_dispensing_progressbar.setTextVisible(False)
        self.w8a_dispensing_progressbar.setStyleSheet(progressbar_blue_stylesheet)
        self.w8a_dispensing_progressbar.hide()

        #
        # Animation object for the dispensing progress bar
        nozzle_on_time_seconds = self.setpoint_current_blast_sec
        i_nozzle = int(nozzle_on_time_seconds * 1000.0)
        self.w8a_dispensing_animation = QPropertyAnimation(self.w8a_dispensing_progressbar, "value")
        self.w8a_dispensing_animation.setDuration(i_nozzle)
        self.w8a_dispensing_animation.setStartValue(0)
        self.w8a_dispensing_animation.setEndValue(self.setpoint_current_blast_sec)
        self.w8a_dispensing_animation.finished.connect(lambda: self.hide_w8a())

        #
        # *********************************************************************************************
        #  Create w9-go screen
        # *********************************************************************************************
        #
        self.w9_fire_nozzle1_button = QtGui.QPushButton("Go Nozzle 1", self)
        self.w9_fire_nozzle1_button.setStyleSheet(
            "font-size: 18pt; font-family: Lucida Sans Typewriter;  font-style: italic;  background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        # GO NOZZLE 1
        self.w9_fire_nozzle1_button.resize(275, 40)
        self.w9_fire_nozzle1_button.move(20, 15)
        self.w9_fire_nozzle1_button.hide()

        self.w9_fire_nozzle2_button = QtGui.QPushButton("Go Nozzle 2", self)
        self.w9_fire_nozzle2_button.setStyleSheet(
            "font-size: 18pt; font-family: Lucida Sans Typewriter;  font-style: italic;  background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        # GO NOZZLE 2
        self.w9_fire_nozzle2_button.resize(275, 40)
        self.w9_fire_nozzle2_button.move(20, 60)
        self.w9_fire_nozzle2_button.hide()

        self.w9_fire_nozzle3_button = QtGui.QPushButton("Go Nozzle 3", self)
        self.w9_fire_nozzle3_button.setStyleSheet(
            "font-size: 18pt; font-family: Lucida Sans Typewriter;  font-style: italic;  background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        # GO NOZZLE 3
        self.w9_fire_nozzle3_button.resize(275, 40)
        self.w9_fire_nozzle3_button.move(20, 105)
        self.w9_fire_nozzle3_button.hide()


        # Independent pulse time buttons beside each nozzle
        self.pulse_time_buttons = {}

        for number, y_position in (
            (1, 15),
            (2, 60),
            (3, 105)
        ):
            button = QtGui.QPushButton(self)

            button.setText(
                "TIME: {}s".format(
                    self.pulse_durations[number]
                )
            )

            button.setGeometry(305, y_position, 155, 40)

            button.setStyleSheet(
                "QPushButton {"
                "background-color: #FFFFFF;"
                "color: #333333;"
                "border: 2px solid #9ADA3A;"
                "border-radius: 5px;"
                "font-size: 15px;"
                "font-weight: bold;"
                "}"
                "QPushButton:pressed {"
                "background-color: #D9EFC3;"
                "}"
            )

            button.clicked.connect(
                lambda checked=False, n=number:
                    self.edit_nozzle_duration(n)
            )

            button.hide()

            self.pulse_time_buttons[number] = button


        self.w9_shutdown_button = QtGui.QPushButton("Shutdown", self)
        self.w9_shutdown_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(255,255,255); color:rgb(51,51,51)"
        )
        self.w9_shutdown_button.resize(195, 25)
        self.w9_shutdown_button.move(273, 235)
        self.w9_shutdown_button.hide()


        self.w9_admin_button = QtGui.QPushButton("Admin", self)
        self.w9_admin_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(255,255,255); color:rgb(51,51,51)"
        )
        self.w9_admin_button.setText("DURATIONS")
        self.w9_admin_button.resize(150, 25)
        self.w9_admin_button.move(12, 235)
        self.w9_admin_button.hide()

        #
        # *******************************************************************
        # ***   Create w9a-dispensing screen                              ***
        # *******************************************************************
        #
        # Create the big "Dispense" button and the progress bar

        self.w9a_dispensing_text_label = QtGui.QLabel(self)
        self.w9a_dispensing_text_label.setText("<center>Dispensing...</center>")
        self.w9a_dispensing_text_label.setStyleSheet(
            "font-size: 28pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(59,120,255); color:rgb(255,255,255)"
        )
        self.w9a_dispensing_text_label.resize(396, 64)
        self.w9a_dispensing_text_label.move(42, 52)
        self.w9a_dispensing_text_label.hide()

        #
        # progress bar for dispensing
        self.w9a_dispensing_progressbar = QtGui.QProgressBar(self)
        self.w9a_dispensing_progressbar.setGeometry(120, 145, 240, 24)
        self.w9a_dispensing_progressbar.setMinimum(0)
        self.w9a_dispensing_progressbar.setMaximum(self.setpoint_current_blast_sec)
        self.w9a_dispensing_progressbar.setValue(0)
        self.w9a_dispensing_progressbar.setTextVisible(False)
        self.w9a_dispensing_progressbar.setStyleSheet(progressbar_blue_stylesheet)
        self.w9a_dispensing_progressbar.hide()
        #
        # Animation object for the dispensing progress bar
        nozzle_on_time_seconds = self.setpoint_current_blast_sec
        i_nozzle = int(nozzle_on_time_seconds * 1000.0)
        self.w9a_dispensing_animation = QPropertyAnimation(self.w9a_dispensing_progressbar, "value")
        self.w9a_dispensing_animation.setDuration(i_nozzle)
        self.w9a_dispensing_animation.setStartValue(0)
        self.w9a_dispensing_animation.setEndValue(self.setpoint_current_blast_sec)
        self.w9a_dispensing_animation.finished.connect(lambda: self.hide_w9a())

        #
        # *********************************************************************************************
        #  Create w9b Error window
        # *********************************************************************************************
        #
        # have to show a title with "Time to change the tank." then below that show the current temperature and pressure and a message that says what is incorrect. Then below that a button to go back to w9 screeen to try again.
        self.w9b_screen_title_label = QtGui.QLabel(self)
        self.w9b_screen_title_label.setText("<center>Environmental Condition Error: <br/> Time to change the tank.</center>")
        self.w9b_screen_title_label.setStyleSheet("font-size: 14pt; font-family: Lucida Sans Typewriter; font-weight: bold; background-color: red")
        self.w9b_screen_title_label.resize(465, 61)
        self.w9b_screen_title_label.move(10, 16)
        self.w9b_screen_title_label.hide()

        self.w9b_temperature_pressure_label = QtGui.QLabel(self)
        self.w9b_temperature_pressure_label.setStyleSheet("font-size: 12pt; font-family: Lucida Sans Typewriter;")
        self.w9b_temperature_pressure_label.resize(465, 31)
        self.w9b_temperature_pressure_label.move(10, 85)
        self.w9b_temperature_pressure_label.hide()

        self.w9b_message_label = QtGui.QLabel(self)
        self.w9b_message_label.setStyleSheet("font-size: 12pt; font-family: Lucida Sans Typewriter; color: red")
        self.w9b_message_label.resize(465, 31)
        self.w9b_message_label.move(10, 120)
        self.w9b_message_label.hide()

        self.w9b_try_again_button = QtGui.QPushButton("Try Again", self)
        self.w9b_try_again_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w9b_try_again_button.resize(160, 30)
        self.w9b_try_again_button.move(166, 170)
        self.w9b_try_again_button.hide()

        #
        # *********************************************************************************************
        #  Create w9c-admin window
        # *********************************************************************************************
        #
        # Window Label
        self.degree_sign = "\N{DEGREE SIGN}"
        # Labels
        self.w9c_admin_text_label = QtGui.QLabel(self)
        self.w9c_admin_text_label.setText("<center>ADMIN: Setpoint Changes<\center>")
        self.w9c_admin_text_label.setAlignment(QtCore.Qt.AlignLeft)
        self.w9c_admin_text_label.setStyleSheet("font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold")
        self.w9c_admin_text_label.resize(475, 20)
        self.w9c_admin_text_label.move(10, 15)
        self.w9c_admin_text_label.hide()

        self.w9c_realtime_sp_text_label = QtGui.QLabel(self)
        self.w9c_realtime_sp_text_label.setText("Changed sp,[sp]")
        self.w9c_realtime_sp_text_label.setAlignment(QtCore.Qt.AlignLeft)
        self.w9c_realtime_sp_text_label.setStyleSheet("font-size: 12pt; font-family: Lucida Sans Typewriter; font-style: italic;font-weight: bold")
        self.w9c_realtime_sp_text_label.resize(180, 41)
        self.w9c_realtime_sp_text_label.move(75, 45)
        self.w9c_realtime_sp_text_label.hide()

        self.w9c_change_sp_text_label = QtGui.QLabel(self)
        self.w9c_change_sp_text_label.setText("Change [sp] ")
        self.w9c_change_sp_text_label.setAlignment(QtCore.Qt.AlignLeft)
        self.w9c_change_sp_text_label.setStyleSheet("font-size: 12pt; font-family: Lucida Sans Typewriter; font-style: italic; font-weight: bold")
        self.w9c_change_sp_text_label.resize(180, 41)
        self.w9c_change_sp_text_label.move(295, 45)
        self.w9c_change_sp_text_label.hide()

        self.w9c_blast_sec_text_label = QtGui.QLabel(self)
        b = self.scrollbar_blast_sec_values.index(self.scrollbar_limits_blast_sec[3])
        c = self.scrollbar_blast_sec_values[b]
        new_text = "Blast  (sec) =   %4.1f,[%4.1f]" % (c, c)
        self.w9c_blast_sec_text_label.setText(new_text)
        self.w9c_blast_sec_text_label.setAlignment(QtCore.Qt.AlignLeft)
        self.w9c_blast_sec_text_label.setStyleSheet("font-size: 11pt; font-family: Lucida Sans Typewriter; font-weight: bold")
        self.w9c_blast_sec_text_label.resize(289, 25)
        self.w9c_blast_sec_text_label.move(10, 76)
        self.w9c_blast_sec_text_label.hide()

        self.w9c_nozzle_t_text_label = QtGui.QLabel(self)
        b = self.scrollbar_nozzle_temperature_C_values.index(self.scrollbar_limits_nozzle_temperature_C[3])
        c = self.scrollbar_nozzle_temperature_C_values[b]
        new_text = "Nozzle (T C) =   %4i,[%4i]" % (c, c)
        self.w9c_nozzle_t_text_label.setText(new_text)
        self.w9c_nozzle_t_text_label.setAlignment(QtCore.Qt.AlignLeft)
        self.w9c_nozzle_t_text_label.setStyleSheet("font-size: 11pt; font-family: Lucida Sans Typewriter; font-weight: bold")
        self.w9c_nozzle_t_text_label.resize(289, 25)
        self.w9c_nozzle_t_text_label.move(10, 106)
        self.w9c_nozzle_t_text_label.hide()

        self.w9c_nozzle_psi_text_label = QtGui.QLabel(self)
        b = self.scrollbar_limits_nozzle_pressure_PSI_values.index(self.scrollbar_limits_nozzle_pressure_PSI[3])
        c = self.scrollbar_limits_nozzle_pressure_PSI_values[b]
        new_text = "Nozzle (psi) =   %4i,[%4i]" % (c, c)
        self.w9c_nozzle_psi_text_label.setText(new_text)
        self.w9c_nozzle_psi_text_label.setAlignment(QtCore.Qt.AlignLeft)
        self.w9c_nozzle_psi_text_label.setStyleSheet("font-size: 11pt; font-family: Lucida Sans Typewriter; font-weight: bold")
        self.w9c_nozzle_psi_text_label.resize(289, 25)
        self.w9c_nozzle_psi_text_label.move(10, 136)
        self.w9c_nozzle_psi_text_label.hide()

        self.w9c_vessel_t_text_label = QtGui.QLabel(self)
        b = self.scrollbar_limits_vessel_temperature_C_values.index(self.scrollbar_limits_vessel_temperature_C[3])
        c = self.scrollbar_limits_vessel_temperature_C_values[b]
        new_text = "Vessel (T C) =   %4i,[%4i]" % (c, c)
        self.w9c_vessel_t_text_label.setText(new_text)
        self.w9c_vessel_t_text_label.setAlignment(QtCore.Qt.AlignLeft)
        self.w9c_vessel_t_text_label.setStyleSheet("font-size: 11pt; font-family: Lucida Sans Typewriter; font-weight: bold")
        self.w9c_vessel_t_text_label.resize(289, 25)
        self.w9c_vessel_t_text_label.move(10, 166)
        self.w9c_vessel_t_text_label.hide()

        self.w9c_vessel_psi_text_label = QtGui.QLabel(self)
        self.w9c_vessel_psi_text_label.setText("Vessel (psi) =    450")
        self.w9c_vessel_psi_text_label.setAlignment(QtCore.Qt.AlignLeft)
        self.w9c_vessel_psi_text_label.setStyleSheet("font-size: 11pt; font-family: Lucida Sans Typewriter; font-weight: bold")
        self.w9c_vessel_psi_text_label.resize(289, 25)
        self.w9c_vessel_psi_text_label.move(10, 196)
        self.w9c_vessel_psi_text_label.hide()

        #
        # Create the buttons
        self.w9c_load_startup_sp_button = QtGui.QPushButton("Load Startup sp", self)
        self.w9c_load_startup_sp_button.setStyleSheet(smaller_button_white_stylesheet)
        self.w9c_load_startup_sp_button.resize(125, 25)
        self.w9c_load_startup_sp_button.move(5, 235)
        self.w9c_load_startup_sp_button.setEnabled(True)
        self.w9c_load_startup_sp_button.hide()

        self.w9c_save_new_startup_sp_button = QtGui.QPushButton("Save New Startup sp", self)
        self.w9c_save_new_startup_sp_button.setStyleSheet(smaller_button_white_stylesheet)
        self.w9c_save_new_startup_sp_button.resize(160, 25)
        self.w9c_save_new_startup_sp_button.move(135, 235)
        self.w9c_save_new_startup_sp_button.setEnabled(True)
        self.w9c_save_new_startup_sp_button.hide()

        self.w9c_run_changed_sp_button = QtGui.QPushButton("Run Changed sp", self)
        self.w9c_run_changed_sp_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w9c_run_changed_sp_button.resize(165, 25)
        self.w9c_run_changed_sp_button.move(303, 235)
        self.w9c_run_changed_sp_button.hide()

        #
        # Create the sliders/scrollbars
        # https://doc.qt.io/archives/qt-4.8/stylesheet-examples.html#customizing-qslider
        # https://thesmithfam.org/blog/2010/03/10/fancy-qslider-stylesheet/

        self.w9c_blast_sec_scrollbar = QtGui.QScrollBar(Qt.Horizontal, self)
        self.w9c_blast_sec_scrollbar.setStyleSheet("background-color:orange")
        self.w9c_blast_sec_scrollbar.setMinimum(0)
        self.w9c_blast_sec_scrollbar.setMaximum(len(self.scrollbar_blast_sec_values) - 1)
        self.w9c_blast_sec_scrollbar.setValue(self.scrollbar_blast_sec_values.index(self.scrollbar_limits_blast_sec[3]))
        self.w9c_blast_sec_scrollbar.resize(200, 25)
        self.w9c_blast_sec_scrollbar.move(250, 71)
        self.w9c_blast_sec_scrollbar.hide()

        self.w9c_nozzle_t_scrollbar = QtGui.QScrollBar(Qt.Horizontal, self)
        self.w9c_nozzle_t_scrollbar.setStyleSheet("background-color:red")
        self.w9c_nozzle_t_scrollbar.setMinimum(0)
        self.w9c_nozzle_t_scrollbar.setMaximum(len(self.scrollbar_nozzle_temperature_C_values) - 1)
        self.w9c_nozzle_t_scrollbar.setValue(self.scrollbar_nozzle_temperature_C_values.index(self.scrollbar_limits_nozzle_temperature_C[3]))
        self.w9c_nozzle_t_scrollbar.resize(200, 25)
        self.w9c_nozzle_t_scrollbar.move(250, 101)
        self.w9c_nozzle_t_scrollbar.hide()

        self.w9c_nozzle_psi_scrollbar = QtGui.QScrollBar(Qt.Horizontal, self)
        self.w9c_nozzle_psi_scrollbar.setStyleSheet("background-color:blue")
        self.w9c_nozzle_psi_scrollbar.setMinimum(0)
        self.w9c_nozzle_psi_scrollbar.setMaximum(len(self.scrollbar_limits_nozzle_pressure_PSI_values) - 1)
        self.w9c_nozzle_psi_scrollbar.setValue(self.scrollbar_limits_nozzle_pressure_PSI_values.index(self.scrollbar_limits_nozzle_pressure_PSI[3]))
        self.w9c_nozzle_psi_scrollbar.resize(200, 25)
        self.w9c_nozzle_psi_scrollbar.move(250, 131)
        self.w9c_nozzle_psi_scrollbar.hide()

        self.w9c_vessel_t_scrollbar = QtGui.QScrollBar(Qt.Horizontal, self)
        self.w9c_vessel_t_scrollbar.setStyleSheet("background-color:red")
        self.w9c_vessel_t_scrollbar.setMinimum(0)
        self.w9c_vessel_t_scrollbar.setMaximum(len(self.scrollbar_limits_vessel_temperature_C_values) - 1)
        self.w9c_vessel_t_scrollbar.setValue(self.scrollbar_limits_vessel_temperature_C_values.index(self.scrollbar_limits_vessel_temperature_C[3]))
        self.w9c_vessel_t_scrollbar.resize(200, 25)
        self.w9c_vessel_t_scrollbar.move(250, 161)
        self.w9c_vessel_t_scrollbar.hide()

        #
        # *********************************************************************************************
        #  Create w10-setpoint-not-reached
        # *********************************************************************************************
        #
        # Window Label
        self.w10_screen_title_label = QtGui.QLabel(self)
        self.w10_screen_title_label.setText("<center>Shut Down the Machine?</center>")
        self.w10_screen_title_label.setStyleSheet("font-size: 20pt; font-family: Lucida Sans Typewriter; font-weight: bold; background-color:rgb(255,255,30)")
        self.w10_screen_title_label.resize(400, 50)
        self.w10_screen_title_label.move(40, 40)
        self.w10_screen_title_label.setWordWrap(True)
        self.w10_screen_title_label.hide()

        self.w10_yes_button = QtGui.QPushButton("Yes", self)
        self.w10_yes_button.setStyleSheet(
            "font-size: 16pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; color:rgb(0,0,0); background-color:rgb(154,218,58)"
        )
        self.w10_yes_button.resize(100, 50)
        self.w10_yes_button.move(70, 112)
        self.w10_yes_button.hide()

        self.w10_no_button = QtGui.QPushButton("No!", self)
        self.w10_no_button.setStyleSheet(
            "font-size: 16pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic;  color:rgb(0,0,0); background-color:rgb(240,58,23)"
        )
        self.w10_no_button.resize(100, 50)
        self.w10_no_button.move(300, 112)
        self.w10_no_button.hide()

        #
        # *********************************************************************************************
        #  Create w11-shutdown-in-progress
        # *********************************************************************************************
        #
        # Label on System Startup Window
        self.w11_screen_title_label = QtGui.QLabel(self)
        new_title = "System Shutdown etime= %3i min, %2i sec" % (0, 0)
        self.w11_screen_title_label.setText(new_title)
        self.w11_screen_title_label.setStyleSheet("font-size: 14pt; font-family: Lucida Sans Typewriter; font-weight: bold")
        self.w11_screen_title_label.resize(470, 31)
        self.w11_screen_title_label.move(5, 16)
        self.w11_screen_title_label.hide()

        #
        # The w11 continue button
        #
        self.w11_continue_button = QtGui.QPushButton("Continue", self)
        self.w11_continue_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w11_continue_button.resize(195, 25)
        self.w11_continue_button.move(273, 235)
        self.w11_continue_button.hide()

        #
        # *********************************************************************************************
        #  Create w12-shutdown-complete
        # *********************************************************************************************
        #
        # Label on System Startup Window
        self.w12_screen_title_label = QtGui.QLabel(self)
        self.w12_screen_title_label.setText("System Shutdown took 8 min, 35 sec")
        self.w12_screen_title_label.setStyleSheet("font-size: 14pt; font-family: Lucida Sans Typewriter; font-weight: bold")
        self.w12_screen_title_label.resize(465, 31)
        self.w12_screen_title_label.move(10, 16)
        self.w12_screen_title_label.hide()

        #
        # The w12 continue button
        #
        self.w12_continue_button = QtGui.QPushButton("Continue", self)
        self.w12_continue_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w12_continue_button.resize(195, 25)
        self.w12_continue_button.move(273, 235)
        self.w12_continue_button.hide()

        #
        # *********************************************************************************************
        #  Create w13-close-air-pressure-valve
        # *********************************************************************************************
        #
        self.w13_continue_button = QtGui.QPushButton("Continue", self)
        self.w13_continue_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w13_continue_button.resize(120, 25)
        self.w13_continue_button.move(340, 240)
        self.w13_continue_button.hide()

        self.w13_back_button = QtGui.QPushButton("BACK", self)

        # Position (x, y)
        self.w13_back_button.move(190, 240)

        # Size (width, height)
        self.w13_back_button.resize(100, 25)

        self.w13_back_button.setStyleSheet(
            "font-size: 12pt; font-weight: bold;"
            "background-color: rgb(154,218,58);"
            "color: rgb(51,51,51);"
        )

        self.w13_back_button.hide()

        self.w13_back_button.clicked.connect(
            self.w13_back_button_callback
        )      

        #
        # *********************************************************************************************
        #  Create w13a-air-regulator-shutdown-turn-knob
        # *********************************************************************************************
        #
        self.w13a_continue_button = QtGui.QPushButton("Continue", self)
        self.w13a_continue_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w13a_continue_button.resize(195, 25)
        self.w13a_continue_button.move(273, 235)
        self.w13a_continue_button.hide()

        #
        # *********************************************************************************************
        #  Create w13b-air-regulator-shutdown-turn-knob
        # *********************************************************************************************
        #
        self.w13b_continue_button = QtGui.QPushButton("Continue", self)
        self.w13b_continue_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w13b_continue_button.resize(195, 25)
        self.w13b_continue_button.move(273, 235)
        self.w13b_continue_button.hide()


        # Reusable Startup / Shutdown introduction page
        self.instruction_intro_mode = None

        self.instruction_intro_title = QtGui.QLabel(self)
        self.instruction_intro_title.setGeometry(20, 85, 440, 75)
        self.instruction_intro_title.setAlignment(
            QtCore.Qt.AlignCenter
        )
        self.instruction_intro_title.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
            "color: #333333; background-color: #F5F6F3;"
        )
        self.instruction_intro_title.hide()

        # BACK
        self.instruction_intro_back = QtGui.QPushButton(
            "BACK", self
        )
        self.instruction_intro_back.setGeometry(
            190, 240, 100, 25
        )

        # CONTINUE
        self.instruction_intro_continue = QtGui.QPushButton(
            "CONTINUE", self
        )
        self.instruction_intro_continue.setGeometry(
            340, 240, 120, 25
        )

        style = (
            "font-size: 12pt; font-weight: bold;"
            "background-color: rgb(154,218,58);"
            "color: rgb(51,51,51);"
        )

        for button in (
            self.instruction_intro_back,
            self.instruction_intro_continue
        ):
            button.setStyleSheet(style)
            button.hide()

        self.instruction_intro_back.clicked.connect(
            self.instruction_intro_back_clicked
        )
        self.instruction_intro_continue.clicked.connect(
            self.instruction_intro_continue_clicked
        )


        #
        # *********************************************************************************************
        #  Create w14-close-co2-valve-all-the-way
        # *********************************************************************************************
        #
        self.w14_continue_button = QtGui.QPushButton("Continue", self)
        self.w14_continue_button.setStyleSheet(
            "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(154,218,58); color:rgb(51,51,51)"
        )
        self.w14_continue_button.resize(195, 25)
        self.w14_continue_button.move(273, 235)
        self.w14_continue_button.hide()

        #
        # *********************************************************************************************
        #  Create w15-power-off-clean-system
        # *********************************************************************************************
        #
        self.w15_screen_title_label = QtGui.QLabel(self)
        self.w15_screen_title_label.setText("<center>Wait Until Screen Darkens<br>Then<br>Turn Off Power<br>And<br>!!!*** CLEAN THE SYSTEM ***!!!</center>")
        self.w15_screen_title_label.setStyleSheet("font-size: 16pt; font-family: Lucida Sans Typewriter; font-weight: bold; background-color:rgb(255,255,30)")
        self.w15_screen_title_label.resize(400, 140)
        self.w15_screen_title_label.move(40, 20)
        self.w15_screen_title_label.setWordWrap(True)
        self.w15_screen_title_label.hide()

        # Label on Controller Shutdown Screen
        self.w15_screen_message_label = QtGui.QLabel(self)
        self.w15_screen_message_label.setText("<center>Shutting Down Controller...</center>")
        self.w15_screen_message_label.setStyleSheet("font-size: 16pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic")
        self.w15_screen_message_label.resize(400, 120)
        self.w15_screen_message_label.move(40, 135)
        self.w15_screen_message_label.setWordWrap(True)
        self.w15_screen_message_label.hide()


        # Fullscreen standby overlay
        self.standby_button = QtGui.QPushButton(
            "SYSTEM IN STANDBY\n\nTap anywhere to start",
            self
        )

        self.standby_button.setStyleSheet("""
            QPushButton {
                background-color: #080808;
                color: #A8A8A8;
                border: none;
                font-size: 24px;
                font-weight: bold;
            }
            QPushButton:pressed {
                background-color: #080808;
            }
        """)

        self.standby_button.setFocusPolicy(
            QtCore.Qt.NoFocus
        )

        self.standby_button.clicked.connect(
            self.wake_from_standby
        )

        # Do NOT show standby when the program first launches
        self.standby_button.hide()


        # **************************************************
        # ***  End of Widget Definitions                 ***
        # **************************************************

        #
        # Now configure the window that will display the widgets - it will be position at the upper left-hand corner (0,0)
        # then its dimensions will be set to the loaded splash screen image (480 pixels wwide, 272 pixels)
        # Then remove the Title bar and window outside frame
        # Reference:  https://stackoverflow.com/questions/7021502/pyqt-remove-the-programs-title-bar
        self.window_x = 0
        self.window_y = 0
        self.setGeometry(self.window_x, self.window_y, self.pixmap.width(), self.pixmap.height())
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)

        self.initUI()


    # Copy constants, file paths, operating ranges, and legacy defaults into instance attributes.
    def _set_variables(self):
        """Set up the variables for the controller"""
        # Initializes the directory and file paths for the controller.
        self.startup_setpoint_file_vessel_temperature_C = STARTUP_SETPOINT_FILE_VESSEL_TEMPERATURE_C
        self.startup_setpoint_file_vessel_pressure_PSI = STARTUP_SETPOINT_FILE_VESSEL_PRESSURE_PSI
        self.startup_setpoint_file_nozzle_temperature_C = STARTUP_SETPOINT_FILE_NOZZLE_TEMPERATURE_C

        self.startup_setpoint_file_nozzle_pressure_PSI = STARTUP_SETPOINT_FILE_NOZZLE_PRESSURE_PSI
        self.startup_setpoint_file_blast_sec = STARTUP_SETPOINT_FILE_BLAST_SEC
        self.startup_setpoint_file_pressure_vessel_heater_on_duration_seconds = STARTUP_SETPOINT_FILE_PRESSURE_VESSEL_HEATER_ON_DURATION_SECONDS
        self.startup_setpoint_file_nozzle_vessel_heater_on_duration_seconds = STARTUP_SETPOINT_FILE_NOZZLE_VESSEL_HEATER_ON_DURATION_SECONDS
        self.startup_setpoint_file_pressure_vessel_heater_seconds_to_wait_after_heating = (
            STARTUP_SETPOINT_FILE_PRESSURE_VESSEL_HEATER_SECONDS_TO_WAIT_AFTER_HEATING
        )
        self.startup_setpoint_file_nozzle_vessel_heater_seconds_to_wait_after_heating = STARTUP_SETPOINT_FILE_NOZZLE_VESSEL_HEATER_SECONDS_TO_WAIT_AFTER_HEATING
        self.startup_file_data_logging_file_number = STARTUP_FILE_DATA_LOGGING_FILE_NUMBER

        self.current_vessel_temperature_C = 0
        self.current_vessel_pressure_PSI = 0
        self.current_nozzle_temperature_C = 0
        self.current_nozzle_downstream_pressure_PSI = 0
        self.current_pressure_controller_PSI = 0

        self.operatingRange_vessel_temperature_C = OPERATING_RANGE_VESSEL_TEMPERATURE_C
        self.operatingRange_vessel_pressure_PSI = OPERATING_RANGE_VESSEL_PRESSURE_PSI
        self.operatingRange_nozzle_temperature_C = OPERATING_RANGE_NOZZLE_TEMPERATURE_C
        self.operatingRange_nozzle_pressure_PSI = OPERATING_RANGE_NOZZLE_PRESSURE_PSI
        self.operatingRange_pressure_controller_PSI = OPERATING_RANGE_PRESSURE_CONTROLLER_PSI

        self.operatingRange_blast_sec = OPERATING_RANGE_BLAST_SEC
        self.safeShutdownRange_vessel_temperature_C = SAFE_SHUTDOWN_RANGE_VESSEL_TEMPERATURE_C
        self.safeShutdownRange_vessel_pressure_PSI = SAFE_SHUTDOWN_RANGE_VESSEL_PRESSURE_PSI
        self.safeShutdownRange_nozzle_temperature_C = SAFE_SHUTDOWN_RANGE_NOZZLE_TEMPERATURE_C
        self.safeShutdownRange_nozzle_pressure_PSI = SAFE_SHUTDOWN_RANGE_NOZZLE_PRESSURE_PSI
        self.setpoint_default_vessel_temperature_C = SETPOINT_DEFAULT_VESSEL_TEMPERATURE_C
        self.setpoint_default_vessel_pressure_PSI = SETPOINT_DEFAULT_VESSEL_PRESSURE_PSI
        self.setpoint_default_nozzle_temperature_C = SETPOINT_DEFAULT_NOZZLE_TEMPERATURE_C
        self.setpoint_default_nozzle_pressure_PSI = SETPOINT_DEFAULT_NOZZLE_PRESSURE_PSI
        self.setpoint_default_blast_sec = SETPOINT_DEFAULT_BLAST_SEC

        self.setpoint_current_vessel_temperature_C = SETPOINT_CURRENT_VESSEL_TEMPERATURE_C
        self.setpoint_current_vessel_temperature_C_tolerance = SETPOINT_CURRENT_VESSEL_TEMPERATURE_C_TOLERANCE
        self.setpoint_current_vessel_pressure_PSI = SETPOINT_CURRENT_VESSEL_PRESSURE_PSI
        self.setpoint_current_nozzle_temperature_C = SETPOINT_CURRENT_NOZZLE_TEMPERATURE_C
        self.setpoint_current_nozzle_temperature_C_tolerance = SETPOINT_CURRENT_NOZZLE_TEMPERATURE_C_TOLERANCE
        self.setpoint_current_nozzle_pressure_PSI = SETPOINT_CURRENT_NOZZLE_PRESSURE_PSI
        self.setpoint_current_nozzle_pressure_PSI_tolerance = SETPOINT_CURRENT_NOZZLE_PRESSURE_PSI_TOLERANCE
        self.setpoint_current_blast_sec = SETPOINT_CURRENT_BLAST_SEC


    # Load or initialize historical operating setpoints.
    def initialize_setpoints(self):
        # Limit the setpoints to maximum allowed values with clamping
        self.setpoint_current_vessel_temperature_C = min(self.setpoint_current_vessel_temperature_C, 39)
        self.setpoint_current_nozzle_temperature_C = min(self.setpoint_current_nozzle_temperature_C, 40)
        self.setpoint_current_vessel_pressure_PSI = min(self.setpoint_current_vessel_pressure_PSI, 1450)
        self.setpoint_current_nozzle_pressure_PSI = min(self.setpoint_current_nozzle_pressure_PSI, 1450)


    # Derive allowable legacy operating ranges from current setpoints.
    def adjust_operating_ranges(self):
        # Adjust the temperature and pressure operating ranges based on the current setpoints
        self.operatingRange_vessel_temperature_C = (
            self.setpoint_current_vessel_temperature_C - 2,
            self.setpoint_current_vessel_temperature_C + 3,
        )
        self.operatingRange_nozzle_temperature_C = (
            self.setpoint_current_nozzle_temperature_C - 2,
            self.setpoint_current_nozzle_temperature_C + 2,
        )
        self.operatingRange_vessel_pressure_PSI = (
            self.setpoint_current_vessel_pressure_PSI,
            self.operatingRange_vessel_pressure_PSI[1],
        )


    # Initialize legacy setpoint scrollbar ranges and widget values.
    def initialize_scrollbars(self):
        # Setup scrollbar limits based on operating ranges
        self.scrollbar_limits_blast_sec = (
            self.operatingRange_blast_sec[0],
            self.operatingRange_blast_sec[1],
            0.5,
            self.setpoint_current_blast_sec,
        )
        self.scrollbar_limits_nozzle_temperature_C = (
            0,
            50,
            1,
            self.setpoint_current_nozzle_temperature_C,
        )
        self.scrollbar_blast_sec_values = tuple([x * 0.5 for x in range(2, 14)])
        self.scrollbar_limits_nozzle_pressure_PSI = (
            self.operatingRange_nozzle_pressure_PSI[0],
            self.operatingRange_nozzle_pressure_PSI[1],
            1,
            self.setpoint_current_nozzle_pressure_PSI,
        )
        self.scrollbar_limits_nozzle_pressure_PSI_values = tuple(range(0, 1451, 50))
        self.scrollbar_limits_vessel_temperature_C = (
            0,
            50,
            1,
            self.setpoint_current_vessel_temperature_C,
        )

        # Pre-defined ranges for temperature and pressure scrollbars
        self.scrollbar_nozzle_temperature_C_values = tuple(range(2, 41))
        self.scrollbar_nozzle_pressure_PSI_values = tuple(range(0, 1451, 50))
        self.scrollbar_limits_vessel_temperature_C_values = tuple(range(2, 40))


    # Initialize historical timing/logging values; disabled at current initialization call site.
    def initialize_logging_and_timing_controls(self):
        # Lists for temperature logging
        self.read_nozzle_temperature_C_list = [0.112] * 75
        self.read_vessel_temperature_C_list = [0.109] * 75

        # Logging file setup
        self.write_header_to_data_logging_file("w")
        self.write_column_labels_to_data_logging_file()


    # Initialize historical controller state flags and screen timing.
    def initialize_system_state(self):
        # System state initialization
        self.system_in_startup = False
        self.system_in_shutdown = False
        self.elapsed_startup_time_seconds = 0
        self.elapsed_shutdown_time_seconds = 0
        self.elapsed_time_from_GUI_startup_seconds = 0
        self.current_screen = ""
        self.system_nozzle_pressure_in_operating_range = False
        self.current_nozzle_downstream_pressure_PSI = None #read_alicat_downstream_pressure()


    # Initialize legacy control and sensor state variables.
    def initialize_control_variables(self):
        # Heater control timers and flags
        self.pressure_vessel_heater_on_duration_seconds = 3
        self.nozzle_vessel_heater_on_duration_seconds = 1
        self.dt = 1  # one second looping on control

        self.pressure_vessel_heater_seconds_to_wait_after_heating = 25
        self.nozzle_vessel_heater_seconds_to_wait_after_heating = 20

        self.nozzle_vessel_heater_wait = False
        self.pressure_vessel_heater_wait = False
        self.nozzle_vessel_heater_on = False
        self.pressure_vessel_heater_on = False
        self.nozzle_solenoid_on = {1: False, 2: False, 3: False}

        self.setpoints_were_reset = False


    # Construct the legacy subsystem-test label, status checkbox, and test button.
    def create_solenoid_relay_ui(self, solenoid_number, vertical_position):
        # Constants
        LABEL_WIDTH = 400
        LABEL_HEIGHT = 25
        CHECKBOX_WIDTH = 80
        CHECKBOX_HEIGHT = 15
        BUTTON_WIDTH = 75
        BUTTON_HEIGHT = 15
        HORIZONTAL_SPACING = 15

        # Styles
        label_style = "font-size: 11pt; font-family: Lucida Sans Typewriter; font-weight: bold"
        checkbox_style = checkbox_ready_stylesheet
        button_style = """
            font-size: 12pt;
            font-family: Lucida Sans Typewriter;
            font-weight: bold;
            font-style: italic;
            background-color: rgb(154,218,58);
            color: rgb(51,51,51);
        """

        # Label
        label = QtGui.QLabel(self)

        label.setText("Solenoid " + str(solenoid_number) + " Relay")
        label.setAlignment(QtCore.Qt.AlignLeft)
        label.setStyleSheet(label_style)
        label.resize(LABEL_WIDTH, LABEL_HEIGHT)
        label.move(HORIZONTAL_SPACING, vertical_position)
        label.hide()

        # Checkbox
        checkbox = QtGui.QCheckBox("2 clicks?", self)
        checkbox.setGeometry(
            LABEL_WIDTH - 2 * CHECKBOX_WIDTH,
            vertical_position,
            CHECKBOX_WIDTH,
            CHECKBOX_HEIGHT,
        )
        checkbox.setStyleSheet(checkbox_style)
        checkbox.setChecked(False)
        checkbox.setEnabled(True)
        checkbox.hide()

        # Test button
        button = QtGui.QPushButton("Test", self)
        button.setStyleSheet(button_style)
        button.resize(BUTTON_WIDTH, BUTTON_HEIGHT)
        button.move(LABEL_WIDTH - HORIZONTAL_SPACING, vertical_position)
        button.hide()

        return label, checkbox, button


    # Connect button signals and QTimer callbacks, display Welcome, enter fullscreen, then scale controls.
    def initUI(self):
        #
        # Assign the Widget callbacks - note that you have to use the lambda statement because you are passing a function call
        # (if you don't, you get a NoneType error)
        # Reference:  https://stackoverflow.com/questions/10730131/create-dynamic-button-in-pyqt

        self.w1_continue_button.clicked.connect(lambda: self.w1_continue_button_callback())

        self.w2_abort_button.clicked.connect(lambda: self.w2_abort_button_callback())
        self.w2_back_button.clicked.connect(lambda: self.w2_back_button_callback())

        self.w2_continue_button.clicked.connect(lambda: self.w2_continue_button_callback())

        self.w2_continue_confirm_button.clicked.connect(lambda: self.w2_continue_confirm_callback())

        self.solenoid1_test_button.clicked.connect(lambda: self.solenoid_status_test_button_callback(1))
        self.solenoid2_test_button.clicked.connect(lambda: self.solenoid_status_test_button_callback(2))
        self.solenoid3_test_button.clicked.connect(lambda: self.solenoid_status_test_button_callback(3))

        self.w2a_shutdown_button.clicked.connect(lambda: self.w2a_shutdown_button_callback())

        self.w3_continue_button.clicked.connect(lambda: self.w3_continue_button_callback())

        self.w4_continue_button.clicked.connect(lambda: self.w4_continue_button_callback())
        self.w4_back_button.clicked.connect( self.w4_back_button_callback)

        self.w5_turn_on_button.clicked.connect(lambda: self.w5_turn_on_button_callback())
        self.w5a_power_button.clicked.connect(lambda: self.w5a_power_button_callback())
        self.turn_on_water_bath_timer.timeout.connect(lambda: self.turn_on_water_bath_timer_callback())
        self.w5b_continue_button.clicked.connect(lambda: self.w5b_continue_button_callback())

        self.w6_abort_button.clicked.connect(lambda: self.w6_abort_button_callback())
        self.w6_continue_button.clicked.connect(lambda: self.w6_continue_button_callback())

        self.w6a_shutdown_button.clicked.connect(lambda: self.w6a_shutdown_button_callback())
        self.w6a_back_button.clicked.connect(lambda: self.w6a_back_button_callback())

        self.w7_continue_button.clicked.connect(lambda: self.w7_continue_button_callback())

        self.w8_continue_button.clicked.connect(lambda: self.w8_continue_button_callback())
        self.w8_purge_nozzle_button1.clicked.connect(lambda: self.w8_purge_nozzle_button_callback(1))
        self.w8_purge_nozzle_button2.clicked.connect(lambda: self.w8_purge_nozzle_button_callback(2))
        self.w8_purge_nozzle_button3.clicked.connect(lambda: self.w8_purge_nozzle_button_callback(3))

        self.w9_shutdown_button.clicked.connect(lambda: self.w9_shutdown_button_callback())
        self.w9_fire_nozzle1_button.clicked.connect(lambda: self.w9_fire_nozzle_button_callback(1))
        self.w9_fire_nozzle2_button.clicked.connect(lambda: self.w9_fire_nozzle_button_callback(2))
        self.w9_fire_nozzle3_button.clicked.connect(lambda: self.w9_fire_nozzle_button_callback(3))
        self.w9_admin_button.clicked.connect(self.edit_pulse_durations )

        self.w9b_try_again_button.clicked.connect(lambda: self.w9b_try_again_button_callback())

        self.w9c_blast_sec_scrollbar.valueChanged.connect(lambda: self.w9c_blast_sec_scrollbar_callback())
        self.w9c_nozzle_t_scrollbar.valueChanged.connect(lambda: self.w9c_nozzle_t_scrollbar_callback())
        self.w9c_nozzle_psi_scrollbar.valueChanged.connect(lambda: self.w9c_nozzle_psi_scrollbar_callback())
        self.w9c_vessel_t_scrollbar.valueChanged.connect(lambda: self.w9c_vessel_t_scrollbar_callback())

        self.w9c_save_new_startup_sp_button.clicked.connect(lambda: self.w9c_save_new_startup_sp_button_callback())
        self.w9c_load_startup_sp_button.clicked.connect(lambda: self.w9c_load_startup_sp_button_callback())
        self.w9c_run_changed_sp_button.clicked.connect(lambda: self.w9c_run_changed_sp_button_callback())

        self.w10_yes_button.clicked.connect(lambda: self.w10_yes_button_callback())
        self.w10_no_button.clicked.connect(lambda: self.w10_no_button_callback())

        self.w11_continue_button.clicked.connect(lambda: self.w11_continue_button_callback())

        self.w12_continue_button.clicked.connect(lambda: self.w12_continue_button_callback())

        self.w13_continue_button.clicked.connect(lambda: self.w13_continue_button_callback())
        self.w13a_continue_button.clicked.connect(lambda: self.w13a_continue_button_callback())
        self.w13b_continue_button.clicked.connect(lambda: self.w13b_continue_button_callback())

        self.w14_continue_button.clicked.connect(lambda: self.w14_continue_button_callback())

        #
        # Assign the Timer callbacks - note that you have to use the lambda statement because you are passing a function call
        # (if you don't, you get a NoneType error)
        # Reference:  https://stackoverflow.com/questions/10730131/create-dynamic-button-in-pyqt

        # self.connect( self.system_startup_timer, SIGNAL("timeout()"), self.system_startup_time_update)
        self.system_startup_timer.timeout.connect(self.system_startup_time_update)
        self.system_shutdown_timer.timeout.connect(self.system_shutdown_time_update)
        self.system_state_timer.timeout.connect(self.system_state_time_update)

        self.system_shutdown_timer_powerdown.timeout.connect(self.system_shutdown_powerdown)

        self.read_vessel_temperature_C_timer.timeout.connect(lambda: self.read_vessel_temperature_C_timer_callback())
        self.read_nozzle_temperature_C_timer.timeout.connect(lambda: self.read_nozzle_temperature_C_timer_callback())

        self.cycle_nozzle_solenoid_timer.timeout.connect(lambda: set_nozzle_solenoid(False))
        #self.set_nozzle_pressure_to_current_setpoint_timer.timeout.connect(lambda: self.set_nozzle_pressure_to_current_setpoint_timer_callback())

        self.control_vessel_and_nozzle_vessel_temperature_timer.timeout.connect(lambda: self.control_vessel_and_nozzle_vessel_temperature_timer_callback())

        # self.heat_nozzle_vessel_timer.timeout.connect(lambda: set_nozzle_vessel_heater(False))
        # self.heat_pressure_vessel_timer.timeout.connect(lambda: set_pressure_vessel_heater(False))

        # Start the system state monitoring, then bring up the spash screen
        
        #self.system_state_timer.start()
        # Display welcome screen
        self.show_w1()

        # Expand the application window
        self.showFullScreen()

        # Scale all controls and images
        self.scale_ui_to_screen()


    # Scale widgets and font styling from reference 480x272 geometry to the actual display.
    def scale_ui_to_screen(self):

        # Prevent accidentally scaling twice
        if getattr(self, "_ui_scaled", False):
            return

        self._ui_scaled = True

        import re

        # Original Pratyush GUI dimensions
        original_width = 480.0
        original_height = 272.0

        # Get actual touchscreen resolution
        screen = QtGui.QApplication.desktop().screenGeometry()

        screen_width = screen.width()
        screen_height = screen.height()

        # Horizontal and vertical scale factors
        scale_x = screen_width / original_width
        scale_y = screen_height / original_height

        # Use a common scale factor for text
        font_scale = min(scale_x, scale_y)

        print("Screen resolution: {} x {}".format(
            screen_width, screen_height
        ))

        print("Scaling: X = {:.2f}, Y = {:.2f}".format(
            scale_x, scale_y
        ))

        # Scale every direct child widget
        for widget in self.findChildren(QtGui.QWidget):

            if widget.parentWidget() != self:
                continue

            # Get the widget's original geometry
            rect = widget.geometry()

            # Scale its position and dimensions
            new_x = int(round(rect.x() * scale_x))
            new_y = int(round(rect.y() * scale_y))
            new_width = max(1, int(round(rect.width() * scale_x)))
            new_height = max(1, int(round(rect.height() * scale_y)))

            widget.setGeometry(
                new_x,
                new_y,
                new_width,
                new_height
            )

            # Background is handled separately below
            if widget == self.label_background:
                continue

            # Scale font sizes specified in stylesheets
            style = str(widget.styleSheet())

            def scale_font_size(match):
                size = float(match.group(2))
                unit = match.group(3)

                new_size = max(
                    1,
                    int(round(size * font_scale))
                )

                return "{}{}{}".format(
                    match.group(1),
                    new_size,
                    unit
                )

            if re.search(r"font-size\s*:", style, re.I):

                new_style = re.sub(
                    r"(font-size\s*:\s*)(\d+(?:\.\d+)?)(pt|px)",
                    scale_font_size,
                    style,
                    flags=re.I
                )

                widget.setStyleSheet(new_style)

            else:
                # Scale fonts that don't use explicit CSS sizes
                font = widget.font()

                if font.pointSizeF() > 0:
                    font.setPointSizeF(
                        font.pointSizeF() * font_scale
                    )
                    widget.setFont(font)

        # Make every background image fill the screen,
        # including images loaded during navigation
        self.label_background.setScaledContents(True)

        self.label_background.setGeometry(
            0,
            0,
            screen_width,
            screen_height
        )

        self.label_background.lower()



    # =========================================================================
    # 2. Welcome and startup instruction workflow
    # Main operator path: Welcome -> Startup title -> five images -> unlocked nozzle controls.
    # =========================================================================

    # Show the Welcome Continue button and set current_screen to w1.
    def show_w1(self):
        self.current_screen = "w1"
        self.w1_continue_button.show()


    # Hide the Welcome button and set the neutral CALS background.
    def hide_w1(self):
        self.w1_continue_button.hide()
        self.pixmap = QtGui.QPixmap(IMAGES_FOLDER + "/light-gray-background-with-cals-logo.png")
        self.label_background.setPixmap(self.pixmap)


    # Leave Welcome and open the Startup Instructions title screen.
    def w1_continue_button_callback(self):
        self.hide_w1()
        self.show_instruction_intro("startup")


    # Display the shared startup/shutdown heading; allow Back on startup title only.
    def show_instruction_intro(self, mode):

        self.instruction_intro_mode = mode
        self.current_screen = mode + "_intro"

        # Standard background
        self.pixmap = QtGui.QPixmap(
            IMAGES_FOLDER +
            "/light-gray-background-with-cals-logo.png"
        )
        self.label_background.setPixmap(self.pixmap)

        if mode == "startup":
            self.instruction_intro_title.setText(
                "STARTUP INSTRUCTIONS"
            )
        else:
            self.instruction_intro_title.setText(
                "SHUTDOWN INSTRUCTIONS"
            )

        self.instruction_intro_title.show()
        self.instruction_intro_title.raise_()

        # Only allow BACK during startup instructions
        if mode == "startup":
            self.instruction_intro_back.show()
            self.instruction_intro_back.raise_()
        else:
            self.instruction_intro_back.hide()

        # CONTINUE is available for both startup and shutdown
        self.instruction_intro_continue.show()
        self.instruction_intro_continue.raise_()


    # Hide shared title and navigation controls.
    def hide_instruction_intro(self):

        self.instruction_intro_title.hide()
        self.instruction_intro_back.hide()
        self.instruction_intro_continue.hide()


    # From Startup Instructions, restore the Welcome splash and show W1.
    def instruction_intro_back_clicked(self):

        # Only allow BACK from Startup Instructions
        if self.instruction_intro_mode != "startup":
            return

        # Hide Startup Instructions page
        self.hide_instruction_intro()

        # Restore the original Welcome background
        self.pixmap = QtGui.QPixmap(
            IMAGES_FOLDER + "/splash-screen-corrected.png"
        )

        self.label_background.setPixmap(self.pixmap)

        # Show Welcome screen
        self.show_w1()


    # Open first illustration of startup (W4) or shutdown (W13) and reset step index.
    def instruction_intro_continue_clicked(self):

        mode = self.instruction_intro_mode
        self.hide_instruction_intro()

        if mode == "startup":
            self.startup_step = 0
            self.show_w4()

        else:
            self.shutdown_step = 0
            self.show_w13()


    # Load five startup illustration paths and display W4 Back/Continue.
    def show_w4(self):
        self.current_screen = "w4"

        # Use images within the existing project folder
        image_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "window-background-images"
        )

        self.startup_images = [
            os.path.join(
                image_folder,
                "open-co2-tank-valve-all-the-way.png"
            ),
            os.path.join(
                image_folder,
                "turn-on-recirculating-water-bath.png"
            ),
            os.path.join(
                image_folder,
                "open-air-pressure-valve-all-the-way.png"
            ),
            os.path.join(
                image_folder,
                "air-regulator-startup-turn-knob.png"
            ),
            os.path.join(
                image_folder,
                "air-regulator-startup-set-regulator-to-85psi.png"
            )
        ]

        self.update_startup_image()
        self.w4_continue_button.show()
        self.w4_continue_button.raise_()
        self.w4_back_button.show()
        self.w4_back_button.raise_()


    # Draw the current startup image and set the last-step Continue label.
    def update_startup_image(self):

        image_path = self.startup_images[self.startup_step]

        self.pixmap = QtGui.QPixmap(image_path)

        if not self.pixmap.isNull():
            self.label_background.setPixmap(self.pixmap)
        else:
            print("ERROR: Startup image not found: " + image_path)
            self.label_background.setText(
                "Startup illustration unavailable"
            )

        # Update button text
        if self.startup_step == len(self.startup_images) - 1:
            self.w4_continue_button.setText("Go to Controls")
        else:
            self.w4_continue_button.setText("Continue")

        self.w4_back_button.setText("BACK")


    # Hide W4 controls, restore neutral background, and hide optional review warning.
    def hide_w4(self):
        self.w4_continue_button.hide()
        self.w4_back_button.hide()

        # Restore original background
        image_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "window-background-images"
        )

        self.pixmap = QtGui.QPixmap(
            os.path.join(
                image_folder,
                "light-gray-background-with-cals-logo.png"
            )
        )

        self.label_background.setPixmap(self.pixmap)

        # Hide an optional bench-test warning from earlier edits
        if hasattr(self, "w4_review_warning"):
            self.w4_review_warning.hide()


    # Advance the startup sequence; after last step send OFF commands, clear shutdown latch, and show controls.
    def w4_continue_button_callback(self):

        if self.startup_step < len(self.startup_images) - 1:

            # Move to the next startup instruction
            self.startup_step += 1
            self.update_startup_image()

        else:

            # Confirm outputs have been commanded OFF
            # before enabling a new operating session
            try:
                self.all_solenoids_off()
            except Exception as e:
                self.shutdown_latched = True
                QtGui.QMessageBox.critical(
                    self,
                    "Startup Error",
                    "Unable to command all solenoids OFF: {}".format(e)
                )
                return

            # Allow solenoid operation in the new session
            self.shutdown_latched = False

            # Leave startup instructions
            self.hide_w4()

            # Return to nozzle controls
            self.show_w9()


    # Go to preceding startup image, or to the Startup Instructions title from step one.
    def w4_back_button_callback(self):

        # Go to previous startup instruction
        if self.startup_step > 0:
            self.startup_step -= 1
            self.update_startup_image()

        else:
            self.hide_w4()
            self.show_instruction_intro("startup")



    # =========================================================================
    # 3. Current nozzle controls and pulse lifecycle
    # Individual pulse setting, on/off command, visual animation, cutoff, shutdown latch.
    # =========================================================================

    # Show three GO buttons and three time buttons, enabling them only when not shutdown-latched.
    def show_w9(self):
        # self.current_screen = "w9"
        # self.w9_fire_nozzle1_button.show()
        # self.w9_fire_nozzle2_button.show()
        # self.w9_fire_nozzle3_button.show()
        # self.w9_admin_button.show()
        # self.w9_shutdown_button.show()
        self.current_screen = "w9"

        self.w9_fire_nozzle1_button.show()
        self.w9_fire_nozzle2_button.show()
        self.w9_fire_nozzle3_button.show()

        for button in (
            self.w9_fire_nozzle1_button,
            self.w9_fire_nozzle2_button,
            self.w9_fire_nozzle3_button
        ):
            button.setEnabled(not self.shutdown_latched)

        for button in self.pulse_time_buttons.values():
            button.show()
            button.setEnabled(
                not getattr(self, "shutdown_latched", False)
            )
        #self.w9_admin_button.show()
        self.w9_shutdown_button.show()


    # Hide nozzle, duration, Admin, and shutdown buttons.
    def hide_w9(self):
        self.w9_fire_nozzle1_button.hide()
        self.w9_fire_nozzle2_button.hide()
        self.w9_fire_nozzle3_button.hide()
        self.w9_admin_button.hide()
        self.w9_shutdown_button.hide()
        for button in self.pulse_time_buttons.values():
            button.hide()


    # Open the custom five-option popup and update only the selected nozzle duration and label.
    def edit_nozzle_duration(self, nozzle_number):

        if getattr(self, "shutdown_latched", False):
            return

        if self.current_screen != "w9":
            return

        dialog = QtGui.QDialog(self)
        dialog.setWindowTitle("Pulse Time")
        dialog.setModal(True)
        dialog.setFixedSize(420, 218)

        dialog.setStyleSheet("""
            QDialog {
                background-color: #F5F6F3;
            }
            QLabel#Title {
                color: #222222;
                font-size: 18px;
                font-weight: bold;
            }
            QLabel#Subtitle {
                color: #555555;
                font-size: 12px;
            }
            QPushButton#TimeOption {
                background-color: white;
                color: #333333;
                border: 2px solid #BAC5B5;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton#TimeOption:checked {
                background-color: #9ADA3A;
                color: #253520;
                border: 2px solid #60931B;
            }
            QPushButton#Cancel {
                background-color: #E6E9E5;
                color: #333333;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#Save {
                background-color: #B31B1B;
                color: white;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
        """)

        layout = QtGui.QVBoxLayout(dialog)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Title
        title = QtGui.QLabel(
            "SOLENOID {} - PULSE TIME".format(nozzle_number)
        )
        title.setObjectName("Title")
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QtGui.QLabel(
            "Select duration in seconds"
        )
        subtitle.setObjectName("Subtitle")
        subtitle.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(subtitle)

        # Five independent duration options
        time_row = QtGui.QHBoxLayout()
        time_row.setSpacing(5)

        button_group = QtGui.QButtonGroup(dialog)
        button_group.setExclusive(True)

        for seconds in range(1, 6):

            button = QtGui.QPushButton(
                "{}s".format(seconds)
            )
            button.setObjectName("TimeOption")
            button.setCheckable(True)
            button.setMinimumHeight(55)

            button_group.addButton(button, seconds)

            if self.pulse_durations[nozzle_number] == seconds:
                button.setChecked(True)

            time_row.addWidget(button)

        layout.addLayout(time_row)

        layout.addStretch(1)

        # Bottom buttons
        footer = QtGui.QHBoxLayout()
        footer.setSpacing(8)

        cancel = QtGui.QPushButton("CANCEL")
        cancel.setObjectName("Cancel")
        cancel.setMinimumHeight(38)

        save = QtGui.QPushButton("SAVE")
        save.setObjectName("Save")
        save.setMinimumHeight(38)

        cancel.clicked.connect(dialog.reject)
        save.clicked.connect(dialog.accept)

        footer.addWidget(cancel)
        footer.addWidget(save)

        layout.addLayout(footer)

        # Center dialog on touchscreen
        screen = QtGui.QApplication.desktop().screenGeometry()
        dialog.move(
            screen.x() + (screen.width() - dialog.width()) // 2,
            screen.y() + (screen.height() - dialog.height()) // 2
        )

        # Save only if operator confirms
        if dialog.exec_() != QtGui.QDialog.Accepted:
            return

        new_duration = button_group.checkedId()

        if new_duration not in (1, 2, 3, 4, 5):
            return

        # Update ONLY the selected solenoid
        self.pulse_durations[nozzle_number] = new_duration

        self.pulse_time_buttons[nozzle_number].setText(
            "TIME: {}s".format(new_duration)
        )

        print(
            "Solenoid {} duration saved: {} seconds".format(
                nozzle_number, new_duration
            )
        )


    # Block a pulse if latched; otherwise transition W9 -> W9a for selected nozzle.
    def w9_fire_nozzle_button_callback(self, nozzle_number):
        # system_ready = self.test_system()
        # if system_ready:
        #     self.hide_w9()
        #     self.show_w9a(nozzle_number)
        # else:
        #     self.hide_w9()
        #     self.show_w9b()
        if self.shutdown_latched:
            return

        self.hide_w9()
        self.show_w9a(nozzle_number)


    # Start one selected solenoid, run its independent cutoff timer, and animate progress on a 0..1000 scale.
    def show_w9a(self, nozzle_number):

        # Prevent pulsing after shutdown
        if getattr(self, "shutdown_latched", False):
            return

        # Get the selected solenoid's pulse duration
        seconds = self.pulse_durations[nozzle_number]
        duration_ms = int(seconds * 1000)

        self.current_screen = "w9a"

        # Stop any previous animation
        self.w9a_dispensing_animation.stop()

        # Progress bar: use 1000 steps for smooth animation
        # even when the pulse duration is only 1 second
        self.w9a_dispensing_progressbar.setRange(0, 1000)
        self.w9a_dispensing_progressbar.setValue(0)

        # Configure the progress animation
        self.w9a_dispensing_animation.setDuration(duration_ms)
        self.w9a_dispensing_animation.setStartValue(0)
        self.w9a_dispensing_animation.setEndValue(1000)
        self.w9a_dispensing_animation.setEasingCurve(
            QtCore.QEasingCurve.Linear
        )

        # Show the dispensing interface
        self.w9a_dispensing_text_label.show()
        self.w9a_dispensing_progressbar.show()

        if hasattr(self, "w9a_stop_button"):
            self.w9a_stop_button.show()

        # Activate ONLY the selected solenoid
        set_nozzle_solenoid(nozzle_number, True)
        self.nozzle_solenoid_on[nozzle_number] = True

        # Start the separate automatic OFF timer
        self.solenoid_cutoff_timer.start(duration_ms)

        # Start the visual progress animation
        self.w9a_dispensing_animation.start()


    # Stop cutoff and animation, command all solenoids OFF, then return to controls if not shutdown-latched.
    def hide_w9a(self):

        # Cancel the cutoff timer
        self.solenoid_cutoff_timer.stop()

        # Stop the progress animation
        self.w9a_dispensing_animation.stop()

        # Command all solenoids OFF
        errors = []

        for number in (1, 2, 3):
            try:
                set_nozzle_solenoid(number, False)
                self.nozzle_solenoid_on[number] = False
            except Exception as e:
                errors.append(str(e))

        if errors:
            print("SOLENOID OFF ERROR: " + "; ".join(errors))
            QtGui.QMessageBox.critical(
                self,
                "OFF NOT CONFIRMED",
                "One or more solenoid OFF commands failed. "
                "Isolate the supplies manually."
            )
            return

        # Hide dispensing interface
        self.w9a_dispensing_text_label.hide()
        self.w9a_dispensing_progressbar.hide()

        # Return to controls unless shutdown is underway
        if not getattr(self, "shutdown_latched", False):
            self.show_w9()


    # Stop relevant timers/animations and request LOW on all three relays; raise on failed OFF commands.
    def all_solenoids_off(self):
        """Stop pulse timing and command all three solenoids OFF."""

        # Stop timers that can control solenoid pulses.
        for name in (
            "cycle_nozzle_solenoid_timer",
            "solenoid_cutoff_timer",
        ):
            timer = getattr(self, name, None)
            if timer is not None:
                timer.stop()

        # Stop dispensing animations.
        for name in (
            "w9a_dispensing_animation",
            "w8a_dispensing_animation",
        ):
            animation = getattr(self, name, None)
            if animation is not None:
                animation.stop()

        # Stop the legacy automatic power-down timer.
        timer = getattr(
            self, "system_shutdown_timer_powerdown", None
        )
        if timer is not None:
            timer.stop()

        # Attempt to turn OFF every solenoid independently.
        errors = []

        for number in (1, 2, 3):
            try:
                set_nozzle_solenoid(number, False)

                if hasattr(self, "nozzle_solenoid_on"):
                    self.nozzle_solenoid_on[number] = False

                print("Solenoid {}: OFF command sent".format(
                    number
                ))

            except Exception as e:
                errors.append(
                    "Solenoid {}: {}".format(number, e)
                )

        if errors:
            raise RuntimeError("; ".join(errors))


    # Latch shutdown, request all outputs OFF, hide controls, open Shutdown Instructions title; show OFF errors.
    def w9_shutdown_button_callback(self):

        # Do not permit further pulses after shutdown begins.
        self.shutdown_latched = True

        error_message = None

        # Request OFF before changing screens.
        try:
            self.all_solenoids_off()
        except Exception as e:
            error_message = str(e)

        self.hide_w9()

        # Show shutdown introduction.
        self.show_instruction_intro("shutdown")

        if error_message is not None:
            QtGui.QMessageBox.critical(
                self,
                "OFF NOT CONFIRMED",
                "One or more relay OFF commands failed.\n"
                "Isolate supplies manually and seek assistance.\n\n"
                + error_message
            )



    # =========================================================================
    # 4. Shutdown instructions and standby/wake
    # Shutdown title -> illustrated steps -> dark standby overlay -> tap to return to Welcome.
    # =========================================================================

    # Load five shutdown illustration filenames, display first image and Back/Continue controls.
    def show_w13(self):

        self.current_screen = "w13"

        # Original BeagleBone shutdown graphics
        self.shutdown_images = [
            "turn-off-batch.png",
            "close-air-pressure-valve-all-the-way.png",
            "air-regulator-shutdown-turn-knob.png",
            "air-regulator-shutdown-set-regulator-0psi.png",
            "close-co2-tank-valve-all-the-way.png"
        ]

        self.update_shutdown_image()

        self.w13_continue_button.show()
        self.w13_continue_button.raise_()
        self.w13_back_button.show()
        self.w13_back_button.raise_()


    # Load current shutdown illustration, fall back on missing file, update Continue label.
    def update_shutdown_image(self):

        image_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "window-background-images"
        )

        filename = self.shutdown_images[self.shutdown_step]
        image_path = os.path.join(image_folder, filename)

        self.pixmap = QtGui.QPixmap(image_path)

        if not self.pixmap.isNull():
            self.label_background.setPixmap(self.pixmap)
        else:
            print("ERROR: Shutdown image missing: " + image_path)
            self.label_background.clear()
            self.label_background.setText(
                "Shutdown illustration unavailable.\n"
                "Ask a trained operator for instructions."
            )

        # Change the final button text
        if self.shutdown_step == len(self.shutdown_images) - 1:
            self.w13_continue_button.setText("FINISH")
        else:
            self.w13_continue_button.setText("CONTINUE")


    # Hide shutdown illustration controls and restore neutral CALS background.
    def hide_w13(self):
        self.pixmap = QtGui.QPixmap(IMAGES_FOLDER + "/light-gray-background-with-cals-logo.png")
        self.label_background.setPixmap(self.pixmap)
        self.w13_continue_button.hide()
        self.w13_back_button.hide()


    # Advance the shutdown slideshow; after last step enter standby instead of returning Home.
    def w13_continue_button_callback(self):

        if self.shutdown_step < len(self.shutdown_images) - 1:

            # Next shutdown instruction
            self.shutdown_step += 1
            self.update_shutdown_image()

        else:

            # Final shutdown instruction completed.
            # Enter standby instead of returning Home.
            if self.enter_standby():
                self.hide_w13()


    # Return to prior shutdown image or the Shutdown Instructions title; never to controls.
    def w13_back_button_callback(self):

        if self.shutdown_step > 0:
            self.shutdown_step -= 1
            self.update_shutdown_image()

        else:
            self.hide_w13()
            self.show_instruction_intro("shutdown")


    # Latch shutdown, command all outputs OFF, then show full-screen dark tap-to-wake overlay.
    def enter_standby(self):

        # Keep the system locked during standby
        self.shutdown_latched = True

        # Command all solenoids OFF before entering standby
        try:
            self.all_solenoids_off()

        except Exception as e:
            QtGui.QMessageBox.critical(
                self,
                "Shutdown Error",
                "Unable to command all solenoids OFF:\n{}".format(e)
            )
            return False

        self.current_screen = "standby"

        # Cover the entire fullscreen window
        self.standby_button.setGeometry(self.rect())

        # Place standby over every other widget
        self.standby_button.show()
        self.standby_button.raise_()

        print("System entered standby")
        return True


    # Hide dark overlay and restore Welcome without clearing shutdown latch.
    def wake_from_standby(self):

        if self.current_screen != "standby":
            return

        # Remove dark overlay
        self.standby_button.hide()

        # Restore original Welcome image
        self.pixmap = QtGui.QPixmap(
            IMAGES_FOLDER + "/splash-screen-corrected.png"
        )

        self.label_background.setPixmap(self.pixmap)

        # Show Welcome screen
        self.show_w1()

        # Do NOT reset shutdown_latched here.
        # Startup instructions must be completed first.

        print("Standby exited - Welcome displayed")



    # =========================================================================
    # 5. Shared/historical screen views and widget visibility
    # Retained historical screens; the normal operator path uses W1/W4/W9/W9a/W13 instead.
    # =========================================================================

    # Retained helper for show confirmation screen.
    def show_confirmation_screen(self, screen_title, yes_button, no_button):
        self.current_screen = "confirmation"
        self.label_confirmation_screen_title.setText(screen_title)
        self.label_confirmation_screen_title.show()
        yes_button.show()
        no_button.show()


    # Retained helper for hide confirmation screen.
    def hide_confirmation_screen(self, back_screen_label, yes_button, no_button):
        self.current_screen = back_screen_label
        self.pixmap = QtGui.QPixmap(IMAGES_FOLDER + "/light-gray-background-with-cals-logo.png")
        self.label_confirmation_screen_title.hide()
        self.label_background.setPixmap(self.pixmap)
        yes_button.hide()
        no_button.hide()


    # Retained helper for hide controller subsystem status widgets.
    def hide_controller_subsystem_status_widgets(self):
        self.solenoid1_label.hide()
        self.solenoid1_checkbox.hide()
        self.solenoid1_test_button.hide()

        self.solenoid2_test_button.hide()
        self.solenoid2_checkbox.hide()
        self.solenoid2_label.hide()

        self.solenoid3_test_button.hide()
        self.solenoid3_checkbox.hide()
        self.solenoid3_label.hide()


    # Retained helper for show controller subsystem status widgets.
    def show_controller_subsystem_status_widgets(self):
        self.solenoid1_label.show()
        self.solenoid1_checkbox.show()
        self.solenoid1_test_button.show()

        self.solenoid2_test_button.show()
        self.solenoid2_checkbox.show()
        self.solenoid2_label.show()

        self.solenoid3_test_button.show()
        self.solenoid3_checkbox.show()
        self.solenoid3_label.show()


    # Display the historical W2 screen and its associated widgets.
    def show_w2(self):
        self.current_screen = "w2"
        self.w2_screen_title_label.show()
        self.show_controller_subsystem_status_widgets()
        self.w2_abort_button.show()
        self.w2_continue_button.show()
        self.system_in_startup = True


    # Hide the historical W2 widgets and restore/hide associated screen elements.
    def hide_w2(self):
        self.w2_screen_title_label.hide()
        self.hide_controller_subsystem_status_widgets()
        self.w2_abort_button.hide()
        self.w2_continue_button.hide()


    # Display the historical W2A screen and its associated widgets.
    def show_w2a(self):
        self.current_screen = "w2a"
        self.w2a_screen_title.show()
        self.show_controller_subsystem_status_widgets()
        self.w2_abort_button.hide()
        self.w2a_shutdown_button.show()


    # Hide the historical W2A widgets and restore/hide associated screen elements.
    def hide_w2a(self):
        self.w2a_screen_title.hide()
        self.hide_controller_subsystem_status_widgets()
        self.w2a_shutdown_button.hide()


    # Display the historical W2B screen and its associated widgets.
    def show_w2b(self):
        self.current_screen = "w2b"
        self.w2b_screen_title.show()
        self.w2b_screen_message.show()


    # Hide the historical W2B widgets and restore/hide associated screen elements.
    def hide_w2b(self):
        self.w2b_screen_title.hide()
        self.w2b_screen_message.hide()


    # Display the historical W3 screen and its associated widgets.
    def show_w3(self):
        self.current_screen = "w3"
        self.w3_screen_title_label.show()
        self.show_controller_subsystem_status_widgets()
        # self.w3_shutdown_button.show()
        self.w2_abort_button.hide()
        self.w3_continue_button.show()


    # Hide the historical W3 widgets and restore/hide associated screen elements.
    def hide_w3(self):
        self.w3_screen_title_label.hide()
        self.w3_continue_button.hide()
        self.hide_controller_subsystem_status_widgets()


    # Display the historical W5 screen and its associated widgets.
    def show_w5(self):
        self.current_screen = "w5"
        self.w5_turn_on_button.show()
        self.pixmap = QtGui.QPixmap(IMAGES_FOLDER + "/turn-on-recirculating-water-bath.png")
        self.label_background.setPixmap(self.pixmap)


    # Hide the historical W5 widgets and restore/hide associated screen elements.
    def hide_w5(self):
        self.pixmap = QtGui.QPixmap(IMAGES_FOLDER + "/light-gray-background-with-cals-logo.png")
        self.label_background.setPixmap(self.pixmap)
        self.w5_turn_on_button.hide()
        self.show_w5a()


    # Display the historical W5A screen and its associated widgets.
    def show_w5a(self):
        self.current_screen = "w5a"
        self.w5a_label_title.show()
        self.w5a_power_button.show()
        self.turn_on_water_bath_timer.start()


    # Hide the historical W5A widgets and restore/hide associated screen elements.
    def hide_w5a(self):
        self.w5a_label_title.hide()
        self.w5a_power_button.hide()
        self.turn_on_water_bath_timer.stop()
        self.show_w6()


    # Display the historical W5B screen and its associated widgets.
    def show_w5b(self):
        self.current_screen = "w5b"
        self.w5b_continue_button.show()
        self.pixmap = QtGui.QPixmap(IMAGES_FOLDER + "/air-regulator-startup-set-regulator-to-85psi.png")
        self.label_background.setPixmap(self.pixmap)


    # Hide the historical W5B widgets and restore/hide associated screen elements.
    def hide_w5b(self):
        self.pixmap = QtGui.QPixmap(IMAGES_FOLDER + "/light-gray-background-with-cals-logo.png")
        self.label_background.setPixmap(self.pixmap)
        self.w5b_continue_button.hide()
        self.show_w6()


    # Retained helper for hide system startup widgets.
    def hide_system_startup_widgets(self):
        self.vessel_psi_text_label.hide()
        self.vessel_pressure_PSI_progressbar.hide()
        self.vessel_pressure_checkbox.hide()
        self.vessel_heater_on_indicator_label.hide()

        self.vessel_temp_C_text_label.hide()
        self.vessel_temp_C_progressbar.hide()
        self.vessel_temp_checkbox.hide()

        self.nozzle_psi_text_label.hide()
        self.nozzle_pressure_PSI_progressbar.hide()
        self.nozzle_pressure_checkbox.hide()

        self.nozzle_temp_C_text_label.hide()
        self.nozzle_temp_C_progressbar.hide()
        self.nozzle_temp_checkbox.hide()
        self.nozzle_heater_on_indicator_label.hide()


    # Retained helper for show system startup widgets.
    def show_system_startup_widgets(self):
        self.vessel_psi_text_label.show()
        self.vessel_pressure_PSI_progressbar.show()
        self.vessel_pressure_checkbox.show()
        # self.vessel_heater_on_indicator_label.show()

        self.vessel_temp_C_text_label.show()
        self.vessel_temp_C_progressbar.show()
        self.vessel_temp_checkbox.show()

        self.nozzle_psi_text_label.show()
        self.nozzle_pressure_PSI_progressbar.show()
        self.nozzle_pressure_checkbox.show()

        self.nozzle_temp_C_text_label.show()
        self.nozzle_temp_C_progressbar.show()
        self.nozzle_temp_checkbox.show()


    # Display the historical W6 screen and its associated widgets.
    def show_w6(self):
        self.current_screen = "w6"
        self.w6_screen_title_label.show()
        self.w6_abort_button.show()
        self.w6_continue_button.show()
        self.show_system_startup_widgets()
        self.system_in_startup = True
        # set_alicat_pressure(self.setpoint_current_nozzle_pressure_PSI)
        self.set_nozzle_pressure_to_current_setpoint_timer.start()
        self.system_startup_timer.start()


    # Hide the historical W6 widgets and restore/hide associated screen elements.
    def hide_w6(self):
        self.w6_screen_title_label.hide()
        self.w6_abort_button.hide()
        self.w6_continue_button.hide()
        self.hide_system_startup_widgets()
        self.system_startup_timer.stop()


    # Display the historical W6A screen and its associated widgets.
    def show_w6a(self):
        self.current_screen = "w6a"
        self.w6a_screen_title_label.show()
        self.w6a_screen_message.show()
        self.w6a_shutdown_button.show()
        self.w6a_back_button.show()
        self.system_startup_timer.stop()


    # Hide the historical W6A widgets and restore/hide associated screen elements.
    def hide_w6a(self):
        self.w6a_screen_title_label.hide()
        self.w6a_screen_message.hide()
        self.w6a_back_button.hide()
        self.w6a_shutdown_button.hide()


    # Display the historical W7 screen and its associated widgets.
    def show_w7(self):
        self.current_screen = "w7"
        self.system_startup_final_time()
        self.w7_screen_title_label.show()
        self.w7_continue_button.show()
        self.show_system_startup_widgets()
        self.system_startup_timer.stop()


    # Hide the historical W7 widgets and restore/hide associated screen elements.
    def hide_w7(self):
        self.w7_screen_title_label.hide()
        self.w7_continue_button.hide()
        self.hide_system_startup_widgets()


    # Display the historical W8 screen and its associated widgets.
    def show_w8(self):
        self.current_screen = "w8"
        self.w8_purge_nozzle_button1.show()
        self.w8_purge_nozzle_button2.show()
        self.w8_purge_nozzle_button3.show()
        self.w8_continue_button.show()


    # Hide the historical W8 widgets and restore/hide associated screen elements.
    def hide_w8(self):
        self.w8_purge_nozzle_button1.hide()
        self.w8_purge_nozzle_button2.hide()
        self.w8_purge_nozzle_button3.hide()
        self.w8_continue_button.hide()


    # Display the historical W8A screen and its associated widgets.
    def show_w8a(self, nozzle_number):
        self.current_screen = "w8a"
        self.w8a_dispensing_text_label.show()
        self.w8a_dispensing_progressbar.show()

        set_nozzle_solenoid(nozzle_number, True)

        self.w8a_dispensing_animation.start()


    # Hide the historical W8A widgets and restore/hide associated screen elements.
    def hide_w8a(self):
        self.w8a_dispensing_text_label.hide()
        self.w8a_dispensing_progressbar.hide()
        for key, value in SOLENOID_NUMBER_PIN.items():
            set_nozzle_solenoid(key, False)
            self.nozzle_solenoid_on[key] = False
        self.show_w8()


    # Display the historical W10 screen and its associated widgets.
    def show_w10(self):
        self.current_screen = "w10"
        self.w10_screen_title_label.show()
        self.w10_yes_button.show()
        self.w10_no_button.show()


    # Hide the historical W10 widgets and restore/hide associated screen elements.
    def hide_w10(self):
        self.w10_screen_title_label.hide()
        self.w10_yes_button.hide()
        self.w10_no_button.hide()


    # Display the historical W11 screen and its associated widgets.
    def show_w11(self):
        self.current_screen = "w11"
        #
        # Turn off all relays and set the Alicat pressure controller to zero
        self.control_vessel_and_nozzle_vessel_temperature_timer.stop()
        set_nozzle_vessel_heater(False)
        set_pressure_vessel_heater(False)
        set_nozzle_solenoid(1, False)
        set_nozzle_solenoid(2, False)
        set_nozzle_solenoid(3, False)

        #
        # Change temperature operating ranges so that the heaters will not never turn on
        # (heaters only turn on if the current temperature goes below the lower end of operating range)
        self.operatingRange_nozzle_temperature_C = (0, 1)
        self.operatingRange_vessel_temperature_C = (0, 1)
        # self.setpoint_current_vessel_pressure_PSI    =       800
        # self.setpoint_current_nozzle_temperature_C   =        0
        # self.setpoint_current_nozzle_pressure_PSI    =        0
        # self.setpoint_current_nozzle_pressure_PSI_tolerance = 10
        # self.setpoint_current_blast_sec             =          2.5
        # set_alicat_pressure(0)
        self.setpoint_current_nozzle_pressure_PSI = 0
        self.set_nozzle_pressure_to_current_setpoint_timer.start()
        #
        # Change the system startup widget checkbox labels
        self.vessel_pressure_checkbox.setText("Venting...")
        self.vessel_temp_checkbox.setText("Cooling...")
        self.nozzle_pressure_checkbox.setText("Venting...")
        self.nozzle_temp_checkbox.setText("Cooling...")

        #
        # Show the screen's widgets
        self.w11_screen_title_label.show()
        self.w11_continue_button.show()
        self.show_system_startup_widgets()
        #
        # Set the appropriate states for startup and shutdown
        self.system_in_startup = False
        self.system_in_shutdown = True
        #
        # Set the shutdown timer and progressbar
        # self.pressure_controller_etime = self.pressure_controller_shutdown_time_seconds
        # self.nozzle_pressure_PSI_progressbar.setMaximum(self.pressure_controller_shutdown_time_seconds)

        self.system_shutdown_timer.start()


    # Hide the historical W11 widgets and restore/hide associated screen elements.
    def hide_w11(self):
        self.w11_screen_title_label.hide()
        self.w11_continue_button.hide()
        self.hide_system_startup_widgets()
        self.system_shutdown_timer.stop()


    # Display the historical W12 screen and its associated widgets.
    def show_w12(self):
        self.current_screen = "w12"
        self.system_shutdown_final_time()
        self.w12_screen_title_label.show()
        self.w12_continue_button.show()
        self.show_system_startup_widgets()


    # Hide the historical W12 widgets and restore/hide associated screen elements.
    def hide_w12(self):
        self.w12_screen_title_label.hide()
        self.w12_continue_button.hide()
        self.hide_system_startup_widgets()


    # Display the historical W13A screen and its associated widgets.
    def show_w13a(self):
        self.current_screen = "w13a"
        self.pixmap = QtGui.QPixmap(IMAGES_FOLDER + "/air-regulator-shutdown-turn-knob.png")
        self.label_background.setPixmap(self.pixmap)
        self.w13a_continue_button.show()


    # Hide the historical W13A widgets and restore/hide associated screen elements.
    def hide_w13a(self):
        self.pixmap = QtGui.QPixmap(IMAGES_FOLDER + "/light-gray-background-with-cals-logo.png")
        self.label_background.setPixmap(self.pixmap)
        self.w13a_continue_button.hide()


    # Display the historical W13B screen and its associated widgets.
    def show_w13b(self):
        self.current_screen = "w13b"
        self.pixmap = QtGui.QPixmap(IMAGES_FOLDER + "/air-regulator-shutdown-set-regulator-0psi.png")
        self.label_background.setPixmap(self.pixmap)
        self.w13b_continue_button.show()


    # Hide the historical W13B widgets and restore/hide associated screen elements.
    def hide_w13b(self):
        self.pixmap = QtGui.QPixmap(IMAGES_FOLDER + "/light-gray-background-with-cals-logo.png")
        self.label_background.setPixmap(self.pixmap)
        self.w13b_continue_button.hide()


    # Display the historical W14 screen and its associated widgets.
    def show_w14(self):
        self.current_screen = "w14"
        self.pixmap = QtGui.QPixmap(IMAGES_FOLDER + "/close-co2-tank-valve-all-the-way.png")
        self.label_background.setPixmap(self.pixmap)
        self.w14_continue_button.show()


    # Hide the historical W14 widgets and restore/hide associated screen elements.
    def hide_w14(self):
        self.pixmap = QtGui.QPixmap(IMAGES_FOLDER + "/light-gray-background-with-cals-logo.png")
        self.label_background.setPixmap(self.pixmap)
        self.w14_continue_button.hide()


    # Display the historical W15 screen and its associated widgets.
    def show_w15(self):
        self.current_screen = "w15"
        self.pixmap = QtGui.QPixmap(IMAGES_FOLDER + "/light-gray-background-with-cals-logo.png")
        self.label_background.setPixmap(self.pixmap)
        self.w15_screen_title_label.show()
        self.w15_screen_message_label.show()


    # Hide the historical W15 widgets and restore/hide associated screen elements.
    def hide_w15(self):
        self.pixmap = QtGui.QPixmap(IMAGES_FOLDER + "/light-gray-background-with-cals-logo.png")
        self.label_background.setPixmap(self.pixmap)
        self.w15_screen_title_label.hide()
        self.w15_screen_message_label.hide()



    # =========================================================================
    # 6. Retained legacy screen-event callbacks
    # Existing legacy callbacks, some still wired to historical widgets; not part of current usual workflow.
    # =========================================================================

    # Handle the historical w2 back button event; see method body for its exact UI actions.
    def w2_back_button_callback(self):
        self.w2_back_button.hide()
        self.hide_confirmation_screen("w2", self.w2a_shutdown_button, self.w2_continue_confirm_button)
        self.show_w2()


    # Handle the historical w2 abort button event; see method body for its exact UI actions.
    def w2_abort_button_callback(self):
        self.hide_w2()
        self.show_confirmation_screen(
            "Are you sure you want to abort?",
            self.w2a_shutdown_button,
            self.w2_back_button,
        )


    # Historical W2 relay test: energizes selected relay and starts legacy cycle timer.
    def solenoid_status_test_button_callback(self, nozzle_number):
        print("Testing Nozzle " + str(nozzle_number) + " connected at Pin " + str(SOLENOID_NUMBER_PIN.get(nozzle_number)))
        set_nozzle_solenoid(nozzle_number, True)
        self.cycle_nozzle_solenoid_timer.start()


    # Handle the historical w2 continue button event; see method body for its exact UI actions.
    def w2_continue_button_callback(self):
        self.hide_w2()
        self.show_confirmation_screen(
            "Are you sure you want to continue",
            self.w2_continue_confirm_button,
            self.w2_back_button,
        )


    # Handle the historical w2 continue confirm event; see method body for its exact UI actions.
    def w2_continue_confirm_callback(self):
        self.hide_w2()
        self.w2_back_button.hide()
        self.hide_confirmation_screen("w3", self.w2_continue_confirm_button, self.w2_continue_button)
        self.show_w3()


    # Handle the historical w2a shutdown button event; see method body for its exact UI actions.
    def w2a_shutdown_button_callback(self):
        self.hide_w2a()
        self.hide_confirmation_screen("w13", self.w2a_shutdown_button, self.w2_back_button)
        self.show_w13()


    # Handle the historical w3 continue button event; see method body for its exact UI actions.
    def w3_continue_button_callback(self):
        self.hide_w3()
        self.show_w4()


    # Handle the historical w5 turn on button event; see method body for its exact UI actions.
    def w5_turn_on_button_callback(self):
        self.hide_w5()
        self.show_w5a()


    # Handle the historical w5a power button event; see method body for its exact UI actions.
    def w5a_power_button_callback(self):
        self.hide_w5a()
        self.show_w6()


    # Handle the historical turn on water bath timer event; see method body for its exact UI actions.
    def turn_on_water_bath_timer_callback(self):
        self.hide_w5()
        self.hide_w5a()
        self.show_w6()


    # Handle the historical w5b continue button event; see method body for its exact UI actions.
    def w5b_continue_button_callback(self):
        self.hide_w5b()
        self.show_w6()


    # Handle the historical w6 abort button event; see method body for its exact UI actions.
    def w6_abort_button_callback(self):
        self.hide_w6()
        self.show_w6a()


    # Handle the historical w6 shutdown button event; see method body for its exact UI actions.
    def w6_shutdown_button_callback(self):
        self.hide_w6()
        self.show_w6a()


    # Handle the historical w6a back button event; see method body for its exact UI actions.
    def w6a_back_button_callback(self):
        self.hide_w6a()
        self.show_w6()


    # Handle the historical w6a shutdown button event; see method body for its exact UI actions.
    def w6a_shutdown_button_callback(self):
        self.hide_w6a()
        self.show_w10()


    # Handle the historical w6 continue button event; see method body for its exact UI actions.
    def w6_continue_button_callback(self):
        self.hide_w6()
        self.show_w7()


    # Handle the historical w7 continue button event; see method body for its exact UI actions.
    def w7_continue_button_callback(self):
        self.hide_w7()
        self.show_w8()


    # Handle the historical w8 continue button event; see method body for its exact UI actions.
    def w8_continue_button_callback(self):
        self.hide_w8()
        self.show_w9()


    # Handle the historical w8 purge nozzle button event; see method body for its exact UI actions.
    def w8_purge_nozzle_button_callback(self, nozzle_number):
        self.hide_w8()
        self.show_w8a(nozzle_number)


    # Handle the historical w10 yes button event; see method body for its exact UI actions.
    def w10_yes_button_callback(self):
        self.hide_w10()
        self.show_w13()


    # Handle the historical w10 no button event; see method body for its exact UI actions.
    def w10_no_button_callback(self):
        self.hide_w10()
        self.show_w6()


    # Handle the historical w11 continue button event; see method body for its exact UI actions.
    def w11_continue_button_callback(self):
        self.hide_w11()
        self.show_w12()


    # Handle the historical w12 continue button event; see method body for its exact UI actions.
    def w12_continue_button_callback(self):
        self.hide_w12()
        self.show_w13()


    # Handle the historical w13a continue button event; see method body for its exact UI actions.
    def w13a_continue_button_callback(self):
        self.hide_w13a()
        self.show_w13b()


    # Handle the historical w13b continue button event; see method body for its exact UI actions.
    def w13b_continue_button_callback(self):
        self.hide_w13b()
        self.show_w14()


    # Historical W14 continuation that starts the old powerdown timer; not used in current W13-to-standby path.
    def w14_continue_button_callback(self):
        self.hide_w14()
        self.show_w15()
        self.system_shutdown_timer_powerdown.start()



    # =========================================================================
    # 7. Retained administrative/alternative pulse controls
    # Old Admin and alternate pulse editor retained unchanged; W9 currently shows per-nozzle TIME buttons.
    # =========================================================================

    # Retained dialog to edit all three independent durations (the normal W9 Admin button is hidden).
    def edit_pulse_durations(self):

        if getattr(self, "shutdown_latched", False):
            return

        dialog = QtGui.QDialog(self)
        dialog.setWindowTitle("Pulse Durations")

        layout = QtGui.QFormLayout(dialog)
        spinboxes = {}

        for number in (1, 2, 3):
            spin = QtGui.QSpinBox(dialog)

            spin.setRange(1, 5)
            spin.setSingleStep(1)
            spin.setSuffix(" s")
            spin.setValue(self.pulse_durations[number])
            spin.setMinimumHeight(35)

            layout.addRow(
                "Solenoid {}:".format(number),
                spin
            )

            spinboxes[number] = spin

        buttons = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Save |
            QtGui.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal,
            dialog
        )

        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec_() == QtGui.QDialog.Accepted:

            for number in (1, 2, 3):
                self.pulse_durations[number] = (
                    spinboxes[number].value()
                )

            self.update_pulse_labels()


    # Retained alternate label formatter that writes durations onto GO buttons.
    def update_pulse_labels(self):

        self.w9_fire_nozzle1_button.setText(
            "Go Nozzle 1 ({}s)".format(
                self.pulse_durations[1]
            )
        )

        self.w9_fire_nozzle2_button.setText(
            "Go Nozzle 2 ({}s)".format(
                self.pulse_durations[2]
            )
        )

        self.w9_fire_nozzle3_button.setText(
            "Go Nozzle 3 ({}s)".format(
                self.pulse_durations[3]
            )
        )


    # Open historical W9c admin screen (not invoked by W9 per-nozzle time controls).
    def w9_admin_button_callback(self):
        self.hide_w9()
        self.show_w9c()


    # Display the historical W9B screen and its associated widgets.
    def show_w9b(self):
        current_temperature = self.get_nozzle_vessel_temperature()
        current_pressure = self.get_pressure_vessel_temperature()

        self.w9b_screen_title_label.show()
        self.w9b_temperature_pressure_label.setText("Temperature: %4.1f, Pressure: %4.1f" % (current_temperature, current_pressure))
        self.w9b_temperature_pressure_label.show()
        message_label = ""
        if current_pressure < 520:
            message_label = "The pressure in the vessel is too low to dispense ice cream."
        elif current_temperature > 1:
            message_label = "The temperature in the vessel is too high to dispense ice cream."
        else:
            message_label = "Both the temperature and pressure are not within the operating range to dispense ice cream."
        self.w9b_message_label.setText(message_label)
        self.w9b_message_label.show()
        self.w9b_try_again_button.show()


    # Hide the historical W9B widgets and restore/hide associated screen elements.
    def hide_w9b(self):
        self.w9b_screen_title_label.hide()
        self.w9b_temperature_pressure_label.hide()
        self.w9b_message_label.hide()
        self.w9b_try_again_button.hide()


    # Display the historical W9C screen and its associated widgets.
    def show_w9c(self):
        self.current_screen = "w9c"
        self.pixmap = QtGui.QPixmap(IMAGES_FOLDER + "/light-gray-background.png")
        self.label_background.setPixmap(self.pixmap)
        self.w9c_admin_text_label.show()

        self.w9c_realtime_sp_text_label.show()
        self.w9c_change_sp_text_label.show()

        self.w9c_blast_sec_text_label.show()
        self.w9c_blast_sec_scrollbar.show()

        self.w9c_nozzle_t_text_label.show()
        self.w9c_nozzle_t_scrollbar.show()

        self.w9c_nozzle_psi_text_label.show()
        self.w9c_nozzle_psi_scrollbar.show()

        self.w9c_vessel_t_text_label.show()
        self.w9c_vessel_t_scrollbar.show()

        self.w9c_vessel_psi_text_label.show()

        self.w9c_load_startup_sp_button.show()
        self.w9c_save_new_startup_sp_button.show()
        self.w9c_run_changed_sp_button.show()


    # Hide the historical W9C widgets and restore/hide associated screen elements.
    def hide_w9c(self):
        self.pixmap = QtGui.QPixmap(IMAGES_FOLDER + "/light-gray-background-with-cals-logo.png")
        self.label_background.setPixmap(self.pixmap)
        self.w9c_admin_text_label.hide()

        self.w9c_realtime_sp_text_label.hide()
        self.w9c_change_sp_text_label.hide()

        self.w9c_blast_sec_text_label.hide()
        self.w9c_blast_sec_scrollbar.hide()

        self.w9c_nozzle_t_text_label.hide()
        self.w9c_nozzle_t_scrollbar.hide()

        self.w9c_nozzle_psi_text_label.hide()
        self.w9c_nozzle_psi_scrollbar.hide()

        self.w9c_vessel_t_text_label.hide()
        self.w9c_vessel_t_scrollbar.hide()

        self.w9c_vessel_psi_text_label.hide()

        self.w9c_load_startup_sp_button.hide()
        self.w9c_save_new_startup_sp_button.hide()
        self.w9c_run_changed_sp_button.hide()


    # Handle the historical w9b try again button event; see method body for its exact UI actions.
    def w9b_try_again_button_callback(self):
        self.hide_w9b()
        self.show_w9()


    # Handle the historical w9c blast sec scrollbar event; see method body for its exact UI actions.
    def w9c_blast_sec_scrollbar_callback(self):
        ival = self.w9c_blast_sec_scrollbar.value()
        a = self.scrollbar_blast_sec_values[ival]
        b = self.scrollbar_blast_sec_values.index(self.scrollbar_limits_blast_sec[3])
        c = self.scrollbar_blast_sec_values[b]
        new_text = "Blast  (sec) =   %4.1f,[%4.1f]" % (
            a,
            self.setpoint_current_blast_sec,
        )
        self.w9c_blast_sec_text_label.setText(new_text)


    # Handle the historical w9c nozzle t scrollbar event; see method body for its exact UI actions.
    def w9c_nozzle_t_scrollbar_callback(self):
        ival = self.w9c_nozzle_t_scrollbar.value()
        a = self.scrollbar_nozzle_temperature_C_values[ival]
        b = self.scrollbar_nozzle_temperature_C_values.index(self.scrollbar_limits_nozzle_temperature_C[3])
        c = self.scrollbar_nozzle_temperature_C_values[b]
        new_text = "Nozzle (T C) =   %4i,[%4i]" % (
            a,
            self.setpoint_current_nozzle_temperature_C,
        )
        self.w9c_nozzle_t_text_label.setText(new_text)


    # Handle the historical w9c nozzle psi scrollbar event; see method body for its exact UI actions.
    def w9c_nozzle_psi_scrollbar_callback(self):
        ival = self.w9c_nozzle_psi_scrollbar.value()
        a = self.scrollbar_limits_nozzle_pressure_PSI_values[ival]
        b = self.scrollbar_limits_nozzle_pressure_PSI_values.index(self.scrollbar_limits_nozzle_pressure_PSI[3])
        c = self.scrollbar_limits_nozzle_pressure_PSI_values[b]
        # print "read nozzle pressure = %d"%self.setpoint_current_nozzle_pressure_PSI
        new_text = "Nozzle (psi) =   %4i,[%4i]" % (
            a,
            self.setpoint_current_nozzle_pressure_PSI,
        )
        self.w9c_nozzle_psi_text_label.setText(new_text)


    # Handle the historical w9c vessel t scrollbar event; see method body for its exact UI actions.
    def w9c_vessel_t_scrollbar_callback(self):
        ival = self.w9c_vessel_t_scrollbar.value()
        a = self.scrollbar_limits_vessel_temperature_C_values[ival]
        b = self.scrollbar_limits_vessel_temperature_C_values.index(self.scrollbar_limits_vessel_temperature_C[3])
        c = self.scrollbar_limits_vessel_temperature_C_values[b]
        new_text = "Vessel (T C) =   %4i,[%4i]" % (a, c)
        self.w9c_vessel_t_text_label.setText(new_text)


    # Handle the historical w9c load startup sp button event; see method body for its exact UI actions.
    def w9c_load_startup_sp_button_callback(self):
        self.load_startup_setpoint_vessel_temperature_C()
        self.load_startup_setpoint_vessel_pressure_PSI()
        self.load_startup_setpoint_nozzle_temperature_C()
        self.load_startup_setpoint_nozzle_pressure_PSI()
        self.load_startup_blast_sec()
        #
        # Now have to update system variables and the w9c scrollbars and their labels
        #
        # Check and adjust the maximum setpoint temperatures so the upper operating band won't exeed 42C (the upper safe range)
        if self.setpoint_current_vessel_temperature_C > 39:
            self.setpoint_current_vessel_temperature_C = 39

        if self.setpoint_current_nozzle_temperature_C > 40:
            self.setpoint_current_vessel_temperature_C = 40

        if self.setpoint_current_vessel_pressure_PSI > 1450:
            self.setpoint_current_vessel_pressure_PSI = 1450

        if self.setpoint_current_nozzle_pressure_PSI > 1450:
            self.setpoint_current_nozzle_pressure_PSI = 1450

        #
        # nothing happens when I call the scrollbar callbacks directly, or use the update or repaint methods
        # self.w9c_blast_sec_scrollbar_callback()
        # self.w9c_blast_sec_scrollbar.update()
        # self.w9c_blast_sec_scrollbar.repaint()

        # self.w9c_nozzle_t_scrollbar_callback()
        # self.w9c_nozzle_psi_scrollbar_callback()
        # self.w9c_vessel_t_scrollbar_callback()

        self.w9c_blast_sec_scrollbar.setValue(self.scrollbar_blast_sec_values.index(self.setpoint_current_blast_sec))
        # ival = self.w9c_blast_sec_scrollbar.value()
        # a = self.scrollbar_blast_sec_values[ival]
        # b = self.scrollbar_blast_sec_values.index(self.scrollbar_limits_blast_sec[3])
        # c = self.scrollbar_blast_sec_values[b]
        new_text = "Blast  (sec) =   %4.1f,[%4.1f]" % (
            self.setpoint_current_blast_sec,
            self.setpoint_current_blast_sec,
        )
        self.w9c_blast_sec_text_label.setText(new_text)

        self.w9c_nozzle_t_scrollbar.setValue(self.scrollbar_nozzle_temperature_C_values.index(self.setpoint_current_nozzle_temperature_C))
        # ival = self.w9c_nozzle_t_scrollbar.value()
        # a = self.scrollbar_nozzle_temperature_C_values [ival]
        # b = self.scrollbar_nozzle_temperature_C_values.index(self.scrollbar_limits_nozzle_temperature_C[3])
        # c = self.scrollbar_nozzle_temperature_C_values[b]
        new_text = "Nozzle (T C) =   %4i,[%4i]" % (
            self.setpoint_current_nozzle_temperature_C,
            self.setpoint_current_nozzle_temperature_C,
        )
        self.w9c_nozzle_t_text_label.setText(new_text)

        self.w9c_nozzle_psi_scrollbar.setValue(self.scrollbar_limits_nozzle_pressure_PSI_values.index(self.setpoint_current_nozzle_pressure_PSI))
        # ival = self.w9c_nozzle_psi_scrollbar.value()
        # a = self.scrollbar_limits_nozzle_pressure_PSI_values[ival]
        # b = self.scrollbar_limits_nozzle_pressure_PSI_values.index(self.scrollbar_limits_nozzle_pressure_PSI[3])
        # c = self.scrollbar_limits_nozzle_pressure_PSI_values[b]
        # print "read nozzle pressure = %d"%self.setpoint_current_nozzle_pressure_PSI
        new_text = "Nozzle (psi) =   %4i,[%4i]" % (
            self.setpoint_current_nozzle_pressure_PSI,
            self.setpoint_current_nozzle_pressure_PSI,
        )
        self.w9c_nozzle_psi_text_label.setText(new_text)

        self.w9c_vessel_t_scrollbar.setValue(self.scrollbar_limits_vessel_temperature_C_values.index(self.setpoint_current_vessel_temperature_C))
        # ival = self.w9c_vessel_t_scrollbar.value()
        # a = self.scrollbar_limits_vessel_temperature_C_values[ival]
        # b = self.scrollbar_limits_vessel_temperature_C_values.index(self.scrollbar_limits_vessel_temperature_C[3])
        # c = self.scrollbar_limits_vessel_temperature_C_values[b]
        new_text = "Vessel (T C) =   %4i,[%4i]" % (
            self.setpoint_current_vessel_temperature_C,
            self.setpoint_current_vessel_temperature_C,
        )
        self.w9c_vessel_t_text_label.setText(new_text)


    # Handle the historical w9c save new startup sp button event; see method body for its exact UI actions.
    def w9c_save_new_startup_sp_button_callback(self):
        #
        # Save setpoints to the STARTUP_SETPOINTS directory
        self.w9c_save_new_startup_sp_button.setText("Saving...")
        self.save_startup_setpoint_vessel_temperature_C()
        self.save_startup_setpoint_nozzle_temperature_C()
        self.save_startup_setpoint_nozzle_pressure_PSI()
        self.save_startup_blast_sec()
        self.w9c_save_new_startup_sp_button.setText("Save New Startup sp")


    # Handle the historical w9c run changed sp button event; see method body for its exact UI actions.
    def w9c_run_changed_sp_button_callback(self):
        #
        # Update blast setpoint value and update the dispensing animations accordingly
        i_sec = self.w9c_blast_sec_scrollbar.value()
        new_blast_sec = self.scrollbar_blast_sec_values[i_sec]
        self.setpoint_current_blast_sec = new_blast_sec
        new_text = "Blast  (sec) =   %4.1f,[%4.1f]" % (
            self.setpoint_current_blast_sec,
            self.setpoint_current_blast_sec,
        )
        self.w9c_blast_sec_text_label.setText(new_text)

        new_dispensing_time = self.setpoint_current_blast_sec * 1000.0 - self.solenoid_timer_machine_error
        print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n new dispensing time", new_dispensing_time)
        self.w8a_dispensing_animation.setDuration(new_dispensing_time)
        # self.w8a_dispensing_progressbar.setMaximum(self.setpoint_current_blast_sec)
        self.w9a_dispensing_animation.setDuration(new_dispensing_time)
        # self.w9a_dispensing_progressbar.setMaximum(self.setpoint_current_blast_sec // 0.5)

        #
        # Update the current setpoint nozzle pressure value and update scrollbar label
        ival = self.w9c_nozzle_psi_scrollbar.value()
        self.setpoint_current_nozzle_pressure_PSI = self.scrollbar_limits_nozzle_pressure_PSI_values[ival]
        c = self.setpoint_current_nozzle_pressure_PSI
        new_text = "Nozzle (psi) =   %4i,[%4i]" % (c, c)
        self.w9c_nozzle_psi_text_label.setText(new_text)

        #
        # Update the current setpoint nozzle temperature value and update scrollbar label
        ival = self.w9c_nozzle_t_scrollbar.value()
        self.setpoint_current_nozzle_temperature_C = self.scrollbar_nozzle_temperature_C_values[ival]
        c = self.setpoint_current_nozzle_temperature_C
        new_text = "Nozzle (T C) =   %4i,[%4i]" % (c, c)
        self.w9c_nozzle_t_text_label.setText(new_text)

        #
        # Update the current setpoint vessel temperature value and update scrollbar label
        ival = self.w9c_vessel_t_scrollbar.value()
        self.setpoint_current_vessel_temperature_C = self.scrollbar_limits_vessel_temperature_C_values[ival]
        c = self.setpoint_current_vessel_temperature_C
        new_text = "Vessel (T C) =   %4i,[%4i]" % (c, c)
        self.w9c_vessel_t_text_label.setText(new_text)

        #
        # Adjust the current operating range values on vessel temperature and vessel nozzle temperature
        # The vessel temperature operating range is -2, +3 from the vessel temperature setpoint
        # The nozzle temperature operating range is -2, +2 from the nozzle temperature setpoint
        self.operatingRange_vessel_temperature_C = (
            self.setpoint_current_vessel_temperature_C - 2,
            self.setpoint_current_vessel_temperature_C + 3,
        )
        self.operatingRange_nozzle_temperature_C = (
            self.setpoint_current_nozzle_temperature_C - 2,
            self.setpoint_current_nozzle_temperature_C + 2,
        )

        #
        # Set the new pressure on the Alicat, hide the w9c screen, and move to the w6 screen
        self.setpoints_were_reset = True
        # set_alicat_pressure( self.setpoint_current_nozzle_pressure_PSI)
        self.set_nozzle_pressure_to_current_setpoint_timer.start()
        self.hide_w9c()
        self.show_w6()



    # =========================================================================
    # 8. Legacy timers, monitoring, and shutdown helpers
    # Historical monitoring, heater/pressure control, elapsed-time labels, and power-down callbacks.
    # =========================================================================

    # Update retained startup time update logic or display.
    def system_startup_time_update(self):
        self.elapsed_startup_time_seconds += 1
        n = self.elapsed_startup_time_seconds
        minutes = n // 60
        seconds = n % 60
        new_title = "System Startup: etime= %3i min, %2i sec" % (minutes, seconds)
        self.w6_screen_title_label.setText(new_title)


    # Update retained startup final time logic or display.
    def system_startup_final_time(self):
        n = self.elapsed_startup_time_seconds
        minutes = n // 60
        seconds = n % 60
        new_title = "<center>System Startup took %3i min, %2i sec<\center>" % (
            minutes,
            seconds,
        )
        self.w7_screen_title_label.setText(new_title)


    # Update retained shutdown time update logic or display.
    def system_shutdown_time_update(self):
        self.elapsed_shutdown_time_seconds += 1
        n = self.elapsed_shutdown_time_seconds
        minutes = n // 60
        seconds = n % 60
        new_title = "System Shutdown etime= %3i min, %2i sec" % (minutes, seconds)
        self.w11_screen_title_label.setText(new_title)


    # Update retained shutdown final time logic or display.
    def system_shutdown_final_time(self):
        n = self.elapsed_shutdown_time_seconds
        minutes = n // 60
        seconds = n % 60
        new_title = "<center>System Shutdown took %3i min, %2i sec<\center>" % (
            minutes,
            seconds,
        )
        self.w12_screen_title_label.setText(new_title)


    # Historical callback that shuts down the OS and controls old heaters; not used by current standby flow.
    def system_shutdown_powerdown(self):
        #
        # Stop the heater control process
        self.control_vessel_and_nozzle_vessel_temperature_timer.stop()
        self.system_state_timer.stop()
        #
        # Turn off all relays
        set_nozzle_solenoid(1, False)
        set_nozzle_solenoid(2, False)
        set_nozzle_solenoid(3, False)
        set_nozzle_vessel_heater(False)
        set_pressure_vessel_heater(False)
        os.system("sudo shutdown -h now")


    # Update legacy nozzle thermocouple samples on timer events.
    def read_nozzle_temperature_C_timer_callback(self):
        self.read_nozzle_temperature_C_list.pop(0)  # Remove the oldest temperature point
        #
        # Use the ADC.read method, which returns a value between 0.0 and 1.0 - multiply by 1.8
        # to get the actual volts seen by the BeagleBone Black - the BeagleBone Black analog inputs
        # work in the 0 to 1.8V range.
        #
        # The BBIO library documentation says that you must read it twice to get a reading.
        x = float(ADC.read(Nozzle_Vessel_Thermocouple_Grove_Cape_V2_AIN_2) * 1.8)
        x = float(ADC.read(Nozzle_Vessel_Thermocouple_Grove_Cape_V2_AIN_2) * 1.8)
        # Add the most recent temperature point to the list
        self.read_nozzle_temperature_C_list.append(x)


    # Update legacy vessel thermocouple samples on timer events.
    def read_vessel_temperature_C_timer_callback(self):
        self.read_vessel_temperature_C_list.pop(0)  # Remove the oldest temperature point from the list
        #
        # Use the ADC.read method, which returns a value between 0.0 and 1.0 - multiply by 1.8
        # to get the actual volts seen by the BeagleBone Black - the BeagleBone Black analog inputs
        # work in the 0 to 1.8V range.
        #
        # The BBIO library documentation says that you must read it twice to get a reading.
        x = float(ADC.read(Pressure_Vessel_Thermocouple_Grove_Cape_V2_AIN_0) * 1.8)
        x = float(ADC.read(Pressure_Vessel_Thermocouple_Grove_Cape_V2_AIN_0) * 1.8)
        # Add the most recent temperature point to the list
        self.read_vessel_temperature_C_list.append(x)


    # Legacy Alicat pressure setpoint callback (not active in normal startup).
    def set_nozzle_pressure_to_current_setpoint_timer_callback(self):
        set_alicat_pressure(self.setpoint_current_nozzle_pressure_PSI)
        print("\nCurrent Nozzle Pressure Setpoint = %d\r" % (self.setpoint_current_nozzle_pressure_PSI))
        time.sleep(0.5)
        pvalue = read_alicat_downstream_pressure()
        print("Current Nozzle Pressure Downstream Reading = %d" % (pvalue))


    # Legacy heater control callback (not enabled in normal startup).
    def control_vessel_and_nozzle_vessel_temperature_timer_callback(self):
        print("calling control vessel nozzle timer callback")
        current_nozzle_vessel_temperature = self.get_nozzle_vessel_temperature()
        current_pressure_vessel_temperature = self.get_pressure_vessel_temperature()
        current_pressure_vessel_psi = read_vessel_pressure()

        print("Nozzle vessel temperature: " + str(current_nozzle_vessel_temperature))
        print("Pressure vessel temperature" + str(current_pressure_vessel_temperature))
        print("Pressure vessel psi: " + str(current_pressure_vessel_psi))

        self.current_nozzle_temperature_C = current_nozzle_vessel_temperature
        self.current_vessel_temperature_C = current_pressure_vessel_temperature
        self.current_vessel_pressure_PSI = current_pressure_vessel_psi

        #
        # Decrement counters for heaters on and wait times - and set flags of the times have elapsed
        if self.pressure_vessel_heater_wait:
            self.pressure_vessel_heater_off_time = self.pressure_vessel_heater_off_time - self.dt
            if self.pressure_vessel_heater_off_time <= 0:
                self.pressure_vessel_heater_wait = False

        if self.nozzle_vessel_heater_wait:
            self.nozzle_vessel_heater_off_time = self.nozzle_vessel_heater_off_time - self.dt
            if self.nozzle_vessel_heater_off_time <= 0:
                self.nozzle_vessel_heater_wait = False

        if self.pressure_vessel_heater_on:
            self.pressure_vessel_heater_on_time = self.pressure_vessel_heater_on_time - self.dt
            if self.pressure_vessel_heater_on_time <= 0:
                self.pressure_vessel_heater_on = False
                self.pressure_vessel_heater_wait = True
                self.pressure_vessel_heater_off_time = self.pressure_vessel_heater_seconds_to_wait_after_heating
                set_pressure_vessel_heater(False)
                self.vessel_heater_on_indicator_label.hide()

        if self.nozzle_vessel_heater_on:
            self.nozzle_vessel_heater_on_time = self.nozzle_vessel_heater_on_time - self.dt
            if self.nozzle_vessel_heater_on_time <= 0:
                self.nozzle_vessel_heater_on = False
                self.nozzle_vessel_heater_wait = True
                self.nozzle_vessel_heater_off_time = self.nozzle_vessel_heater_seconds_to_wait_after_heating
                set_nozzle_vessel_heater(False)
                self.nozzle_heater_on_indicator_label.hide()

        if current_pressure_vessel_temperature > self.operatingRange_vessel_temperature_C[0]:
            self.pressure_vesssel_heater_exceeds_min_temperature = True

        if current_nozzle_vessel_temperature > self.operatingRange_nozzle_temperature_C[0]:
            self.nozzle_vesssel_heater_exceeds_min_temperature = True

        # If you are not in a wait state, then turn on the nozzle vessel heater if the temperature is below the min
        if not (self.pressure_vessel_heater_wait):
            if (current_pressure_vessel_temperature < self.operatingRange_vessel_temperature_C[0]) and (not self.pressure_vessel_heater_on):
                self.pressure_vessel_heater_on = True
                set_pressure_vessel_heater(True)
                if (self.current_screen == "w6") or (self.current_screen == "w7") or (self.current_screen == "w11") or (self.current_screen == "w12"):
                    self.vessel_heater_on_indicator_label.show()

                self.pressure_vessel_heater_wait = False
                self.pressure_vessel_heater_on_time = self.pressure_vessel_heater_on_duration_seconds

        if self.system_nozzle_pressure_in_operating_range:  # Only enable the nozzle heater after the nozzle tank is at pressure after startup, because the
            # pressurization raises tank temperature by 10C.
            if not (self.nozzle_vessel_heater_wait):
                if (current_nozzle_vessel_temperature < self.operatingRange_nozzle_temperature_C[0]) and (not self.nozzle_vessel_heater_on):
                    self.nozzle_vessel_heater_on = True
                    set_nozzle_vessel_heater(True)
                    if (self.current_screen == "w6") or (self.current_screen == "w7") or (self.current_screen == "w11") or (self.current_screen == "w12"):
                        self.nozzle_heater_on_indicator_label.show()

                    self.nozzle_vessel_heater_wait = False
                    self.nozzle_vessel_heater_on_time = self.nozzle_vessel_heater_on_duration_seconds


    # Update the legacy system state and related display values.
    def system_state_time_update(self):
        self.elapsed_time_from_GUI_startup_seconds += 1

        if self.setpoints_were_reset:
            self.write_header_to_data_logging_file("a")  # Append a new header to the data logging file
            self.write_column_labels_to_data_logging_file()  # Append header columns again
            self.setpoints_were_reset = False

        #
        # Log the temperatures and pressures and write to the file
        current_nozzle_vessel_temperature = self.get_nozzle_vessel_temperature()
        current_pressure_vessel_temperature = self.get_pressure_vessel_temperature()
        current_pressure_vessel_psi = read_vessel_pressure()

        self.current_nozzle_temperature_C = current_nozzle_vessel_temperature
        self.current_vessel_temperature_C = current_pressure_vessel_temperature
        self.current_vessel_pressure_PSI = current_pressure_vessel_psi

        self.write_machine_state_to_data_logging_file()

        # print "Elapsed time = %d" %(self.elapsed_startup_time_seconds)

        vessel_pressure = read_vessel_pressure()
        self.vessel_pressure_PSI_progressbar.setValue(vessel_pressure)
        new_text = "Vessel PSI =    %4i, min = %4i    [OpR= %4i to %4i]" % (
            vessel_pressure,
            self.setpoint_current_vessel_pressure_PSI,
            self.operatingRange_vessel_pressure_PSI[0],
            self.operatingRange_vessel_pressure_PSI[1],
        )
        self.vessel_psi_text_label.setText(new_text)
        new_text = "Vessel PSI =   %4i, (read-only)" % (vessel_pressure)
        self.w9c_vessel_psi_text_label.setText(new_text)

        # Update the progress bar and their labels
        nozzle_temperature = self.get_nozzle_vessel_temperature()
        self.nozzle_temp_C_progressbar.setValue(nozzle_temperature)

        #
        # Round the vessel temperature up to the nearest tenth of a degree (so that the displayed value doesn't disagree with "Ready!")
        nozzle_temperature_rounded = decimal.Decimal(nozzle_temperature).quantize(decimal.Decimal(".1"), rounding=decimal.ROUND_UP)

        #
        # Update the scrollbar labels
        # b = self.scrollbar_nozzle_temperature_C_values.index(self.scrollbar_limits_nozzle_temperature_C[3])
        # c = self.scrollbar_nozzle_temperature_C_values[b]
        # new_text = "Nozzle (T C) =   %4i,[%4i]"     %(nozzle_temperature,self.setpoint_current_nozzle_temperature_C)
        # self.w9c_nozzle_t_text_label.setText(new_text)

        vessel_temperature = self.get_pressure_vessel_temperature()
        self.vessel_temp_C_progressbar.setValue(vessel_temperature)

        #
        # Round the vessel temperature up to the nearest tenth of a degree (so that the displayed value doesn't disagree with "Ready!")
        vessel_temperature_rounded = decimal.Decimal(vessel_temperature).quantize(decimal.Decimal(".1"), rounding=decimal.ROUND_UP)

        nozzle_pressure_estimate = read_alicat_downstream_pressure()
        self.current_nozzle_downstream_pressure_PSI = nozzle_pressure_estimate
        self.nozzle_pressure_PSI_progressbar.setValue(nozzle_pressure_estimate)
        # nozzle_pressure_estimate = float(self.pressure_controller_etime/self.pressure_controller_startup_time_seconds)*(self.scrollbar_limits_nozzle_pressure_PSI[1]-self.scrollbar_limits_nozzle_pressure_PSI[0])

        # self.vessel_temp_C_progressbar.setValue(vessel_temperature)
        # b = self.scrollbar_limits_vessel_temperature_C_values.index(self.scrollbar_limits_vessel_temperature_C[3])
        # c = self.scrollbar_limits_vessel_temperature_C_values[b]
        # new_text = "Vessel (T C) =   %4i,[%4i]"     %( vessel_temperature,self.setpoint_current_vessel_temperature_C)
        # self.w9c_vessel_t_text_label.setText(new_text)

        # new_text = "Nozzle (psi) =   %4i,[%4i]"     %(self.setpoint_current_nozzle_pressure_psi,self.setpoint_current_nozzle_pressure_psi)
        # self.w9c_nozzle_psi_text_label.setText(new_text)

        #
        # Special cases if in startup or shutdown
        if self.system_in_startup:
            # self.pressure_controller_etime +=1
            new_text = (
                "Nozzle  "
                + self.degree_sign
                + "C =  %4.1f,  sp = %4.1f    [OpR=  %4.1f  to  %4.1f]"
                % (
                    nozzle_temperature_rounded,
                    self.setpoint_current_nozzle_temperature_C,
                    self.operatingRange_nozzle_temperature_C[0],
                    self.operatingRange_nozzle_temperature_C[1],
                )
            )
            self.nozzle_temp_C_text_label.setText(new_text)

            new_text = (
                "Vessel  "
                + self.degree_sign
                + "C =  %4.1f,  sp = %4.1f    [OpR=  %4.1f  to  %4.1f]"
                % (
                    vessel_temperature_rounded,
                    self.setpoint_current_vessel_temperature_C,
                    self.operatingRange_vessel_temperature_C[0],
                    self.operatingRange_vessel_temperature_C[1],
                )
            )
            self.vessel_temp_C_text_label.setText(new_text)

            new_text = "Nozzle PSI =  %4i,  sp = %4i    [OpR= %4i to %4i]" % (
                nozzle_pressure_estimate,
                self.setpoint_current_nozzle_pressure_PSI,
                self.operatingRange_nozzle_pressure_PSI[0],
                self.operatingRange_nozzle_pressure_PSI[1],
            )
            self.nozzle_psi_text_label.setText(new_text)

            # Update the system startup widget checkboxes based on current values & comparison with operating limits:
            if self.operatingRange_vessel_pressure_PSI[0] <= vessel_pressure <= self.operatingRange_vessel_pressure_PSI[1]:
                self.vessel_pressure_checkbox.setText("Ready!")
                self.vessel_pressure_checkbox.setStyleSheet(checkbox_ready_stylesheet)
                self.vessel_pressure_checkbox.setChecked(True)
                self.vessel_pressure_checkbox.setEnabled(True)
            else:
                self.vessel_pressure_checkbox.setText("Pressurizing...")
                self.vessel_pressure_checkbox.setStyleSheet(checkbox_waiting_stylesheet)
                self.vessel_pressure_checkbox.setChecked(False)
                self.vessel_pressure_checkbox.setEnabled(False)

            if self.operatingRange_vessel_temperature_C[0] <= vessel_temperature <= self.operatingRange_vessel_temperature_C[1]:
                self.vessel_temp_checkbox.setStyleSheet(checkbox_ready_stylesheet)
                self.vessel_temp_checkbox.setText("Ready!")
                self.vessel_temp_checkbox.setChecked(True)
                self.vessel_temp_checkbox.setEnabled(True)
            else:
                self.vessel_temp_checkbox.setText("Waiting...")
                self.vessel_temp_checkbox.setStyleSheet(checkbox_waiting_stylesheet)
                self.vessel_temp_checkbox.setChecked(False)
                self.vessel_temp_checkbox.setEnabled(False)

            if (
                (self.setpoint_current_nozzle_pressure_PSI - self.setpoint_current_nozzle_pressure_PSI_tolerance)
                <= nozzle_pressure_estimate
                <= (self.setpoint_current_nozzle_pressure_PSI + self.setpoint_current_nozzle_pressure_PSI_tolerance)
            ):
                self.system_nozzle_pressure_in_operating_range = True  # Once set, this enable temperature control on the nozzle pressure tank
                # Have to do this because nozzle tank pressurization increases the tank temperature by around 10C
                self.nozzle_pressure_checkbox.setStyleSheet(checkbox_ready_stylesheet)
                self.nozzle_pressure_checkbox.setText("Ready!")
                self.nozzle_pressure_checkbox.setChecked(True)
                self.nozzle_pressure_checkbox.setEnabled(True)
            else:
                self.nozzle_pressure_checkbox.setText("Pressurizing...")
                self.nozzle_pressure_checkbox.setStyleSheet(checkbox_waiting_stylesheet)
                self.nozzle_pressure_checkbox.setChecked(False)
                self.nozzle_pressure_checkbox.setEnabled(False)

            if self.operatingRange_nozzle_temperature_C[0] <= nozzle_temperature <= self.operatingRange_nozzle_temperature_C[1]:
                self.nozzle_temp_checkbox.setStyleSheet(checkbox_ready_stylesheet)
                self.nozzle_temp_checkbox.setText("Ready!")
                self.nozzle_temp_checkbox.setChecked(True)
                self.nozzle_temp_checkbox.setEnabled(True)
            else:
                self.nozzle_temp_checkbox.setText("Waiting...")
                self.nozzle_temp_checkbox.setStyleSheet(checkbox_waiting_stylesheet)
                self.nozzle_temp_checkbox.setChecked(False)
                self.nozzle_temp_checkbox.setEnabled(False)

        if self.system_in_shutdown:
            new_text = (
                "Nozzle  "
                + self.degree_sign
                + "C =  %4.1f   [Safe=  %4.1f  to  %4.1f]"
                % (
                    nozzle_temperature_rounded,
                    self.safeShutdownRange_nozzle_temperature_C[0],
                    self.safeShutdownRange_nozzle_temperature_C[1],
                )
            )
            self.nozzle_temp_C_text_label.setText(new_text)

            new_text = (
                "Vessel  "
                + self.degree_sign
                + "C =  %4.1f   [Safe=  %4.1f  to  %4.1f]"
                % (
                    vessel_temperature_rounded,
                    self.safeShutdownRange_vessel_temperature_C[0],
                    self.safeShutdownRange_vessel_temperature_C[1],
                )
            )
            self.vessel_temp_C_text_label.setText(new_text)

            new_text = "Nozzle PSI = %4i   [Safe=  %4i  to  %4i]" % (
                nozzle_pressure_estimate,
                self.safeShutdownRange_nozzle_pressure_PSI[0],
                self.safeShutdownRange_nozzle_pressure_PSI[1],
            )
            self.nozzle_psi_text_label.setText(new_text)

            #
            # Set the vessel to "Safe" - per Sarah, it is OK and desirable to keep the vessel at pressure (not a safety issue)
            self.vessel_pressure_checkbox.setText("Safe!")
            self.vessel_pressure_checkbox.setStyleSheet(checkbox_ready_stylesheet)
            self.vessel_pressure_checkbox.setChecked(True)
            self.vessel_pressure_checkbox.setEnabled(True)

            # if  self.safeShutdownRange_vessel_pressure_psi[0] <= vessel_pressure <= self.safeShutdownRange_vessel_pressure_psi[1]:
            # self.vessel_pressure_checkbox.setText("Safe!")
            # self.vessel_pressure_checkbox.setStyleSheet(checkbox_ready_stylesheet)
            # self.vessel_pressure_checkbox.setChecked(True)
            # self.vessel_pressure_checkbox.setEnabled(True)
            # else:
            # self.vessel_pressure_checkbox.setText("Venting...")
            # self.vessel_pressure_checkbox.setStyleSheet(checkbox_waiting_stylesheet)
            # self.vessel_pressure_checkbox.setChecked(False)
            # self.vessel_pressure_checkbox.setEnabled(False)

            if self.safeShutdownRange_vessel_temperature_C[0] <= vessel_temperature <= self.safeShutdownRange_vessel_temperature_C[1]:
                self.vessel_temp_checkbox.setStyleSheet(checkbox_ready_stylesheet)
                self.vessel_temp_checkbox.setText("Safe!")
                self.vessel_temp_checkbox.setChecked(True)
                self.vessel_temp_checkbox.setEnabled(True)
            else:
                self.vessel_temp_checkbox.setText("Cooling...")
                self.vessel_temp_checkbox.setStyleSheet(checkbox_waiting_stylesheet)
                self.vessel_temp_checkbox.setChecked(False)
                self.vessel_temp_checkbox.setEnabled(False)

            if self.safeShutdownRange_nozzle_pressure_PSI[0] <= nozzle_pressure_estimate <= self.safeShutdownRange_nozzle_pressure_PSI[1]:
                self.nozzle_pressure_checkbox.setStyleSheet(checkbox_ready_stylesheet)
                self.nozzle_pressure_checkbox.setText("Safe!")
                self.nozzle_pressure_checkbox.setChecked(True)
                self.nozzle_pressure_checkbox.setEnabled(True)
            else:
                self.nozzle_pressure_checkbox.setText("Venting...")
                self.nozzle_pressure_checkbox.setStyleSheet(checkbox_waiting_stylesheet)
                self.nozzle_pressure_checkbox.setChecked(False)
                self.nozzle_pressure_checkbox.setEnabled(False)

            if self.safeShutdownRange_nozzle_temperature_C[0] <= nozzle_temperature <= self.safeShutdownRange_nozzle_temperature_C[1]:
                self.nozzle_temp_checkbox.setStyleSheet(checkbox_ready_stylesheet)
                self.nozzle_temp_checkbox.setText("Safe!")
                self.nozzle_temp_checkbox.setChecked(True)
                self.nozzle_temp_checkbox.setEnabled(True)
            else:
                self.nozzle_temp_checkbox.setText("Cooling...")
                self.nozzle_temp_checkbox.setStyleSheet(checkbox_waiting_stylesheet)
                self.nozzle_temp_checkbox.setChecked(False)
                self.nozzle_temp_checkbox.setEnabled(False)



    # =========================================================================
    # 9. Stored setpoints and data logging
    # Legacy file-backed defaults, CSV headers, records, and log numbering.
    # =========================================================================

    # Build the numbered legacy CSV log filename.
    def _construct_data_logging_filename(self):
        """Construct the data logging filename for the current session."""
        return "%s_%04d.csv" % (
            self.data_logging_file_name,
            self.data_logging_file_number,
        )


    # Load the legacy setpoint vessel temperature C setting from its stored startup setpoint file.
    def load_startup_setpoint_vessel_temperature_C(self):
        file = open(self.startup_setpoint_file_vessel_temperature_C, "r")
        self.setpoint_current_vessel_temperature_C = int(file.readline())
        file.close()


    # Save the legacy setpoint vessel temperature C startup setpoint.
    def save_startup_setpoint_vessel_temperature_C(self):
        file = open(self.startup_setpoint_file_vessel_temperature_C, "w")  # Open the file - any values written will overwrite the existing values
        ival = self.w9c_vessel_t_scrollbar.value()
        a = self.scrollbar_limits_vessel_temperature_C_values[ival]
        file.write(str(a))
        file.close()


    # Load the legacy setpoint vessel pressure PSI setting from its stored startup setpoint file.
    def load_startup_setpoint_vessel_pressure_PSI(self):
        file = open(self.startup_setpoint_file_vessel_pressure_PSI, "r")
        self.setpoint_current_vessel_pressure_PSI = int(file.readline())
        file.close()


    # Load the legacy setpoint nozzle temperature C setting from its stored startup setpoint file.
    def load_startup_setpoint_nozzle_temperature_C(self):
        file = open(self.startup_setpoint_file_nozzle_temperature_C, "r")
        self.setpoint_current_nozzle_temperature_C = int(file.readline())
        file.close()


    # Save the legacy setpoint nozzle temperature C startup setpoint.
    def save_startup_setpoint_nozzle_temperature_C(self):
        file = open(self.startup_setpoint_file_nozzle_temperature_C, "w")
        ival = self.w9c_nozzle_t_scrollbar.value()
        a = self.scrollbar_nozzle_temperature_C_values[ival]
        file.write(str(a))
        file.close()


    # Load the legacy setpoint nozzle pressure PSI setting from its stored startup setpoint file.
    def load_startup_setpoint_nozzle_pressure_PSI(self):
        file = open(self.startup_setpoint_file_nozzle_pressure_PSI, "r")
        self.setpoint_current_nozzle_pressure_PSI = int(file.readline())
        file.close()


    # Save the legacy setpoint nozzle pressure PSI startup setpoint.
    def save_startup_setpoint_nozzle_pressure_PSI(self):
        file = open(self.startup_setpoint_file_nozzle_pressure_PSI, "w")
        ival = self.w9c_nozzle_psi_scrollbar.value()
        a = self.scrollbar_limits_nozzle_pressure_PSI_values[ival]
        file.write(str(a))
        file.close()


    # Load the legacy blast sec setting from its stored startup setpoint file.
    def load_startup_blast_sec(self):
        file = open(self.startup_setpoint_file_blast_sec, "r")
        self.setpoint_current_blast_sec = float(file.readline())
        file.close()


    # Save the legacy blast sec startup setpoint.
    def save_startup_blast_sec(self):
        file = open(self.startup_setpoint_file_blast_sec, "w")
        ival = self.w9c_blast_sec_scrollbar.value()
        a = self.scrollbar_blast_sec_values[ival]
        file.write(str(a))
        file.close()


    # Load the historical pressure vessel heater on duration seconds value from configured storage.
    def load_pressure_vessel_heater_on_duration_seconds(self):
        file = open(self.startup_setpoint_file_pressure_vessel_heater_on_duration_seconds, "r")
        self.pressure_vessel_heater_on_duration_seconds = float(file.readline())
        file.close()


    # Load the historical nozzle vessel heater on duration seconds value from configured storage.
    def load_nozzle_vessel_heater_on_duration_seconds(self):
        file = open(self.startup_setpoint_file_nozzle_vessel_heater_on_duration_seconds, "r")
        self.nozzle_vessel_heater_on_duration_seconds = float(file.readline())
        file.close()


    # Load the historical pressure vessel heater seconds to wait after heating value from configured storage.
    def load_pressure_vessel_heater_seconds_to_wait_after_heating(self):
        file = open(
            self.startup_setpoint_file_pressure_vessel_heater_seconds_to_wait_after_heating,
            "r",
        )
        self.pressure_vessel_heater_seconds_to_wait_after_heating = float(file.readline())
        file.close()


    # Load the historical nozzle vessel heater seconds to wait after heating value from configured storage.
    def load_nozzle_vessel_heater_seconds_to_wait_after_heating(self):
        file = open(
            self.startup_setpoint_file_nozzle_vessel_heater_seconds_to_wait_after_heating,
            "r",
        )
        self.nozzle_vessel_heater_seconds_to_wait_after_heating = float(file.readline())
        file.close()


    # Write header to data logging file for the retained CSV data logging workflow.
    def write_header_to_data_logging_file(self, write_option):  # write_option can be 'w' (create  new file) or 'a' (append to an existing file)
        # print "write option = %s"%(write_option)
        header = "\n"
        header += "Ice Cream Machine Data Logging File Name, %s\n" % self.data_logging_file_name
        header += "\n"
        header += "Startup Parameters:\n "
        header += "\n"
        header += "Vessel Minimum   Pressure for Ice Cream Machine Operation (PSI), %5.1f\n" % float(self.operatingRange_vessel_pressure_PSI[0])
        header += "Vessel Maximum   Pressure for Ice Cream Machine Operation (PSI), %5.1f\n" % float(self.operatingRange_vessel_pressure_PSI[1])
        header += "\n"
        header += "Vessel Temperature Setpoint (C), %5.1f\n" % float(self.setpoint_current_vessel_temperature_C)
        header += "Vessel Operating Temperature Min (C), %5.1f\n" % float(self.operatingRange_vessel_temperature_C[0])
        header += "Vessel Operating Temperature Max (C), %5.1f\n" % float(self.operatingRange_vessel_temperature_C[1])
        header += "Vessel Heating Pulse Duration (sec),  %5.1f\n" % float(self.pressure_vessel_heater_on_duration_seconds)
        header += "Vessel Heating Post-Pulse Wait Duration (sec),  %5.1f\n" % float(self.pressure_vessel_heater_seconds_to_wait_after_heating)
        header += "\n"
        header += "Nozzle Setpoint Pressure (PSI), %5.1f\n" % float(self.setpoint_current_nozzle_pressure_PSI)
        header += "Nozzle Setpoint Pressure +/- Tolerance (PSI), %5.1f\n" % float(self.setpoint_current_nozzle_pressure_PSI_tolerance)
        header += "\n"
        header += "Nozzle Temperature Setpoint (C), %5.1f\n" % float(self.setpoint_current_nozzle_temperature_C)
        header += "Nozzle Operating Temperature Min (C), %5.1f\n" % float(self.operatingRange_nozzle_temperature_C[0])
        header += "Nozzle Operating Temperature Max (C), %5.1f\n" % float(self.operatingRange_nozzle_temperature_C[1])
        header += "Nozzle Heating Pulse Duration (sec),  %5.1f\n" % float(self.nozzle_vessel_heater_on_duration_seconds)
        header += "Nozzle Heating Post-Pulse Wait Duration (sec),  %5.1f\n" % float(self.nozzle_vessel_heater_seconds_to_wait_after_heating)
        header += "\n"
        header += "Nozzle Solenoid On Time (sec), %5.1f sec\n" % float(self.setpoint_current_blast_sec)
        header += "\n"
        with open(self.data_logging_file_name, write_option) as f:
            f.write(header)
        f.close()


    # Write column labels to data logging file for the retained CSV data logging workflow.
    def write_column_labels_to_data_logging_file(self):
        column_labels = "\n"
        column_labels += " Elapsed Time from GUI Startup (sec),"
        column_labels += " Elapsed Time from Current System Startup (sec),"
        column_labels += " System State(1=Startup 0=Shutdown),"
        column_labels += " Vessel Pressure (PSI),"
        column_labels += " Vessel Min Operating Pressure (PSI) (C),"
        column_labels += " Vessel Max Operating Pressure (PSI) (C),"
        column_labels += " Vessel Heater On (True=1 False=0),"
        column_labels += " Vessel Temperature (C),"
        column_labels += " Vessel Temperature Setpoint(C),"
        column_labels += " Vessel Min Operating Temperature(C),"
        column_labels += " Vessel Max Operating Temperature(C),"
        column_labels += " Nozzle Heater On (True=1 False=0),"
        column_labels += " Nozzle Temperature (C),"
        column_labels += " Nozzle Temperature Setpoint(C),"
        column_labels += " Nozzle Min Operating Temperature(C),"
        column_labels += " Nozzle Max Operating Temperature(C),"
        column_labels += " Nozzle Downstream Pressure (PSI),"
        column_labels += " Nozzle Pressure Setpoint(PSI),"
        column_labels += " Nozzle Solenoid On Time (sec),"
        column_labels += " Nozzle Solenoid On (True=1 False=0)"

        with open(self.data_logging_file_name, "a") as f:
            f.write(column_labels)
        f.close()


    # Write machine state to data logging file for the retained CSV data logging workflow.
    def write_machine_state_to_data_logging_file(self):
        data_row = "\n%5i," % (self.elapsed_time_from_GUI_startup_seconds)
        data_row += "%5i," % (self.elapsed_startup_time_seconds + self.elapsed_shutdown_time_seconds)
        data_row += "%5r," % (self.system_in_startup * 1)
        data_row += " %5.1f," % float(self.current_vessel_pressure_PSI)
        data_row += " %5.1f," % float(self.operatingRange_vessel_pressure_PSI[0])
        data_row += " %5.1f," % float(self.operatingRange_vessel_pressure_PSI[1])
        data_row += " %5r," % (self.pressure_vessel_heater_on * 1)
        data_row += " %5.1f," % float(self.current_vessel_temperature_C)
        data_row += " %5.1f," % float(self.setpoint_current_vessel_temperature_C)
        data_row += " %5.1f," % float(self.operatingRange_vessel_temperature_C[0])
        data_row += " %5.1f," % float(self.operatingRange_vessel_temperature_C[1])
        data_row += " %5r," % (self.nozzle_vessel_heater_on * 1)
        data_row += " %5.1f," % float(self.current_nozzle_temperature_C)
        data_row += " %5.1f," % float(self.setpoint_current_nozzle_temperature_C)
        data_row += " %5.1f," % float(self.operatingRange_nozzle_temperature_C[0])
        data_row += " %5.1f," % float(self.operatingRange_nozzle_temperature_C[1])
        data_row += " %5i," % self.current_nozzle_downstream_pressure_PSI
        data_row += " %5.1f," % float(self.setpoint_current_nozzle_pressure_PSI)
        data_row += " %5.1f," % float(self.setpoint_current_blast_sec)
        data_row += " %5r" % (self.nozzle_solenoid_on[1] * 1)
        data_row += " %5r" % (self.nozzle_solenoid_on[2] * 1)
        data_row += " %5r" % (self.nozzle_solenoid_on[3] * 1)

        with open(self.data_logging_file_name, "a") as f:
            f.write(data_row)
        f.close()


    # Load the historical data logging file number value from configured storage.
    def load_data_logging_file_number(self):
        file = open(self.startup_file_data_logging_file_number, "r")
        try:
            file_number = int(file.readline())
            file.close()
            return file_number
        except:
            return 0


    # Advance the stored data logging filename number counter.
    def increment_data_logging_filename_number(self):
        file = open(self.startup_file_data_logging_file_number, "w")
        a = self.data_logging_file_number + 1
        file.write(str(a))
        file.close()



    # =========================================================================
    # 10. Legacy sensor and system-readiness utilities
    # Legacy thermocouple conversions and operating-range/readiness checks.
    # =========================================================================

    # Read/average the nozzle analog temperature input (legacy routine).
    def get_nozzle_vessel_temperature(self):
        #
        # Use the ADC.read method, which returns a value between 0.0 and 1.0 - multiply by 1.8
        # to get the actual volts seen by the BeagleBone Black - the BeagleBone Black analog inputs
        # work in the 0 to 1.8V range.
        #
        # The BBIO library documentation says that you must read it twice to get a reading.
        # Also, in case there is a problem running this in Python 3, you can get the
        # raw value via this shell command:
        # cat /sys/bus/iio/devices/iio:device0/in_voltage0_raw

        #
        # Take 25 readings over one second - the averaging will reduce electrical noise
        # x = 0
        # sum = 0
        # for i in range(25):
        # x = ADC.read(Nozzle_Vessel_Thermocouple_Grove_Cape_V2_AIN_2)*1.8
        # x = ADC.read(Nozzle_Vessel_Thermocouple_Grove_Cape_V2_AIN_2)*1.8
        # sum = x + sum
        # #time.sleep(0.04)

        # nozzle_vessel_thermocouple_voltage_averaged = sum/25.0
        self.read_nozzle_temperature_C_timer.stop()
        nozzle_thermocouple_voltage_averaged = float(sum(self.read_nozzle_temperature_C_list) / float(len(self.read_nozzle_temperature_C_list)))
        self.read_nozzle_temperature_C_timer.start()
        #
        # Calculate temperature (C) via the linear relationship derived from calibration data
        nozzle_temperature_centigrade = float((1372.2 * nozzle_thermocouple_voltage_averaged) - 153.69)
        #
        # Offset adjustment based on 11/19/2018 tests on re-wrapped tanks
        nozzle_temperature_centigrade = nozzle_temperature_centigrade + 1.59 - 3
        return nozzle_temperature_centigrade


    # Read/average the vessel analog temperature input (legacy routine).
    def get_pressure_vessel_temperature(self):
        #
        # Use the ADC.read method, which returns a value between 0.0 and 1.0 - multiply by 1.8
        # to get the actual volts seen by the BeagleBone Black - the BeagleBone Black analog inputs
        # work in the 0 to 1.8V range.
        #
        # The BBIO library documentation says that you must read it twice to get a reading.
        # Also, in case there is a problem running this in Python 3, you can get the
        # raw value via this shell command:
        # cat /sys/bus/iio/devices/iio:device0/in_voltage0_raw

        #
        # Take 25 readings over one second - the averaging will reduce electrical noise
        # x = 0
        # sum = 0
        # for i in range(25):
        # x = ADC.read(Pressure_Vessel_Thermocouple_Grove_Cape_V2_AIN_0)*1.8
        # x = ADC.read(Pressure_Vessel_Thermocouple_Grove_Cape_V2_AIN_0)*1.8
        # sum = x + sum
        # #time.sleep(0.04)
        # pressure_vessel_thermocouple_voltage_averaged = sum/25.0

        self.read_vessel_temperature_C_timer.stop()
        vessel_thermocouple_voltage_averaged = float(sum(self.read_vessel_temperature_C_list) / float(len(self.read_vessel_temperature_C_list)))
        # print(self.read_vessel_temperature_C_list)
        self.read_vessel_temperature_C_timer.start()

        #
        # Calculate temperature (C) via the linear relationship derived from calibration datadata
        vessel_temperature_centigrade = float((1262.3 * vessel_thermocouple_voltage_averaged) - 137.89)
        #
        # Offset adjustment based on 11/19/2018 tests on re-wrapped tanks
        vessel_temperature_centigrade = vessel_temperature_centigrade + 0.32 - 1.9
        return vessel_temperature_centigrade


    # Evaluate historical sensor/system readiness conditions.
    def test_system(self):
        current_temperature = self.get_nozzle_vessel_temperature()
        current_pressure = self.get_pressure_vessel_temperature()
        print("Current temperature: " + str(current_temperature) + "\nCurrent pressure: " + str(current_pressure))

        if (current_pressure < 520) or (current_temperature > 1):
            return False
        return True



# =============================================================================
# Program entry point -- initializes GPIO, then Qt event loop
# =============================================================================
def main():
    initialize_system()
    app = QtGui.QApplication(sys.argv)
    gui = IceCreamGUI()
    # ex.create_w1()
    # ex.show_w1()
    # ex.create_w2()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
