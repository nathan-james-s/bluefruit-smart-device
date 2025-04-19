# Bluefruit Smart Device Hub

A smart home automation system that integrates with Bluetooth Low Energy (BLE) sensors to monitor environmental conditions and control smart home devices.

## Project Overview

This project creates a smart home automation hub that connects to Adafruit Bluefruit devices to receive sensor data (temperature, humidity, light intensity) and controls smart devices based on that data. The system consists of microservices orchestrated with Kubernetes:

- **Hub Service:** Central controller that processes sensor data and manages device automation
- **Smart Light Service:** Controls smart lighting based on ambient light levels
- **Thermostat Service:** Manages temperature control with cooling/heating modes

## Pervasive Computing Technologies

- **Bluetooth Low Energy (BLE):**
    - Used by both host and the circuitpython to enable wireless sensor communication.

- **IoT and Embedded Systems:**
    - The device code running on the CircuitPython broadcasts sensor data to a hub.

- **Microservices:**
    - Different functionality is split into services which are deployed independently.


## Setup and Installation

### Prerequisites

- Docker
- Minikube
- kubectl
- Python 3.9+
- Adafruit Bluefruit device (optional, system works with simulated data)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/bluefruit-smart-device.git
   cd bluefruit-smart-device
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start Minikube**
   ```bash
   minikube start
   ```

4. **Deploy the services**
   ```bash
   python startHub.py
   ```

   Alternatively, you can deploy services manually:
   ```bash
   # Configure Docker to use Minikube's Docker daemon
   # For Windows:
   & minikube -p minikube docker-env --shell powershell | Invoke-Expression

   # For Linux/macOS:
   eval $(minikube docker-env)

   # Build the Docker images
   docker build -t smart-light:latest -f Dockerfile.light .
   docker build -t thermostat:latest -f Dockerfile.thermostat .

   # Deploy to Kubernetes
   kubectl apply -f k8s-deployment.yaml
   ```

5. **Start the Hub**
   ```bash
   python hub.py
   ```

## Running the Adafruit Bluefruit Device

1. Connect your Adafruit Bluefruit device to your computer.
2. Copy the `code.py` file to the device (it will appear as a USB drive).
3. The device will automatically restart and begin broadcasting sensor data.

## Using the System

### API Endpoints

**Hub Service (default: http://localhost:5000)**
- `GET /api/readings` - Get latest sensor readings
- `GET/POST /api/settings` - Get or update automation settings
- `GET/POST /api/devices/light` - Get status or control the smart light
- `GET/POST /api/devices/thermostat` - Get status or control the thermostat

**Smart Light Service (Kubernetes NodePort: 30001)**
- `GET /api/status` - Get light status
- `POST /api/control` - Control the light (state, brightness)
- `POST /api/toggle` - Toggle the light on/off

**Thermostat Service (Kubernetes NodePort: 30002)**
- `GET /api/status` - Get thermostat status
- `POST /api/control` - Control thermostat (mode, temperature, fan)

## Automation

The system will automatically:

- Turn on lights when light intensity falls below the threshold.
- Turn on cooling when temperature exceeds the threshold.
- Update humidity readings from the sensor.

## Troubleshooting

- **BLE Device Not Connecting**: Ensure the device name in `hub.py` matches your Bluefruit device.
- **Services Not Starting**: Check Minikube status with `minikube status`.
- **API Connection Issues**: Verify the correct Minikube IP with `minikube ip`.