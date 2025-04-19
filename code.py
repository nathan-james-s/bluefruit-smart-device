"""
Author: Nathan Strandberg
Date: 03/11/2025
Title: Term Project
Description: This code is for locking and unlocking the device. Once unlocked, it will print the temperature readings.
"""

import time
import board
import random
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

# Initialize the BLE radio
ble = BLERadio()
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)

# Function to generate sample test data
def get_sensor_data():
    # This is just an example - replace with your actual sensor readings
    temperature = random.uniform(20.0, 30.0)
    humidity = random.uniform(40.0, 60.0)
    light_intensity = random.uniform(10.0, 90.0)  # Light intensity from 10-90%
    return f"T:{temperature:.2f},H:{humidity:.2f},L:{light_intensity:.2f}"

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
        time.sleep(1.0)

    print("Disconnected!")

