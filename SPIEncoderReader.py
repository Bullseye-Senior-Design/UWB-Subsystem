#!/usr/bin/env python3
"""SPI encoder reader for the front wheel encoder.

This module keeps the original SPIEncoderReader name for compatibility, but the
implementation now follows the FrontWheelEncoder class style and SPI protocol.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from typing import Optional

import spidev

logger = logging.getLogger("SPIEncoderReader")
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")


class Constants:
	"""Default SPI settings for the front wheel encoder.

	Replace these values with your project-specific configuration if needed.
	"""
	spi_bus = 0
	frontwheel_encoder_spi_device = 0
	frontwheel_encoder_max_freq_hz = 100
	frontwheel_encoder_spi_mode = 0
	frontwheel_encoder_resolution = 1
	frontwheel_encoder_max_position = (1 << frontwheel_encoder_resolution) - 1


class FrontWheelEncoder:
	def __init__(self):
		self._spi: Optional[spidev.SpiDev] = None
		self._position: Optional[int] = None
		self._running = False
		self._lock = threading.Lock()
		self._interval = 0.1
		self._thread: Optional[threading.Thread] = None
		self._last_read_time: Optional[float] = None
		self._read_count = 0
		self._error_count = 0

		self._resolution = Constants.frontwheel_encoder_resolution
		self._max_position = Constants.frontwheel_encoder_max_position
		self.resolution = self._resolution
		self.max_position = self._max_position

		try:
			self._spi = spidev.SpiDev()
			self._spi.open(Constants.spi_bus, Constants.frontwheel_encoder_spi_device)
			self._spi.max_speed_hz = Constants.frontwheel_encoder_max_freq_hz
			self._spi.mode = Constants.frontwheel_encoder_spi_mode

			logger.info(
				"FrontWheelEncoder SPI initialized on bus %s, device %s, mode %s",
				Constants.spi_bus,
				Constants.frontwheel_encoder_spi_device,
				Constants.frontwheel_encoder_spi_mode,
			)

			self.run()
		except Exception as e:
			logger.error(f"Failed to initialize SPI for FrontWheelEncoder: {e}")
			self._spi = None

	def run(self):
		"""Start monitoring the encoder in a background thread."""
		if self._running:
			logger.warning("FrontWheel encoder already running. Ignoring run() call.")
			return

		self._running = True

		def _update_loop():
			while self._running:
				time.sleep(self._interval)
				self.read_position()

		self._thread = threading.Thread(target=_update_loop, daemon=True)
		self._thread.start()

	def get_position(self) -> Optional[float]:
		"""Return the front wheel angle in degrees."""
		with self._lock:
			if self._position is None:
				return None
			return (self._position / self._max_position) * 360.0

	def read_position(self) -> Optional[int]:
		"""Read raw encoder position data via SPI and return the position."""
		if not self._running or not self._spi:
			return None

		try:
			response = self._spi.xfer2([0xFF, 0xFF, 0xFF, 0xFF])

			data_high = response[1]
			data_low = response[2]
			inv_high = response[3]
			inv_low = response[0]

			raw = (data_high << 8) | data_low
			inv = (inv_high << 8) | inv_low

			logger.debug(f"SPI response: {response}, raw={raw}, inv={inv}")

			binary = self._gray_to_binary(raw)
			position = binary & self._max_position

			with self._lock:
				self._position = position
				self._last_read_time = time.time()
				self._read_count += 1

			return position

		except Exception as e:
			logger.error(f"FrontWheelEncoder SPI read error: {e}")
			with self._lock:
				self._error_count += 1
			return None

	def _gray_to_binary(self, n: int) -> int:
		result = n
		while n > 0:
			n >>= 1
			result ^= n
		return result

	def _get_angle(self, position: int, bits: int = 14) -> float:
		max_val = (1 << bits) - 1
		return (position / max_val) * 360.0

	def close(self):
		if self._spi:
			try:
				self._running = False
				if self._thread:
					self._thread.join(timeout=1)
				self._spi.close()
				self._spi = None
			except Exception:
				pass

	def start(self):
		"""Compatibility alias for run()."""
		self.run()

	def stop(self):
		"""Compatibility alias for close()."""
		self.close()

	def get_position_degrees(self) -> Optional[float]:
		"""Compatibility helper returning the latest position in degrees."""
		return self.get_position()

	def get_position_radians(self) -> Optional[float]:
		"""Return the latest position in radians."""
		position = self.get_position()
		if position is None:
			return None
		return math.radians(position)

	def get_statistics(self) -> dict:
		with self._lock:
			return {
				"running": self._running,
				"position": self._position,
				"resolution": self._resolution,
				"max_position": self._max_position,
				"read_count": self._read_count,
				"error_count": self._error_count,
				"last_read_time": self._last_read_time,
			}

	def __enter__(self):
		self.start()
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.stop()


class SPIEncoderReader(FrontWheelEncoder):
	"""Backward-compatible name for existing code paths."""

	def __init__(self, bus: int = 0, device: int = 0, max_speed_hz: int = 1_000_000,
				 spi_mode: int = 0, bits_per_word: int = 8, resolution: int = 14,
				 interval: float = 0.1):
		self.bus = bus
		self.device = device
		self.max_speed_hz = max_speed_hz
		self.spi_mode = spi_mode
		self.bits_per_word = bits_per_word
		self.resolution = resolution
		self.interval = interval

		Constants.spi_bus = bus
		Constants.frontwheel_encoder_spi_device = device
		Constants.frontwheel_encoder_max_freq_hz = max_speed_hz
		Constants.frontwheel_encoder_spi_mode = spi_mode
		Constants.frontwheel_encoder_resolution = resolution
		Constants.frontwheel_encoder_max_position = (1 << resolution) - 1

		super().__init__()


def main():
	"""Example usage of FrontWheelEncoder."""
	reader = FrontWheelEncoder()

	try:
		logger.info("Reading encoder position every 100ms. Press Ctrl+C to stop.")
		while True:
			position = reader.read_position()
			if position is not None:
				degrees = reader.get_position()
				logger.info(f"Position: {position:4d}  angle={degrees:7.3f}°")
			else:
				logger.warning("Failed to read position")
			time.sleep(0.1)
	except KeyboardInterrupt:
		logger.info("Interrupted by user")
	finally:
		reader.close()
		logger.info("Encoder reader stopped")


if __name__ == "__main__":
	main()
