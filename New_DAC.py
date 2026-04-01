#!/usr/bin/env python3
"""Bit-banged SPI driver for a 12-bit DAC.

This module mirrors the command-word mapping used by the existing `spidev`
implementation, but sends the frame manually using `RPi.GPIO`.

It is intended for Raspberry Pi systems where you want full control over the
SPI waveform without using the kernel SPI controller.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

try:
	import RPi.GPIO as GPIO
except Exception:  # pragma: no cover - allows imports on non-RPi systems
	GPIO = None


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class BitBangDAC:
	"""Bit-banged DAC writer.

	Expected command mapping:
	  - channel 0: 0x3000 | value
	  - channel 1: 0xB000 | value

	The value is treated as normalized input in the range 0.0 .. 1.0 and
	converted to a 12-bit integer (0 .. 4095).
	"""

	def __init__(
		self,
		cs_pin: int = 7,
		clk_pin: int = 11,
		data_pin: int = 10,
		max_value: int = 4095,
		setup_delay: float = 0.0001,
		clock_delay: float = 0.0001,
	):
		self.cs_pin = cs_pin
		self.clk_pin = clk_pin
		self.data_pin = data_pin
		self._max_value = max_value
		self._setup_delay = setup_delay
		self._clock_delay = clock_delay
		self._available = GPIO is not None

		if not self._available:
			logger.warning("RPi.GPIO is unavailable; BitBangDAC will operate as a no-op")
			return

		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)

		GPIO.setup(self.cs_pin, GPIO.OUT)
		GPIO.setup(self.clk_pin, GPIO.OUT)
		GPIO.setup(self.data_pin, GPIO.OUT)

		GPIO.output(self.cs_pin, GPIO.HIGH)
		GPIO.output(self.clk_pin, GPIO.LOW)
		GPIO.output(self.data_pin, GPIO.LOW)

		logger.info(
			"BitBangDAC initialized on CS=%s CLK=%s DATA=%s",
			self.cs_pin,
			self.clk_pin,
			self.data_pin,
		)

	def write(self, channel: int, input_value: float) -> None:
		"""Write a normalized value to the selected DAC channel.

		Args:
			channel: DAC channel index. Channel 0 and 1 are supported.
			input_value: Normalized output in the range 0.0 .. 1.0.
		"""
		if not self._available:
			return

		value = int(input_value * self._max_value)
		value = max(0, min(self._max_value, value))

		if channel == 0:
			command = 0x3000 | value
		else:
			command = 0xB000 | value

		logger.debug(
			"Writing to DAC channel %s: input=%.3f, value=%s, command=0x%04X",
			channel,
			input_value,
			value,
			command,
		)

		self._send_word(command)

	def _send_word(self, word: int) -> None:
		"""Shift out a 16-bit word MSB-first."""
		GPIO.output(self.cs_pin, GPIO.LOW)
		time.sleep(self._setup_delay)

		for bit in range(15, -1, -1):
			if word & (1 << bit):
				GPIO.output(self.data_pin, GPIO.HIGH)
			else:
				GPIO.output(self.data_pin, GPIO.LOW)

			time.sleep(self._setup_delay)
			GPIO.output(self.clk_pin, GPIO.HIGH)
			time.sleep(self._clock_delay)
			GPIO.output(self.clk_pin, GPIO.LOW)

		time.sleep(self._setup_delay)
		GPIO.output(self.cs_pin, GPIO.HIGH)

	def close(self) -> None:
		if not self._available:
			return

		try:
			GPIO.output(self.cs_pin, GPIO.HIGH)
			GPIO.output(self.clk_pin, GPIO.LOW)
			GPIO.output(self.data_pin, GPIO.LOW)
		finally:
			GPIO.cleanup()

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.close()


def main() -> None:
	"""Simple demo that sweeps both channels."""
	logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

	dac = BitBangDAC()
	try:
		while True:
			for level in (0.0, 0.25, 0.5, 0.75, 1.0):
				dac.write(0, level)
				dac.write(1, 1.0 - level)
				time.sleep(0.5)
	except KeyboardInterrupt:
		logger.info("Stopped by user")
	finally:
		dac.close()


if __name__ == "__main__":
	main()
