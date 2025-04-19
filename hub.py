import asyncio
import logging
import json
import os
import re
import requests
import time
import subprocess
from flask import Flask, request, jsonify
from bleConnector import BLEConnector

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SmartHub")

app = Flask(__name__)

# Get Minikube IP address
def get_minikube_ip():
    try:
        result = subprocess.run(['minikube', 'ip'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            logger.error(f"Failed to get minikube IP: {result.stderr}")
            return "localhost"
    except Exception as e:
        logger.error(f"Error getting minikube IP: {e}")
        return "localhost"

MINIKUBE_IP = get_minikube_ip()
logger.info(f"Using Minikube IP: {MINIKUBE_IP}")

# Use NodePort services in Minikube
LIGHT_SERVICE_URL = os.environ.get('LIGHT_SERVICE_URL', f'http://{MINIKUBE_IP}:30001')
THERMOSTAT_SERVICE_URL = os.environ.get('THERMOSTAT_SERVICE_URL', f'http://{MINIKUBE_IP}:30002')

logger.info(f"Light service URL: {LIGHT_SERVICE_URL}")
logger.info(f"Thermostat service URL: {THERMOSTAT_SERVICE_URL}")

# Store the latest sensor readings
latest_readings = {
    "temperature": None,
    "light_intensity": None,
    "humidity": None,
    "last_update": None
}

# Settings and thresholds
settings = {
    "temperature_threshold": 24.0,  # Turn on AC if temperature exceeds this
    "light_threshold": 50.0,        # Turn on lights if below this intensity
    "auto_mode": True,              # Automatically adjust devices based on sensors
}

# BLE connector instance
ble_connector = None


@app.route('/api/readings', methods=['GET'])
def get_readings():
    """API endpoint to get the latest sensor readings"""
    return jsonify(latest_readings)


@app.route('/api/settings', methods=['GET', 'POST'])
def manage_settings():
    """API endpoint to get or update settings"""
    global settings
    
    if request.method == 'GET':
        return jsonify(settings)
    
    if request.method == 'POST':
        new_settings = request.json
        # Update only the provided settings
        for key, value in new_settings.items():
            if key in settings:
                settings[key] = value
        
        # Apply the new settings if in auto mode
        if settings["auto_mode"]:
            apply_automation_rules()
        
        return jsonify(settings)


@app.route('/api/devices/light', methods=['GET', 'POST'])
def control_light():
    """API endpoint to control the smart light"""
    if request.method == 'GET':
        try:
            response = requests.get(f"{LIGHT_SERVICE_URL}/api/status")
            return jsonify(response.json())
        except requests.RequestException as e:
            return jsonify({"error": str(e)}), 500
    
    if request.method == 'POST':
        try:
            # Forward the request to the light service
            response = requests.post(
                f"{LIGHT_SERVICE_URL}/api/control",
                json=request.json
            )
            return jsonify(response.json())
        except requests.RequestException as e:
            return jsonify({"error": str(e)}), 500


@app.route('/api/devices/thermostat', methods=['GET', 'POST'])
def control_thermostat():
    """API endpoint to control the thermostat"""
    if request.method == 'GET':
        try:
            response = requests.get(f"{THERMOSTAT_SERVICE_URL}/api/status")
            return jsonify(response.json())
        except requests.RequestException as e:
            return jsonify({"error": str(e)}), 500
    
    if request.method == 'POST':
        try:
            # Forward the request to the thermostat service
            response = requests.post(
                f"{THERMOSTAT_SERVICE_URL}/api/control",
                json=request.json
            )
            return jsonify(response.json())
        except requests.RequestException as e:
            return jsonify({"error": str(e)}), 500


def process_ble_data(data_str):
    """Process data received from BLE UART"""
    logger.info(f"Processing BLE data: {data_str}")
    
    try:
        # Parse temperature data
        temp_match = re.search(r'T:(\d+\.\d+)', data_str)
        if temp_match:
            latest_readings['temperature'] = float(temp_match.group(1))
            logger.info(f"Temperature updated: {latest_readings['temperature']}°C")
        
        # Parse humidity data
        humidity_match = re.search(r'H:(\d+\.\d+)', data_str)
        if humidity_match:
            latest_readings['humidity'] = float(humidity_match.group(1))
            logger.info(f"Humidity updated: {latest_readings['humidity']}%")
            
        # Parse light intensity data 
        light_match = re.search(r'L:(\d+(?:\.\d+)?)', data_str)
        if light_match:
            latest_readings['light_intensity'] = float(light_match.group(1))
            logger.info(f"Light intensity updated: {latest_readings['light_intensity']}%")
        
        # Update the last reading timestamp
        latest_readings['last_update'] = time.time()
            
        # Apply automation rules if enabled
        if settings['auto_mode']:
            apply_automation_rules()
    
    except Exception as e:
        logger.error(f"Error processing BLE data: {e}")


def apply_automation_rules():
    """Apply automation rules based on sensor readings and thresholds"""
    try:
        # Temperature automation
        if latest_readings['temperature'] is not None:
            if latest_readings['temperature'] > settings['temperature_threshold']:
                # It's too hot, turn on cooling
                requests.post(
                    f"{THERMOSTAT_SERVICE_URL}/api/control",
                    json={"mode": "cool", "target_temperature": settings['temperature_threshold'] - 1}
                )
                logger.info(f"Activating cooling to {settings['temperature_threshold'] - 1}°C")
            else:
                # Temperature is comfortable, turn off HVAC
                requests.post(
                    f"{THERMOSTAT_SERVICE_URL}/api/control",
                    json={"mode": "off"}
                )
                logger.info("Deactivating HVAC, temperature is comfortable")
        
        # Light automation
        if latest_readings['light_intensity'] is not None:
            if latest_readings['light_intensity'] < settings['light_threshold']:
                # It's dark, turn on light
                requests.post(
                    f"{LIGHT_SERVICE_URL}/api/control",
                    json={"state": "on", "brightness": 80}
                )
                logger.info("Turning lights on, low light intensity detected")
            else:
                # It's bright, turn off light
                requests.post(
                    f"{LIGHT_SERVICE_URL}/api/control",
                    json={"state": "off"}
                )
                logger.info("Turning lights off, sufficient ambient light")
    
    except Exception as e:
        logger.error(f"Error applying automation rules: {e}")


async def setup_ble_connector():
    """Set up the BLE connector to receive sensor data"""
    global ble_connector

    device_name = os.environ.get('BLE_DEVICE_NAME', 'CIRCUITPY23c6')
    logger.info(f"Setting up BLE connection to device: {device_name}")
    
    # Create BLE connector instance
    ble_connector = BLEConnector(device_name=device_name)
    
    # Register callback for data
    ble_connector.register_data_callback(process_ble_data)
    
    # Register connection status callback
    def on_connection_status(connected):
        if connected:
            logger.info("Connected to BLE device")
        else:
            logger.warning("Disconnected from BLE device")
            
    ble_connector.register_connection_callback(on_connection_status)
    
    # Start the connector
    logger.info("Starting BLE connector")
    await ble_connector.start()


def start_ble_connector_thread():
    """Start BLE connector in a separate thread"""
    import threading
    
    def run_ble_connector():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(setup_ble_connector())
    
    thread = threading.Thread(target=run_ble_connector)
    thread.daemon = True
    thread.start()
    logger.info("BLE connector thread started")


if __name__ == "__main__":
    import time
    
    # Start BLE connector thread immediately
    logger.info("Starting BLE connector thread")
    start_ble_connector_thread()
    
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 5000))
    
    # Run the Flask app
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port)