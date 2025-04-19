import os
import logging
import time
from flask import Flask, request, jsonify

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Thermostat")

app = Flask(__name__)

# Thermostat state
thermostat_state = {
    "mode": "off",                  # "off", "heat", "cool", "auto"
    "current_temperature": 22.0,    # Current temperature in Celsius
    "target_temperature": 22.0,     # Target temperature in Celsius
    "fan": "auto",                  # "auto" or "on"
    "humidity": 50.0,               # Current humidity percentage
    "last_changed": None            # Timestamp of last state change
}


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get the current status of the thermostat"""
    return jsonify(thermostat_state)


@app.route('/api/control', methods=['POST'])
def control_thermostat():
    """Control the thermostat"""
    global thermostat_state
    
    # Get the request data
    data = request.json
    changed = False
    
    # Update mode if provided
    if 'mode' in data:
        mode = data['mode'].lower()
        if mode in ['off', 'heat', 'cool', 'auto'] and mode != thermostat_state['mode']:
            thermostat_state['mode'] = mode
            changed = True
            logger.info(f"Thermostat mode set to {mode}")
    
    # Update target temperature if provided
    if 'target_temperature' in data:
        try:
            temp = float(data['target_temperature'])
            # Limit to reasonable range (10-35°C)
            temp = max(10.0, min(35.0, temp))
            if temp != thermostat_state['target_temperature']:
                thermostat_state['target_temperature'] = temp
                changed = True
                logger.info(f"Target temperature set to {temp}°C")
        except (ValueError, TypeError):
            pass
    
    # Update fan setting if provided
    if 'fan' in data:
        fan = data['fan'].lower()
        if fan in ['auto', 'on'] and fan != thermostat_state['fan']:
            thermostat_state['fan'] = fan
            changed = True
            logger.info(f"Fan set to {fan}")
    
    if 'current_temperature' in data:
        try:
            temp = float(data['current_temperature'])
            thermostat_state['current_temperature'] = temp
            changed = True
            logger.info(f"Current temperature set to {temp}°C")
        except (ValueError, TypeError):
            pass
    
    # Update timestamp if any changes were made
    if changed:
        thermostat_state['last_changed'] = time.time()
    
    # Return the current state
    return jsonify(thermostat_state)


if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 5002))
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=port)