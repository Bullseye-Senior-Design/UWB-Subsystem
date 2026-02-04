#!/usr/bin/env python3
"""
SPIEncoderReader.py

Reads encoder position from a 4-wire SPI encoder (SE33SPI signal type).

SPI Bus Lines:
- MOSI (Master Out Slave In): Data output from Raspberry Pi to encoder
- MISO (Master In Slave Out): Data input from encoder to Raspberry Pi
- SCLK (Serial Clock): Clock signal output from Raspberry Pi
- SS/CS (Slave Select/Chip Select): Active low chip select output from Raspberry Pi

Features:
- Works on Raspberry Pi using spidev library
- Supports absolute position reading
- Thread-safe position tracking
- Configurable SPI parameters (speed, mode, bits per word)

Hardware notes:
- Raspberry Pi SPI0 uses GPIO pins:
  * GPIO 10 (MOSI) - SPI0_MOSI
  * GPIO 9 (MISO) - SPI0_MISO
  * GPIO 11 (SCLK) - SPI0_SCLK
  * GPIO 8 (CE0) - SPI0_CE0_N (Slave Select 0)
  * GPIO 7 (CE1) - SPI0_CE1_N (Slave Select 1)
- SPI1 uses GPIO 19, 20, 21 (alternative SPI interface)
- Enable SPI interface using raspi-config or by adding 'dtparam=spi=on' to /boot/config.txt

Wiring example:
  Encoder VCC -> 3.3V or 5V (check encoder datasheet)
  Encoder GND -> Pi GND
  Encoder MOSI -> Pi GPIO 10 (MOSI)
  Encoder MISO -> Pi GPIO 9 (MISO)
  Encoder SCLK -> Pi GPIO 11 (SCLK)
  Encoder CS -> Pi GPIO 8 (CE0) or GPIO 7 (CE1)
"""

import time
import threading
from typing import Optional, Tuple
import logging

logger = logging.getLogger("SPIEncoderReader")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

import spidev



