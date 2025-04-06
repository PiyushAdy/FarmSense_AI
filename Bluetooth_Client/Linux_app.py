import json
import sys
import os
import time
import threading
import subprocess
import requests
import dbus
import dbus.mainloop.glib
from gi.repository import GLib
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QTextEdit, 
                            QMessageBox, QGridLayout, QProgressBar, QComboBox,
                            QHBoxLayout, QDialog, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QTimer

# Initialize D-Bus mainloop for Bluetooth operations
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

class BluetoothHelper:
    """Helper class for D-Bus Bluetooth operations"""
    
    def __init__(self):
        self.bus = dbus.SystemBus()
        self.adapter_path = None
        self.devices = {}
        self.init_bluetooth()
        
    def init_bluetooth(self):
        try:
            manager = dbus.Interface(
                self.bus.get_object("org.bluez", "/"),
                "org.freedesktop.DBus.ObjectManager"
            )
            objects = manager.GetManagedObjects()
            
            # Find first available adapter
            for path, interfaces in objects.items():
                if "org.bluez.Adapter1" in interfaces:
                    self.adapter_path = path
                    break
                    
            if not self.adapter_path:
                print("No Bluetooth adapter found")
                return False
                
            return True
        except dbus.exceptions.DBusException as e:
            print(f"D-Bus error: {e}")
            return False
            
    def get_adapter_interface(self):
        if not self.adapter_path:
            return None
            
        return dbus.Interface(
            self.bus.get_object("org.bluez", self.adapter_path),
            "org.bluez.Adapter1"
        )
        
    def start_discovery(self):
        adapter = self.get_adapter_interface()
        if adapter:
            adapter.StartDiscovery()
            return True
        return False
        
    def stop_discovery(self):
        adapter = self.get_adapter_interface()
        if adapter:
            try:
                adapter.StopDiscovery()
            except dbus.exceptions.DBusException:
                # Already stopped
                pass
            return True
        return False
        
    def get_devices(self):
        try:
            manager = dbus.Interface(
                self.bus.get_object("org.bluez", "/"),
                "org.freedesktop.DBus.ObjectManager"
            )
            objects = manager.GetManagedObjects()
            
            devices = {}
            # Find devices
            for path, interfaces in objects.items():
                if "org.bluez.Device1" in interfaces:
                    dev_props = interfaces["org.bluez.Device1"]
                    if "Address" in dev_props and "Name" in dev_props:
                        addr = str(dev_props["Address"])
                        name = str(dev_props["Name"])
                        devices[addr] = name
                        
            return devices
        except dbus.exceptions.DBusException as e:
            print(f"D-Bus error: {e}")
            return {}

