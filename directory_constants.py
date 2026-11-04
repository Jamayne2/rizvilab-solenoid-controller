# ========================================================================================
# Constants for Directory Paths
# ========================================================================================

# Default directory on the BeagleBone
BEAGLEBONE_DEFAULT_DIRECTORY = "/home/debian/controller-final"

# Directory paths
STARTUP_SETPOINT_DIRECTORY = BEAGLEBONE_DEFAULT_DIRECTORY + "/STARTUP_SETPOINTS"
DATA_LOGGING_DIRECTORY = BEAGLEBONE_DEFAULT_DIRECTORY + "/DATA_LOGS"

# ========================================================================================
# Constants for Filenames
# ========================================================================================

# Filenames for startup setpoints
STARTUP_SETPOINT_FILE_VESSEL_TEMPERATURE_C = STARTUP_SETPOINT_DIRECTORY + "/startup_setpoint_file_vessel_temperature_C"
STARTUP_SETPOINT_FILE_VESSEL_PRESSURE_PSI = STARTUP_SETPOINT_DIRECTORY + "/startup_setpoint_file_vessel_pressure_PSI"
STARTUP_SETPOINT_FILE_NOZZLE_TEMPERATURE_C = STARTUP_SETPOINT_DIRECTORY + "/startup_setpoint_file_nozzle_temperature_C"
STARTUP_SETPOINT_FILE_NOZZLE_PRESSURE_PSI = STARTUP_SETPOINT_DIRECTORY + "/startup_setpoint_file_nozzle_pressure_PSI"
STARTUP_SETPOINT_FILE_BLAST_SEC = STARTUP_SETPOINT_DIRECTORY + "/startup_setpoint_file_blast_sec"
STARTUP_SETPOINT_FILE_PRESSURE_VESSEL_HEATER_ON_DURATION_SECONDS = (
    STARTUP_SETPOINT_DIRECTORY + "/startup_setpoint_file_pressure_vessel_heater_on_duration_seconds"
)
STARTUP_SETPOINT_FILE_NOZZLE_VESSEL_HEATER_ON_DURATION_SECONDS = (
    STARTUP_SETPOINT_DIRECTORY + "/startup_setpoint_file_nozzle_vessel_heater_on_duration_seconds"
)
STARTUP_SETPOINT_FILE_PRESSURE_VESSEL_HEATER_SECONDS_TO_WAIT_AFTER_HEATING = (
    STARTUP_SETPOINT_DIRECTORY + "/startup_setpoint_file_pressure_vessel_heater_seconds_to_wait_after_heating"
)
STARTUP_SETPOINT_FILE_NOZZLE_VESSEL_HEATER_SECONDS_TO_WAIT_AFTER_HEATING = (
    STARTUP_SETPOINT_DIRECTORY + "/startup_setpoint_file_nozzle_vessel_heater_seconds_to_wait_after_heating"
)

# Filenames for data logging version numbers
STARTUP_FILE_DATA_LOGGING_FILE_NUMBER = STARTUP_SETPOINT_DIRECTORY + "/startup_data_logging_file_number"

# Filename format for data logging files
DATA_LOGGING_FILE_NAME_TEMPLATE = DATA_LOGGING_DIRECTORY + "/ice_cream_machine_data_logging_file"
