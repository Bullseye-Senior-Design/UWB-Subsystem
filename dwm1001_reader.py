#!/usr/bin/env python3
"""
DWM1001-DEV Tag Position Reader

This program reads position data from a DWM1001-DEV Ultra-Wideband (UWB) tag.
The DWM1001-DEV communicates via UART/Serial interface and provides real-time
location data in a RTLS (Real Time Location System) network.

Requirements:
- pyserial library for serial communication
- DWM1001-DEV tag configured as a tag in RTLS network
- Proper COM port connection

Author: Generated for UWB Subsystem
Date: October 15, 2025
"""

import serial
import time
import json
import struct
import threading
import csv
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Position:
    """Data class to store position information"""
    x: float
    y: float
    z: float
    quality: int
    timestamp: float

@dataclass
class TagInfo:
    """Data class to store tag information"""
    node_id: str
    position: Optional[Position] = None
    battery_level: Optional[int] = None
    update_rate: Optional[int] = None

class DWM1001Manager:
    """
    Class to handle communication with DWM1001-DEV tag and read position data
    """
    
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0):
        """
        Initialize the DWM1001 reader
        
        Args:
            port: Serial port (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux)
            baudrate: Serial communication baud rate (default: 115200)
            timeout: Serial read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_connection: Optional[serial.Serial] = None
        self.is_connected = False
        self.is_reading = False
        self.tag_info = TagInfo(node_id="unknown")
        self.read_thread = None
        
    def connect(self) -> bool:
        """
        Establish serial connection to DWM1001-DEV tag
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            
            # Wait for connection to stabilize
            time.sleep(2)
            
            # Test connection by sending shell command
            self.serial_connection.write(b'\r\n')
            time.sleep(0.1)
            
            # Enter shell mode
            self.serial_connection.write(b'shell\r\n')
            time.sleep(0.5)
            
            self.is_connected = True
            logger.info(f"Successfully connected to DWM1001-DEV on {self.port}")
            return True
            
        except serial.SerialException as e:
            logger.error(f"Failed to connect to {self.port}: {e}")
            return False
    
    def disconnect(self):
        """Close the serial connection"""
        self.stop_reading()
        if self.serial_connection and self.serial_connection.is_open:
            # Exit shell mode before closing
            try:
                self.serial_connection.write(b'quit\r\n')
                time.sleep(0.5)
            except:
                pass
            self.serial_connection.close()
            logger.info("Disconnected from DWM1001-DEV")
        self.is_connected = False
    
    def get_position(self) -> Optional[Position]:
        """
        Get current position from the tag
        
        Returns:
            Position object or None if unsuccessful
        """
        if not self.is_connected or not self.serial_connection:
            logger.error("Not connected to DWM1001-DEV")
            return None
        
        try:
            # Send position request command
            self.serial_connection.write(b'lep\r\n')  # Location Engine Position
            time.sleep(0.1) # TODO check if needed
            
            # Read response
            response = self.serial_connection.read_until(b'\n').decode('utf-8', errors='ignore').strip()
            
            # Parse position data
            # Expected format: "POS,x,y,z,quality"
            if 'POS' in response:
                return self._parse_position(response)
            else:
                logger.warning(f"No position data in response: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return None
    
    def _parse_position(self, response: str) -> Optional[Position]:
        """
        Parse position data from DWM1001 response
        
        Args:
            response: Raw response string from DWM1001
            
        Returns:
            Position object or None if parsing fails
        """
        try:
            # Split response by commas
            parts = response.split(',')
            
            # Extract position coordinates and quality
            # Skip the first part 'POS'
            x = float(parts[1])
            y = float(parts[2])
            z = float(parts[3])
            quality = int(parts[4])

            position = Position(
                x=x,
                y=y, 
                z=z,
                quality=quality,
                timestamp=time.time()
            )
            
            return position
            
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing position data: {e}")
            return None
    
    def get_node_info(self) -> Dict[str, Any]:
        """
        Get node information from the tag
        
        Returns:
            Dictionary containing node information
        """
        if not self.is_connected or not self.serial_connection:
            logger.error("Not connected to DWM1001-DEV")
            return {}
        
        info = {}
        
        try:
            # Get node ID
            self.serial_connection.write(b'si\r\n')  # System Info
            time.sleep(0.1)
            response = self.serial_connection.read_until(b'\n').decode('utf-8', errors='ignore').strip()
            
            # Parse system info
            if 'node_id' in response.lower():
                # Extract node ID from response
                parts = response.split()
                for i, part in enumerate(parts):
                    if 'node_id' in part.lower() and i + 1 < len(parts):
                        info['node_id'] = parts[i + 1]
                        self.tag_info.node_id = parts[i + 1]
                        break
            
            # Get update rate
            self.serial_connection.write(b'pur\r\n')  # Position Update Rate
            time.sleep(0.1)
            response = self.serial_connection.read_until(b'\n').decode('utf-8', errors='ignore').strip()
            
            if 'upd' in response.lower():
                # Parse update rate
                try:
                    rate = int(''.join(filter(str.isdigit, response)))
                    info['update_rate'] = rate
                    self.tag_info.update_rate = rate
                except ValueError:
                    pass
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting node info: {e}")
            return {}
    
    def start_continuous_reading(self, interval: float = 0.1, csv_filename: str = "position_data.csv"):
        """
        Start continuous position reading in a separate thread
        
        """
        if self.is_reading:
            logger.warning("Already reading continuously")
            return
        
        self.is_reading = True
        
        def read_loop():
            while self.is_reading:
                position = self.get_position()
                if position:
                    self.tag_info.position = position
                                        
                    # Save to CSV if enabled
                    self.save_position_to_csv(position, csv_filename)
                    
                    # Call user callback
                    self.print_position(position)
                time.sleep(interval) # TODO check if needed
        
        self.read_thread = threading.Thread(target=read_loop, daemon=True)
        self.read_thread.start()
        
        
        logger.info("Started continuous position reading")
    
    def save_position_to_csv(self, position: Position, filename: str = "position_data.csv") -> bool:
        """
        Save a position reading to a CSV file
        
        Args:
            position: Position object to save
            filename: CSV filename (default: "position_data.csv")
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if file exists to determine if we need to write headers
            file_exists = os.path.exists(filename)
            
            # Open file in append mode
            with open(filename, 'a', newline='') as csvfile:
                fieldnames = ['timestamp', 'datetime', 'x', 'y', 'z', 'quality']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # Write header if file is new
                if not file_exists:
                    writer.writeheader()
                    logger.info(f"Created new CSV file: {filename}")
                
                # Write position data
                writer.writerow({
                    'timestamp': position.timestamp,
                    'datetime': datetime.fromtimestamp(position.timestamp).isoformat(),
                    'x': position.x,
                    'y': position.y,
                    'z': position.z,
                    'quality': position.quality,
                })
                
            return True
            
        except Exception as e:
            logger.error(f"Error saving position to CSV: {e}")
            return False
    
    def clear_csv_file(self, filename: str = "position_data.csv") -> bool:
        """
        Clear/wipe the CSV file by removing it or creating a new empty one with headers
        
        Args:
            filename: CSV filename to clear (default: "position_data.csv")
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Remove the file if it exists
            if os.path.exists(filename):
                os.remove(filename)
                logger.info(f"Cleared existing CSV file: {filename}")
            
            # Create new file with headers only
            with open(filename, 'w', newline='') as csvfile:
                fieldnames = ['timestamp', 'datetime', 'x', 'y', 'z', 'quality']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                logger.info(f"Created fresh CSV file with headers: {filename}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing CSV file: {e}")
            return False
    
    def stop_reading(self):
        """Stop continuous position reading"""
        self.is_reading = False
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join()
        logger.info("Stopped continuous position reading")

    def print_position(self, position: Position):
        """
        Callback function to handle new position data
        
        Args:
            position: Position object with current location data
        """
        print(f"Position: X={position.x:.3f}m, Y={position.y:.3f}m, Z={position.z:.3f}m, "
            f"Quality={position.quality}, Time={position.timestamp:.2f}")

def main():
    """
    Main function demonstrating DWM1001-DEV position reading
    """
    print("DWM1001-DEV Position Reader")
    print("=" * 40)
    
    # Configuration
    COM_PORT = 'COM3'  # Change this to your actual COM port
    BAUDRATE = 115200
    filename = "position_data.csv"
    
    # Create reader instance
    manager = DWM1001Manager(port=COM_PORT, baudrate=BAUDRATE)
        
    # clear CSV file
    manager.clear_csv_file(filename)
    print(f"CSV file '{filename}' cleared and ready for new data.")
    
    
    try:
        # Connect to tag
        print(f"\nConnecting to DWM1001-DEV on {COM_PORT}...")
        if not manager.connect():
            print("Failed to connect. Please check:")
            print("- COM port is correct")
            print("- DWM1001-DEV is connected and powered")
            print("- No other applications are using the COM port")
            return
        
        # Get tag information
        print("\nGetting tag information...")
        info = manager.get_node_info()
        if info:
            print(f"Node ID: {info.get('node_id', 'Unknown')}")
            print(f"Update Rate: {info.get('update_rate', 'Unknown')} Hz")
        
        # Get single position reading
        print("\nGetting position...")
        position = manager.get_position()
        if position:
            manager.print_position(position)
        else:
            print("No position data available")
            print("Make sure the tag is part of a RTLS network with anchors")
        
        # Start continuous reading
        print("\nStarting continuous position reading (Press Ctrl+C to stop)...")
        manager.start_continuous_reading(interval=0.1, csv_filename=filename)
        
        # Keep the program running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping position reading...")
        print(f"Position history exported to: {filename}")
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        manager.disconnect()
        print("Program terminated")

if __name__ == "__main__":
    main()