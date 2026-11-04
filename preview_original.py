#!/usr/bin/env python2
"""READ-ONLY ORIGINAL UI REVIEW for the 2024 Ice Cream Machine main.py.

Copy to the directory containing original main.py and its constants modules.
Does NOT initialize GPIO/ADC, send serial commands, change setpoints,
start the original status timers, or shut down the BeagleBone.
Only intended to browse the original UI, NOT to operate the machine.
"""
from __future__ import print_function
import sys
from PyQt4 import QtCore, QtGui
import main as legacy

# Keep the original imagery/widgets, but disable the program's hardware paths.
def no_hardware(*args, **kwargs):
    return None

for name in (
    'initialize_system', 'setup_gpio', 'setup_analog_inputs',
    'set_gpio', 'set_nozzle_solenoid', 'set_nozzle_vessel_heater',
    'set_pressure_vessel_heater', 'set_alicat_pressure',
):
    setattr(legacy, name, no_hardware)

legacy.read_alicat_downstream_pressure = lambda: 0
legacy.read_vessel_pressure = lambda: 0


# Explicit navigation avoids connecting any of the legacy action callbacks.
PAGES = [
    ('w1', 'Welcome'),
    ('w2', 'System / relay status'),
    ('w2a', 'Startup abort status'),
    ('w2b', 'Startup message'),
    ('w3', 'Ready to start'),
    ('w4', 'Open CO2 valve'),
    ('w5', 'Water bath instructions'),
    ('w5a', 'Water bath power'),
    ('w5b', 'Air regulator startup'),
    ('w6', 'System startup'),
    ('w6a', 'Abort during startup'),
    ('w7', 'Startup complete'),
    ('w8', 'Purge nozzle'),
    ('w8a', 'Purge animation'),
    ('w9', 'Dispense controls'),
    ('w9a', 'Dispense animation'),
    ('w9b', 'Warning / failure'),
    ('w9c', 'Admin / setpoints'),
    ('w10', 'Shutdown confirmation'),
    ('w11', 'System shutdown'),
    ('w12', 'Shutdown complete'),
    ('w13', 'Turn off water bath'),
    ('w13a', 'Air regulator shutdown'),
    ('w13b', 'Set regulator to zero'),
    ('w14', 'Close CO2 valve'),
    ('w15', 'Power off / clean'),
]


class PreviewGUI(legacy.IceCreamGUI):
    """Reuses original widgets without connecting the original callbacks."""
    def initUI(self):
        # Deliberately never call legacy.IceCreamGUI.initUI().
        # Original callbacks actuate relays, regulate pressure, or power off.
        pass

    # No changes to original logging files or persistent setpoint files.
    def load_data_logging_file_number(self):
        return 0

    def increment_data_logging_filename_number(self):
        pass

    def write_header_to_data_logging_file(self, *args, **kwargs):
        pass

    def write_column_labels_to_data_logging_file(self, *args, **kwargs):
        pass

    def write_machine_state_to_data_logging_file(self, *args, **kwargs):
        pass

    def load_startup_setpoint_vessel_temperature_C(self):
        pass

    def load_startup_setpoint_vessel_pressure_PSI(self):
        pass

    def load_startup_setpoint_nozzle_temperature_C(self):
        pass

    def load_startup_setpoint_nozzle_pressure_PSI(self):
        pass

    def load_startup_blast_sec(self):
        pass

    def __init__(self):
        super(PreviewGUI, self).__init__()
        self.setFixedSize(480, 272)
        self.stop_legacy_timers()
        self.page_index = 0
        self.pages = PAGES

        # Original on-screen controls are kept for visual inspection only.
        for button in self.findChildren(QtGui.QAbstractButton):
            button.setEnabled(False)
        for control in self.findChildren(QtGui.QAbstractSlider):
            control.setEnabled(False)

        # Small navigation strip; all physical controls remain unavailable.
        self.toolbar = QtGui.QFrame(self)
        self.toolbar.setGeometry(0, 229, 480, 43)
        self.toolbar.setStyleSheet('QFrame {background-color: #222e36;}')
        self.prev_button = QtGui.QPushButton('PREV', self.toolbar)
        self.prev_button.setGeometry(4, 5, 68, 32)
        self.next_button = QtGui.QPushButton('NEXT', self.toolbar)
        self.next_button.setGeometry(388, 5, 86, 32)
        self.close_button = QtGui.QPushButton('EXIT', self.toolbar)
        self.close_button.setGeometry(307, 5, 75, 32)
        self.page_label = QtGui.QLabel(self.toolbar)
        self.page_label.setGeometry(78, 5, 225, 32)
        self.page_label.setStyleSheet('color: white; font-size: 11px; font-weight: bold;')
        self.page_label.setAlignment(QtCore.Qt.AlignCenter)
        self.prev_button.clicked.connect(lambda: self.change_page(-1))
        self.next_button.clicked.connect(lambda: self.change_page(1))
        self.close_button.clicked.connect(self.close)
        self.go_to_page(0)

    def stop_legacy_timers(self):
        for timer in self.findChildren(QtCore.QTimer):
            timer.stop()

    def go_to_page(self, index):
        if index < 0 or index >= len(self.pages):
            return
        self.stop_legacy_timers()
        self.page_index = index
        key, title = self.pages[index]
        # Hide every old page widget. All original text and graphics remain.
        for widget in self.findChildren(QtGui.QWidget):
            if widget is self.toolbar or self.toolbar.isAncestorOf(widget):
                continue
            if widget is self.label_background:
                continue
            widget.hide()

        bg = legacy.IMAGES_FOLDER + '/light-gray-background-with-cals-logo.png'
        if key == 'w1':
            bg = legacy.IMAGES_FOLDER + '/splash-screen-corrected.png'
        self.label_background.setPixmap(QtGui.QPixmap(bg))
        self.label_background.show()
        self.label_background.lower()
        try:
            # Legacy pages w8a and w9a take the nozzle number argument.
            if key in ('w8a', 'w9a'):
                getattr(self, 'show_' + key)(1)
            else:
                getattr(self, 'show_' + key)()
        except Exception as exc:
            print('Preview page {} could not render: {}'.format(key, exc))
        self.stop_legacy_timers()
        self.toolbar.show()
        self.toolbar.raise_()
        self.page_label.setText('REVIEW {}/{} {}'.format(index + 1, len(self.pages), title))
        self.prev_button.setEnabled(index > 0)
        self.next_button.setEnabled(index < len(self.pages) - 1)

    def change_page(self, offset):
        self.go_to_page(self.page_index + offset)

    def closeEvent(self, event):
        self.stop_legacy_timers()
        event.accept()


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    viewer = PreviewGUI()
    viewer.show()
    sys.exit(app.exec_())