class SPIEncoderReader:
	def __init__(self, bus: int = 0, device: int = 0, max_speed_hz: int = 1000000, 
				 spi_mode: int = 0, bits_per_word: int = 8, resolution: int = 14):
		"""Create an SPI encoder reader.

		Args:
			bus: SPI bus number (0 or 1 on Raspberry Pi)
			device: SPI device/chip select (0 for CE0, 1 for CE1)
			max_speed_hz: SPI clock speed in Hz (default 1 MHz)
			spi_mode: SPI mode (0-3), defines clock polarity and phase
			bits_per_word: Number of bits per word (typically 8)
			resolution: Encoder resolution in bits (e.g., 14 for 16384 positions)
		"""
		self.bus = bus
		self.device = device
		self.max_speed_hz = max_speed_hz
		self.spi_mode = spi_mode
		self.bits_per_word = bits_per_word
		self.resolution = resolution
		self.max_position = (1 << resolution) - 1  # e.g., 16383 for 14-bit

		self._spi: Optional[spidev.SpiDev] = None
		self._running = False
		self._lock = threading.Lock()
		
		self._current_position: Optional[int] = None
		self._last_read_time: Optional[float] = None
		self._read_count = 0
		self._error_count = 0

	def _init_spi(self):
		"""Initialize SPI connection"""
		self._spi = spidev.SpiDev()
		self._spi.open(self.bus, self.device)
		self._spi.max_speed_hz = self.max_speed_hz
		self._spi.mode = self.spi_mode
		self._spi.bits_per_word = self.bits_per_word
		logger.info(f"SPI initialized: bus={self.bus}, device={self.device}, "
					f"speed={self.max_speed_hz}Hz, mode={self.spi_mode}")

	def _read_raw_position(self) -> Optional[int]:
		"""Read raw position data from encoder via SPI.
		
		For SE33SPI encoders, the typical protocol is:
		- Send a read command (or dummy bytes)
		- Receive position data (typically 2 bytes for 12-bit resolution)
		
		Returns:
			Raw position value (0 to max_position) or None on error
		"""
		if not self._spi:
			return None

		try:
			# For most SPI absolute encoders:
			# Send 2-3 bytes of 0x00 to clock out the position data
			# Adjust based on your specific encoder protocol
			bytes_to_read = (self.resolution + 7) // 8  # Round up to nearest byte
			if bytes_to_read < 2:
				bytes_to_read = 2
			
			# Read data from encoder
			data = self._spi.readbytes(bytes_to_read)
			
			# Parse position based on resolution
			# For 12-bit encoder in 2 bytes: MSB first
			# Example: [0x1F, 0xA3] -> 0x1FA3 (12 bits used)
			position = 0
			for byte_val in data:
				position = (position << 8) | byte_val
			
			# Mask to resolution bits
			position &= self.max_position
			
			return position

		except Exception as e:
			logger.error(f"SPI read error: {e}")
			with self._lock:
				self._error_count += 1
			return None

	def start(self):
		"""Start the encoder reader"""
		if self._running:
			logger.warning("Encoder reader already running")
			return

		self._running = True
		self._init_spi()
		logger.info(f"Started SPI encoder reader (resolution: {self.resolution} bits, "
					f"max position: {self.max_position})")

	def stop(self):
		"""Stop the encoder reader and cleanup"""
		self._running = False
		
		if self._spi:
			try:
				self._spi.close()
				self._spi = None
				logger.info("SPI connection closed")
			except Exception as e:
				logger.error(f"Error closing SPI: {e}")

	def read_position(self) -> Optional[int]:
		"""Read current encoder position.
		
		Returns:
			Current position (0 to max_position) or None on error
		"""
		if not self._running or not self._spi:
			logger.warning("Encoder reader not running")
			return None

		position = self._read_raw_position()
		
		if position is not None:
			with self._lock:
				self._current_position = position
				self._last_read_time = time.time()
				self._read_count += 1
		
		return position

	def get_position_degrees(self) -> Optional[float]:
		"""Read current position in degrees (0-360).
		
		Returns:
			Position in degrees or None on error
		"""
		position = self.read_position()
		if position is None:
			return None
		
		# Convert position to degrees
		degrees = (position / self.max_position) * 360.0
		return degrees

	def get_position_radians(self) -> Optional[float]:
		"""Read current position in radians (0-2π).
		
		Returns:
			Position in radians or None on error
		"""
		position = self.read_position()
		if position is None:
			return None
		
		# Convert position to radians
		import math
		radians = (position / self.max_position) * 2.0 * math.pi
		return radians

	def get_statistics(self) -> dict:
		"""Get reader statistics.
		
		Returns:
			Dictionary with read count, error count, last position, etc.
		"""
		with self._lock:
			return {
				'read_count': self._read_count,
				'error_count': self._error_count,
				'current_position': self._current_position,
				'last_read_time': self._last_read_time,
				'running': self._running
			}

	def reset_statistics(self):
		"""Reset statistics counters"""
		with self._lock:
			self._read_count = 0
			self._error_count = 0

	def __enter__(self):
		"""Context manager entry"""
		self.start()
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		"""Context manager exit"""
		self.stop()


def main():
	"""Example usage of SPIEncoderReader"""
	
	# Create encoder reader
	# Adjust parameters based on your encoder specifications
	reader = SPIEncoderReader(
		bus=0,              # SPI bus 0
		device=0,           # CE0 (chip select 0)
		max_speed_hz=1667,  # 0.6ms
		spi_mode=0,         # SPI mode 0 (check encoder datasheet)
		bits_per_word=8,
		resolution=14       # 14-bit encoder (16384 positions)
	)

	try:
		reader.start()
		
		logger.info("Reading encoder position every 100ms. Press Ctrl+C to stop.")
		logger.info(f"Encoder resolution: {reader.resolution} bits ({reader.max_position + 1} positions)")
		
		while True:
			# Read raw position
			position = reader.read_position()
			
			if position is not None:
				# Also get position in degrees
				degrees = reader.get_position_degrees()
				radians = reader.get_position_radians()
				
				logger.info(f"Position: {position:4d}/{reader.max_position} "
						   f"({degrees:6.2f}°, {radians:.4f} rad)")
			else:
				logger.warning("Failed to read position")
			
			# Display statistics every 50 reads
			stats = reader.get_statistics()
			if stats['read_count'] > 0 and stats['read_count'] % 50 == 0:
				error_rate = (stats['error_count'] / stats['read_count']) * 100
				logger.info(f"Statistics - Reads: {stats['read_count']}, "
						   f"Errors: {stats['error_count']} ({error_rate:.1f}%)")
			
			time.sleep(0.1)  # 100ms between reads

	except KeyboardInterrupt:
		logger.info("Interrupted by user")
	except Exception as e:
		logger.error(f"Runtime error: {e}", exc_info=True)
	finally:
		reader.stop()
		logger.info("Encoder reader stopped")


if __name__ == '__main__':
	main()
