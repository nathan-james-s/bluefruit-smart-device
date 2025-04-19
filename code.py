"""
Author: Nathan Strandberg
Date: 04/19/2025
Title: Smart Hub Bluefruit
Description: This code is for locking and unlocking the device. Once unlocked, it will print the temperature readings.
"""

import time
import board
import random
import analogio
import adafruit_thermistor
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

# Initialize the BLE radio
ble = BLERadio()
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)

thermistor = adafruit_thermistor.Thermistor(board.TEMPERATURE, 10000, 10000, 25, 3950)
light_sensor = analogio.AnalogIn(board.LIGHT)

# Function to get light intensity as a percentage
def get_light_percentage():
    # Convert analog reading to percentage (0-100%)
    # Assumes 16-bit analog reading (0-65535)
    raw_value = light_sensor.value
    percentage = (raw_value / 65535) * 100
    return percentage

# Function to get sensor data
def get_sensor_data():
    try:
        # Read temperature from thermistor (in Celsius)
        temperature = thermistor.temperature
        
        # Simulate humidity reading (for example purposes)
        humidity = random.uniform(40.0, 60.0)

        # Read light intensity as percentage
        light_intensity = get_light_percentage()
        
        return f"T:{temperature:.2f},H:{humidity:.2f},L:{light_intensity:.2f}"
    except RuntimeError as e:
        # DHT sensors can sometimes fail to read
        print(f"Sensor reading error: {e}")
        return "Error reading sensors"

print("Starting BLE UART service")

# Make sure we're not already advertising before starting
if ble.advertising:
    ble.stop_advertising()

# Initial advertisement start
ble.start_advertising(advertisement)

while True:
    # Advertise until we're connected
    while not ble.connected:
        print("Waiting for connection...")
        # Only start advertising if we're not already advertising
        if not ble.advertising:
            ble.start_advertising(advertisement)
        time.sleep(0.5)

    # Connected, so stop advertising
    if ble.advertising:
        ble.stop_advertising()
    print("Connected!")

    # Loop as long as we're connected
    while ble.connected:
        # Get the data to send
        data_to_send = get_sensor_data()

        # Send it over UART
        uart.write(f"{data_to_send}\n".encode("utf-8"))
        print(f"Sent: {data_to_send}")

        # Wait before sending the next update
        time.sleep(5.0)

    print("Disconnected!")
