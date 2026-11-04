IMAGES_FOLDER = "/home/debian/pratyush-controller/window-background-images"

# MATLAB "blue" [.2314 0.4706 1.0000] = 59,120,255 or #3b78ff
progressbar_blue_stylesheet = """
    QProgressBar::chunk {
    background-color: #3B78FF;
    width: 20px;
    }
"""
# MATLAB "red" [[0.9414 0.2275 0.0902], 240,58,23 or #f03a17
progressbar_red_stylesheet = """
    QProgressBar::chunk {
    background-color: #F03A17;
    width: 20px;
    }
"""

checkbox_ready_stylesheet = "font-size: 11; font-family: Lucida Sans Typewriter; font-weight: bold;  color:rgb(0,0,0); background-color:rgb(154,218,58);"
checkbox_waiting_stylesheet = "font-size: 9; font-family: Lucida Sans Typewriter; font-weight: bold; font-style:italic; background-color:rgb(242,242,242);"
checkbox_heating_stylesheet = "font-size: 9; font-family: Lucida Sans Typewriter; font-weight: bold; font-style:italic; background-color:rgb(242,35,35);"
checkbox_warning_stylesheet = "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(255,255,30); color:rgb(51,51,51)"
label_heating_stylesheet = "font-size: 14; font-family: Lucida Sans Typewriter; font-weight: bold;font-style:italic; color:rgb(255,51,51)"
button_disabled_stylesheet = "font-size: 9; font-family: Lucida Sans Typewriter; font-weight: bold; font-style:italic; background-color:rgb(242,242,242);"
button_white_stylesheet = "font-size: 12pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(255,255,255); color:rgb(51,51,51)"
smaller_button_white_stylesheet = "font-size: 9pt; font-family: Lucida Sans Typewriter; font-weight: bold; font-style: italic; background-color:rgb(255,255,255); color:rgb(51,51,51)"

# MATLAB "green"  154,218,58

# Pressure codes to Alicat string
pressure_codes = {
    0: "A$$W24=0000",
    50: "A$$W24=1067",
    100: "A$$W24=2133",
    150: "A$$W24=3200",
    200: "A$$W24=4267",
    250: "A$$W24=5333",
    300: "A$$W24=6400",
    350: "A$$W24=7467",
    400: "A$$W24=8533",
    450: "A$$W24=9600",
    500: "A$$W24=10667",
    550: "A$$W24=11733",
    600: "A$$W24=12800",
    650: "A$$W24=13867",
    700: "A$$W24=14933",
    750: "A$$W24=16000",
    800: "A$$W24=17067",
    850: "A$$W24=18133",
    900: "A$$W24=19200",
    950: "A$$W24=20267",
    1000: "A$$W24=21333",
    1050: "A$$W24=22400",
    1100: "A$$W24=23467",
    1150: "A$$W24=24533",
    1200: "A$$W24=25600",
    1250: "A$$W24=26667",
    1300: "A$$W24=27733",
    1350: "A$$W24=28800",
    1400: "A$$W24=29867",
    1450: "A$$W24=30933",
    1500: "A$$W24=32000",
    1550: "A$$W24=33067",
    1600: "A$$W24=34133",
    1650: "A$$W24=35200",
    1700: "A$$W24=36267",
    1750: "A$$W24=37333",
    1800: "A$$W24=38400",
    1850: "A$$W24=39467",
    1900: "A$$W24=40533",
    1950: "A$$W24=41600",
    2000: "A$$W24=42667",
}

# ========================================================================================
#  Define the the BeagleBone GPIO pins used by the BeagleBone relays
#
Pressure_Vessel_Heater_Relay_Grove_Cape_V2_GPIO_111 = "P9_29"
Nozzle_Vessel_Heater_Relay_Grove_Cape_V2_GPIO_03 = "P9_21"
# Nozzle_Solenoid_Relay_Grove_Cape_V2_GPIO_115 = "P9_27"
# Nozzle_Solenoid_Relay_Grove_Cape_V2_GPIO_20 = "P9_41"
# Nozzle_Solenoid_Relay_Grove_Cape_V2_GPIO_07 = "P9_42"
PRESSURE_VESSEL_HEATER_PIN = "P9_29"
NOZZLE_VESSEL_HEATER_PIN = "P9_21"
SOLENOID_NUMBER_PIN = {
    1: "P9_16",
    2: "P9_25",
    3: "P9_12"
}
