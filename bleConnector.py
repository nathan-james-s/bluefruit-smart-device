import asyncio
import logging
from typing import Optional, Dict, Any, Callable, List
import re

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# Nordic UART Service UUIDs
UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # Write to this characteristic
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # Notifications come from this characteristic

class BLEConnector:
    """
    Manages persistent connections to BLE devices and handles UART data.
    """
    def __init__(self, 
                 device_name: str = None, 
                 device_address: str = None,
                 scan_timeout: float = 5.0,
                 connection_timeout: float = 10.0,
                 reconnect_delay: float = 2.0,
                 max_reconnect_attempts: int = 5):
        """
        Initialize the BLE connector.
        
        Args:
            device_name: Name of the BLE device to connect to (optional if address is provided)
            device_address: MAC address of the BLE device (optional if name is provided)
            scan_timeout: Maximum time to scan for devices (in seconds)
            connection_timeout: Maximum time to wait for a connection (in seconds)
            reconnect_delay: Time to wait between reconnection attempts (in seconds)
            max_reconnect_attempts: Maximum number of reconnection attempts before giving up
        """
        if not device_name and not device_address:
            raise ValueError("Either device_name or device_address must be provided")
        
        self.device_name = device_name
        self.device_address = device_address
        self.scan_timeout = scan_timeout
        self.connection_timeout = connection_timeout
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        
        self.device: Optional[BLEDevice] = None
        self.client: Optional[BleakClient] = None
        self.is_connected = False
        self.is_running = False
        self.reconnect_attempts = 0
        
        self.advertisement_callbacks: List[Callable[[BLEDevice, AdvertisementData], None]] = []
        self.connection_callbacks: List[Callable[[bool], None]] = []
        self.data_callbacks: List[Callable[[str], None]] = []
        
        # Set up logging
        self.logger = logging.getLogger("BLEConnector")
        self.logger.setLevel(logging.INFO)
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def register_advertisement_callback(self, callback: Callable[[BLEDevice, AdvertisementData], None]):
        """Register a callback function to process advertisement data."""
        self.advertisement_callbacks.append(callback)
    
    def register_connection_callback(self, callback: Callable[[bool], None]):
        """Register a callback function to be notified of connection status changes."""
        self.connection_callbacks.append(callback)
    
    def register_data_callback(self, callback: Callable[[str], None]):
        """Register a callback function to process UART data."""
        self.data_callbacks.append(callback)
    
    def _notify_connection_status(self, connected: bool):
        """Notify all registered callbacks of connection status change."""
        for callback in self.connection_callbacks:
            try:
                callback(connected)
            except Exception as e:
                self.logger.error(f"Error in connection callback: {e}")
    
    def _process_advertisement(self, device: BLEDevice, adv_data: AdvertisementData):
        """Process advertisement data from the device."""
        for callback in self.advertisement_callbacks:
            try:
                callback(device, adv_data)
            except Exception as e:
                self.logger.error(f"Error in advertisement callback: {e}")
    
    def _process_uart_data(self, data: str):
        """Process UART data received from the device."""
        # First, print the data to the console
        self.logger.info(f"Received data: {data}")
        
        # Try to parse temperature and humidity data
        try:
            # Look for T:xx.xx,H:xx.xx format
            match = re.search(r'T:(\d+\.\d+),H:(\d+\.\d+)', data)
            if match:
                temp = float(match.group(1))
                humidity = float(match.group(2))
                self.logger.info(f"Parsed values - Temperature: {temp}°C, Humidity: {humidity}%")
        except Exception as e:
            self.logger.warning(f"Could not parse data: {e}")
        
        # Notify all registered callbacks
        for callback in self.data_callbacks:
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"Error in data callback: {e}")
    
    async def _find_device(self) -> Optional[BLEDevice]:
        """Scan for and find the target BLE device."""
        self.logger.info(f"Scanning for device: {self.device_name or self.device_address}")
        
        if self.device_address:
            device = await BleakScanner.find_device_by_address(
                self.device_address, timeout=self.scan_timeout
            )
            if device:
                return device
        
        # If address not provided or device not found by address, scan by name
        if self.device_name:
            devices = await BleakScanner.discover(timeout=self.scan_timeout)
            for device in devices:
                if device.name and self.device_name.lower() in device.name.lower():
                    self.device_address = device.address
                    return device
        
        return None
    
    def _notification_handler(self, sender, data):
        """Handle notifications received from the UART TX characteristic."""
        try:
            # Try to decode the data as UTF-8
            decoded_data = data.decode('utf-8').strip()
            self._process_uart_data(decoded_data)
        except Exception as e:
            self.logger.error(f"Error handling notification: {e}")
            # If decoding fails, log the raw data
            self.logger.info(f"Raw data: {data}")
    
    async def _connect_to_device(self) -> bool:
        """Establish connection to the device and set up notification handling."""
        if not self.device:
            self.logger.error("No device found to connect to")
            return False
        
        try:
            self.logger.info(f"Connecting to {self.device.name} ({self.device.address})")
            
            # Define disconnect callback
            def disconnection_handler(client):
                self.logger.warning(f"Disconnected from {self.device.name}")
                self.is_connected = False
                self._notify_connection_status(False)
                # No need to manually reconnect here as the main loop will handle it
            
            # Create client with disconnection callback
            self.client = BleakClient(
                self.device, 
                disconnected_callback=disconnection_handler,
                timeout=self.connection_timeout
            )
            
            # Connect to the device
            await self.client.connect()
            self.is_connected = True
            self.reconnect_attempts = 0
            self.logger.info(f"Connected to {self.device.name}")
            
            # Check for UART service
            services = await self.client.get_services()
            if services.get_service(UART_SERVICE_UUID):
                self.logger.info("UART Service found")
                
                # Set up notification handler for the TX characteristic
                await self.client.start_notify(
                    UART_TX_CHAR_UUID, 
                    self._notification_handler
                )
                self.logger.info("UART notifications enabled")
            else:
                self.logger.warning("UART Service not found on device")
            
            self._notify_connection_status(True)
            return True
            
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            self.is_connected = False
            return False
    
    async def setup_advertisement_listener(self):
        """Set up a listener for advertisements from the target device."""
        self.logger.info("Setting up advertisement listener")
        
        def callback(device: BLEDevice, advertisement_data: AdvertisementData):
            if (self.device_address and device.address == self.device_address) or \
               (self.device_name and device.name and self.device_name.lower() in device.name.lower()):
                self._process_advertisement(device, advertisement_data)
        
        # Start the scanner with the callback
        scanner = BleakScanner()
        scanner.register_detection_callback(callback)
        await scanner.start()
        return scanner
    
    async def start(self):
        """Start the BLE connector and maintain connection."""
        self.is_running = True
        
        # Start advertisement listener
        scanner = await self.setup_advertisement_listener()
        
        try:
            while self.is_running:
                # If not connected, try to find and connect to the device
                if not self.is_connected:
                    self.device = await self._find_device()
                    
                    if self.device:
                        connection_successful = await self._connect_to_device()
                        
                        if not connection_successful:
                            self.reconnect_attempts += 1
                            if self.reconnect_attempts >= self.max_reconnect_attempts:
                                self.logger.error(f"Failed to connect after {self.max_reconnect_attempts} attempts")
                                await asyncio.sleep(30)  # Wait longer before trying again
                                self.reconnect_attempts = 0
                                continue
                            
                            self.logger.info(f"Retrying connection in {self.reconnect_delay} seconds")
                            await asyncio.sleep(self.reconnect_delay)
                            continue
                    else:
                        self.logger.warning("Device not found, retrying scan...")
                        await asyncio.sleep(self.reconnect_delay)
                        continue
                
                # If connected, just keep the connection alive
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Error in BLE connector: {e}")
        finally:
            # Clean up
            await scanner.stop()
            if self.client and self.is_connected:
                try:
                    await self.client.stop_notify(UART_TX_CHAR_UUID)
                except:
                    pass
                await self.client.disconnect()
            self.is_running = False
            self.logger.info("BLE connector stopped")
    
    async def stop(self):
        """Stop the BLE connector."""
        self.is_running = False
        if self.client and self.is_connected:
            try:
                await self.client.stop_notify(UART_TX_CHAR_UUID)
            except:
                pass
            await self.client.disconnect()
            self.is_connected = False
    
    async def send_data(self, data: str) -> bool:
        """Send data to the UART service."""
        if not self.is_connected or not self.client:
            self.logger.error("Not connected to device")
            return False
        
        try:
            # Encode the string to bytes and send to the RX characteristic
            await self.client.write_gatt_char(UART_RX_CHAR_UUID, data.encode('utf-8'))
            return True
        except Exception as e:
            self.logger.error(f"Error sending data: {e}")
            return False


# Example usage showing how to capture and process the sensor data
async def main():
    # Create a connector with your device name
    # Replace "CircuitPython" with your actual device name
    connector = BLEConnector(device_name="CIRCUITPY23c6")
    
    # Register a callback for received data
    def on_data_received(data):
        print(f"Data received: {data}")
        
        # Parse the data (assuming format like "T:22.15,H:52.15")
        try:
            match = re.search(r'T:(\d+\.\d+),H:(\d+\.\d+)', data)
            if match:
                temp = float(match.group(1))
                humidity = float(match.group(2))
                print(f"Temp: {temp}°C, Humidity: {humidity}%")
                
                # Here you could do something with the data, like:
                # - Save to a database
                # - Update a visualization
                # - Trigger an action based on thresholds
        except Exception as e:
            print(f"Error parsing data: {e}")
    
    # Register the callback
    connector.register_data_callback(on_data_received)
    
    # Start the connector
    await connector.start()

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the main function
    asyncio.run(main())