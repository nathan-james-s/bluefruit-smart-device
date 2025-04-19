import os
import logging
import time
from flask import Flask, request, jsonify

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SmartLight")

app = Flask(__name__)

# Light state
light_state = {
    "state": "off",        # "on" or "off"
    "brightness": 0,       # 0-100
    "last_changed": None   # Timestamp of last state change
}


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get the current status of the light"""
    return jsonify(light_state)


@app.route('/api/control', methods=['POST'])
def control_light():
    """Control the light"""
    global light_state
    
    # Get the request data
    data = request.json
    changed = False
    
    # Update state if provided
    if 'state' in data:
        state = data['state'].lower()
        if state in ['on', 'off'] and state != light_state['state']:
            light_state['state'] = state
            changed = True
            logger.info(f"Light turned {state}")
    
    # Update brightness if provided and light is on
    if 'brightness' in data and light_state['state'] == 'on':
        brightness = int(max(0, min(100, data['brightness'])))  # 0-100
        if brightness != light_state['brightness']:
            light_state['brightness'] = brightness
            changed = True
            logger.info(f"Brightness set to {brightness}%")
    
    # Update timestamp if any changes were made
    if changed:
        light_state['last_changed'] = time.time()
    
    # Return the current state
    return jsonify(light_state)


@app.route('/api/toggle', methods=['POST'])
def toggle_light():
    """Toggle the light on/off"""
    global light_state
    
    # Toggle the state
    new_state = "off" if light_state['state'] == 'on' else "on"
    light_state['state'] = new_state
    
    # If turning on, set brightness to last value or default to 100
    if new_state == 'on' and light_state['brightness'] == 0:
        light_state['brightness'] = 100
    
    # If turning off, set brightness to 0
    if new_state == 'off':
        light_state['brightness'] = 0
    
    # Update timestamp
    light_state['last_changed'] = time.time()
    
    logger.info(f"Light toggled to {new_state}")
    
    # Return the current state
    return jsonify(light_state)


if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 5001))
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=port)