class BluetoothRFCOMMThread(QThread):
    """Thread for handling RFCOMM connection using bluetoothctl"""
    data_received = pyqtSignal(str)
    connection_status = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    json_complete = pyqtSignal(str)
    
    def __init__(self, bt_addr, parent=None):
        super().__init__(parent)
        self.bt_addr = bt_addr
        self.running = False
        self.rfcomm_device = None
        
    def run(self):
        self.running = True
        self.connection_status.emit("Setting up RFCOMM connection...")
        
        # Set up RFCOMM connection
        try:
            # Find available RFCOMM device
            rfcomm_dev = "/dev/rfcomm0"  # Default device
            
            # Bind the RFCOMM device (requires sudo)
            self.connection_status.emit("Binding RFCOMM device...")
            cmd = ["pkexec", "rfcomm", "bind", rfcomm_dev, self.bt_addr, "1"]
            p = subprocess.run(cmd, capture_output=True, text=True)
            
            if p.returncode != 0:
                self.connection_status.emit(f"Error binding RFCOMM: {p.stderr}")
                self.running = False
                return
                
            self.rfcomm_device = rfcomm_dev
            self.connection_status.emit(f"Connected to HC05 on {rfcomm_dev}")
            
            # Open the device file in binary mode
            with open(rfcomm_dev, 'rb') as f:
                # Set the baud rate for the RFCOMM device
                subprocess.run(["stty", "-F", rfcomm_dev, "9600", "cs8", "-cstopb", "-parenb"], 
                               check=True)
                
                # Give the connection time to stabilize
                time.sleep(1)
                
                # Receive data
                data_buffer = ""
                json_start_found = False
                json_end_found = False
                json_level = 0
                
                while self.running:
                    try:
                        # Read binary data
                        chunk = f.read(1)
                        if not chunk:
                            time.sleep(0.1)
                            continue
                            
                        # Convert to string
                        char = chunk.decode('utf-8', errors='replace')
                        data_buffer += char
                        self.data_received.emit(char)
                        
                        # Track JSON structure
                        if char == '{':
                            json_start_found = True
                            json_level += 1
                        elif char == '}':
                            json_level -= 1
                            if json_level == 0 and json_start_found:
                                json_end_found = True
                        
                        # Update progress
                        if json_start_found and not json_end_found:
                            self.progress_update.emit(min(95, len(data_buffer) // 10))
                        
                        # Check if we have a complete JSON
                        if json_start_found and json_end_found:
                            # Try to find valid JSON in the buffer
                            try:
                                # Extract the JSON part
                                start_idx = data_buffer.find('{')
                                end_idx = data_buffer.rfind('}') + 1
                                json_str = data_buffer[start_idx:end_idx]
                                
                                # Validate JSON
                                json.loads(json_str)  # Just to check if valid
                                
                                self.progress_update.emit(100)
                                self.json_complete.emit(json_str)
                                self.connection_status.emit("JSON data received successfully")
                                break  # Exit after successful JSON reception
                            except json.JSONDecodeError:
                                # If JSON is invalid, continue collecting
                                json_end_found = False
                                self.connection_status.emit("Partial JSON received, continuing...")
                    
                    except (IOError, OSError) as e:
                        if not self.running:
                            break
                        self.connection_status.emit(f"IO Error: {str(e)}")
                        break
        
        except Exception as e:
            self.connection_status.emit(f"Error: {str(e)}")
        finally:
            # Clean up RFCOMM binding on exit
            self.disconnect_rfcomm()
            self.connection_status.emit("Disconnected from HC05")
    
    def disconnect_rfcomm(self):
        if self.rfcomm_device:
            try:
                # Release the RFCOMM device
                cmd = ["pkexec", "rfcomm", "release", self.rfcomm_device]
                subprocess.run(cmd, capture_output=True, text=True)
                self.rfcomm_device = None
            except Exception as e:
                print(f"Error releasing RFCOMM: {e}")
    
    def stop(self):
        self.running = False
        self.disconnect_rfcomm()

class BluetoothScanThread(QThread):
    """Thread for scanning Bluetooth devices using D-Bus"""
    device_found = pyqtSignal(str, str)  # name, address
    scan_complete = pyqtSignal()
    scan_status = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bt_helper = BluetoothHelper()
        
    def run(self):
        self.scan_status.emit("Scanning for Bluetooth devices...")
        
        # Start discovery
        if not self.bt_helper.start_discovery():
            self.scan_status.emit("Failed to start Bluetooth discovery")
            self.scan_complete.emit()
            return
            
        # Wait for discovery to find devices (8 seconds)
        for i in range(8):
            time.sleep(1)
            # Get current devices and emit signals
            devices = self.bt_helper.get_devices()
            for addr, name in devices.items():
                self.device_found.emit(name, addr)
                
        # Stop discovery
        self.bt_helper.stop_discovery()
        
        # Final device check
        devices = self.bt_helper.get_devices()
        if not devices:
            self.scan_status.emit("No devices found")
        else:
            self.scan_status.emit(f"Found {len(devices)} devices")
            
        # Signal completion
        self.scan_complete.emit()

class DeviceScanDialog(QDialog):
    """Dialog for scanning and selecting Bluetooth devices"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_device = None
        self.found_devices = set()  # Keep track of already found devices
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("Scan for HC05 Devices")
        self.setGeometry(300, 300, 400, 300)
        
        layout = QVBoxLayout()
        
        # Status label
        self.status_label = QLabel("Click 'Scan' to discover nearby Bluetooth devices")
        layout.addWidget(self.status_label)
        
        # Device list
        layout.addWidget(QLabel("Available Devices:"))
        self.device_list = QListWidget()
        self.device_list.itemDoubleClicked.connect(self.accept_device)
        layout.addWidget(self.device_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.scan_button = QPushButton("Scan")
        self.scan_button.clicked.connect(self.start_scan)
        button_layout.addWidget(self.scan_button)
        
        select_button = QPushButton("Select")
        select_button.clicked.connect(self.accept_device)
        button_layout.addWidget(select_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def start_scan(self):
        # Clear previous results
        self.device_list.clear()
        self.found_devices.clear()
        self.scan_button.setEnabled(False)
        
        # Start scan thread
        self.scan_thread = BluetoothScanThread()
        self.scan_thread.device_found.connect(self.add_device)
        self.scan_thread.scan_status.connect(self.update_status)
        self.scan_thread.scan_complete.connect(self.scan_finished)
        self.scan_thread.start()
        
    @pyqtSlot(str, str)
    def add_device(self, name, addr):
        # Only add devices we haven't seen yet
        if addr not in self.found_devices:
            self.found_devices.add(addr)
            item = QListWidgetItem(f"{name} ({addr})")
            item.setData(Qt.UserRole, addr)
            self.device_list.addItem(item)
        
    @pyqtSlot(str)
    def update_status(self, status):
        self.status_label.setText(status)
        
    @pyqtSlot()
    def scan_finished(self):
        self.scan_button.setEnabled(True)
        
    def accept_device(self):
        current_item = self.device_list.currentItem()
        if current_item:
            self.selected_device = current_item.data(Qt.UserRole)
            self.accept()
        else:
            QMessageBox.warning(self, "Selection Error", "Please select a device")

class ApiSubmitThread(QThread):
    """Thread for submitting data to API"""
    result_signal = pyqtSignal(str, bool)  # message, success
    
    def __init__(self, url, username, password, plant_id, json_data, parent=None):
        super().__init__(parent)
        self.url = url
        self.username = username
        self.password = password
        self.plant_id = plant_id
        self.json_data = json_data
        
    def run(self):
        try:
            # Prepare payload
            payload = {
                'username': self.username,
                'password': self.password,
                'plant_id': self.plant_id,
                'data': json.loads(self.json_data)
            }
            
            # Send POST request
            response = requests.post(self.url, json=payload)
            
            # Check response
            if response.status_code == 200:
                self.result_signal.emit(f"Success! API responded with: {response.text}", True)
            else:
                self.result_signal.emit(f"API Error: Status {response.status_code} - {response.text}", False)
                
        except requests.exceptions.RequestException as e:
            self.result_signal.emit(f"Request Error: {str(e)}", False)
        except json.JSONDecodeError:
            self.result_signal.emit("Error: Invalid JSON data", False)
        except Exception as e:
            self.result_signal.emit(f"Error: {str(e)}", False)

class BluetoothJSONApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bt_thread = None
        self.api_thread = None
        self.json_data = None
        
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Bluetooth JSON API Client')
        self.setGeometry(300, 300, 600, 500)
        
        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Bluetooth configuration section
        bt_layout = QGridLayout()
        bt_layout.addWidget(QLabel("HC05 MAC Address:"), 0, 0)
        
        # Device selection row
        addr_layout = QHBoxLayout()
        self.bt_addr_input = QLineEdit("MAC Address of HC05")  # Default/example address
        addr_layout.addWidget(self.bt_addr_input)
        
        self.scan_btn = QPushButton("Scan")
        self.scan_btn.clicked.connect(self.scan_devices)
        addr_layout.addWidget(self.scan_btn)
        
        bt_layout.addLayout(addr_layout, 0, 1)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_bluetooth_connection)
        bt_layout.addWidget(self.connect_btn, 0, 2)
        
        # Status and progress
        bt_layout.addWidget(QLabel("Status:"), 1, 0)
        self.status_label = QLabel("Disconnected")
        bt_layout.addWidget(self.status_label, 1, 1, 1, 2)
        
        bt_layout.addWidget(QLabel("JSON Reception Progress:"), 2, 0)
        self.progress_bar = QProgressBar()
        bt_layout.addWidget(self.progress_bar, 2, 1, 1, 2)
        
        main_layout.addLayout(bt_layout)
        
        # Received data display
        main_layout.addWidget(QLabel("Received Data:"))
        self.data_display = QTextEdit()
        self.data_display.setReadOnly(True)
        main_layout.addWidget(self.data_display)
        
        # User credentials
        cred_layout = QGridLayout()
        cred_layout.addWidget(QLabel("Username:"), 0, 0)
        self.username_input = QLineEdit()
        cred_layout.addWidget(self.username_input, 0, 1)
        
        cred_layout.addWidget(QLabel("Password:"), 1, 0)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        cred_layout.addWidget(self.password_input, 1, 1)
        
        # Added Plant ID field
        cred_layout.addWidget(QLabel("Plant ID:"), 2, 0)
        self.plant_id_input = QLineEdit()
        cred_layout.addWidget(self.plant_id_input, 2, 1)
        
        cred_layout.addWidget(QLabel("API Endpoint:"), 3, 0)
        self.api_endpoint = QLineEdit("http://127.0.0.1:5000/sensor")
        cred_layout.addWidget(self.api_endpoint, 3, 1)
        
        main_layout.addLayout(cred_layout)
        
        # Submit button
        self.submit_btn = QPushButton("Submit to API")
        self.submit_btn.clicked.connect(self.submit_to_api)
        self.submit_btn.setEnabled(False)
        main_layout.addWidget(self.submit_btn)
    
    def scan_devices(self):
        scan_dialog = DeviceScanDialog(self)
        if scan_dialog.exec_() == QDialog.Accepted and scan_dialog.selected_device:
            self.bt_addr_input.setText(scan_dialog.selected_device)
            
    def toggle_bluetooth_connection(self):
        if self.bt_thread is None or not self.bt_thread.isRunning():
            # Start connection
            bt_addr = self.bt_addr_input.text()
            if not bt_addr:
                QMessageBox.warning(self, "Input Error", "Please enter the HC05 MAC address")
                return
                
            self.bt_thread = BluetoothRFCOMMThread(bt_addr)
            self.bt_thread.data_received.connect(self.update_data_display)
            self.bt_thread.connection_status.connect(self.update_status)
            self.bt_thread.progress_update.connect(self.update_progress)
            self.bt_thread.json_complete.connect(self.handle_json_complete)
            
            self.bt_thread.start()
            self.connect_btn.setText("Disconnect")
        else:
            # Stop connection
            self.bt_thread.stop()
            self.connect_btn.setText("Connect")
            
    @pyqtSlot(str)
    def update_data_display(self, data):
        self.data_display.moveCursor(0)  # Move cursor to end
        self.data_display.insertPlainText(data)
        
    @pyqtSlot(str)
    def update_status(self, status):
        self.status_label.setText(status)
        
    @pyqtSlot(int)
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        
    @pyqtSlot(str)
    def handle_json_complete(self, json_str):
        self.json_data = json_str
        self.submit_btn.setEnabled(True)
        QMessageBox.information(self, "JSON Received", "JSON data has been successfully received and parsed.")
        
    def submit_to_api(self):
        username = self.username_input.text()
        password = self.password_input.text()
        plant_id = self.plant_id_input.text()
        api_url = self.api_endpoint.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Input Error", "Please enter both username and password")
            return
            
        if not plant_id:
            QMessageBox.warning(self, "Input Error", "Please enter a Plant ID")
            return
            
        if not api_url:
            QMessageBox.warning(self, "Input Error", "Please enter the API endpoint URL")
            return
            
        if not self.json_data:
            QMessageBox.warning(self, "No Data", "No JSON data has been received yet")
            return
            
        # Submit data to API in a separate thread
        self.submit_btn.setEnabled(False)
        self.api_thread = ApiSubmitThread(api_url, username, password, plant_id, self.json_data)
        self.api_thread.result_signal.connect(self.handle_api_result)
        self.api_thread.start()
        
    @pyqtSlot(str, bool)
    def handle_api_result(self, message, success):
        self.submit_btn.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "API Submission", message)
        else:
            QMessageBox.warning(self, "API Submission Failed", message)
            
    def closeEvent(self, event):
        # First, properly disconnect Bluetooth if connected
        if self.bt_thread and self.bt_thread.isRunning():
            self.bt_thread.stop()
            self.bt_thread.wait()  # Wait for thread to finish
        
        # Also ensure API thread is properly terminated
        if self.api_thread and self.api_thread.isRunning():
            self.api_thread.wait()
            
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BluetoothJSONApp()
    window.show()
    
    # Set up GLib main loop for D-Bus events without threads_init
    main_loop = GLib.MainLoop()
    context = main_loop.get_context()
    
    # Timer to process GLib events
    def process_glib_events():
        while context.pending():
            context.iteration(False)
    
    timer = QTimer()
    timer.timeout.connect(process_glib_events)
    timer.start(100)  # 100ms interval
    
    sys.exit(app.exec_())
