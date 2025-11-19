#!/usr/bin/env python3
"""
ProximitySensor.py

Reads a digital GPIO pin from a TAISS M12 4mm 5V DC proximity sensor.

Features:
- Works on Raspberry Pi using RPi.GPIO (BCM numbering)

Important hardware notes:
- Raspberry Pi GPIOs are NOT 5V tolerant. Do NOT connect the sensor output directly to
  a Pi GPIO if the sensor drives 5V. Use an appropriate level shifter, an open-collector
  sensor output with a 3.3V pull-up, or a simple voltage divider (when safe) to convert
  the output to 3.3V logic.
- Many proximity sensors offer NPN (open-collector) or PNP outputs. For NPN (open-collector)
  you can pull the line up to 3.3V on the Pi. For PNP or push-pull outputs, ensure the output
  doesn't drive 5V into the GPIO.

Wiring example (NPN open-collector preferred):
  Sensor V+ -> 5V
  Sensor GND -> Pi GND
  Sensor output -> Pi GPIO input pin with internal pull-up disabled and external 3.3V pull-up
  (or use Pi internal pull-up if the sensor is open-collector and output will never drive 5V)
"""

import time
import threading
from datetime import datetime
import logging

logger = logging.getLogger("ProximitySensor")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

import RPi.GPIO as GPIO



class ProximitySensorReader:
	def __init__(self, pin: int, active_high: bool = True, pull_up: bool = True, debounce_ms: int = 50,
				 edge: str = 'both'):
		"""Create a proximity sensor reader.

		Args:
			pin: BCM GPIO pin number to read (e.g., 17)
			active_high: True if sensor output is HIGH when object detected
			pull_up: True to enable pull-up, False for pull-down (when using internal pull)
			debounce_ms: Debounce time in milliseconds
			edge: 'rising', 'falling', or 'both' (which edge to detect)
		"""
		self.pin = pin
		self.active_high = active_high
		self.pull_up = pull_up
		self.debounce_ms = debounce_ms
		self.edge = edge.lower()

		self._running = False
		self._lock = threading.Lock()
		self._last_event_time = 0.0

		# internal history for optional export

	def _normalize_present(self, raw_state: int) -> bool:
		# raw_state is 0 or 1
		return raw_state == (1 if self.active_high else 0)

	def _gpio_callback(self, channel):
		now = time.time()
		# with self._lock:
		# 	if (now - self._last_event_time) * 1000.0 < self.debounce_ms:
		# 		return
		# 	self._last_event_time = now

		try:
			raw = GPIO.input(self.pin)
		except Exception as e:
			logger.error(f"GPIO read failed in callback: {e}")
			return

		present = self._normalize_present(raw)
		ts = now
		logger.info(f"Event: present={present} raw={raw} time={datetime.fromtimestamp(ts).isoformat()}")

	def start(self):
		"""Start monitoring the GPIO pin"""

		GPIO.setmode(GPIO.BCM)

		pud = GPIO.PUD_UP if self.pull_up else GPIO.PUD_DOWN
		GPIO.setup(self.pin, GPIO.IN, pull_up_down=pud)

		# Determine edge type
		if self.edge == 'both':
			gedge = GPIO.BOTH
		elif self.edge == 'rising':
			gedge = GPIO.RISING
		elif self.edge == 'falling':
			gedge = GPIO.FALLING
		else:
			gedge = GPIO.BOTH

		GPIO.add_event_detect(self.pin, gedge, callback=self._gpio_callback, bouncetime=self.debounce_ms)
		logger.info(f"Started monitoring GPIO {self.pin} (active_high={self.active_high})")

	def stop(self):
		"""Stop monitoring and cleanup"""
		self._running = False

		if GPIO is not None:
			try:
				GPIO.remove_event_detect(self.pin)
			except Exception:
				pass
			# Don't call GPIO.cleanup() globally to avoid affecting other users; only cleanup pin
			try:
				GPIO.cleanup(self.pin)
			except Exception:
				pass

def main():

	reader = ProximitySensorReader(pin=4,
								   active_high=True,
								   pull_up=True,
								   debounce_ms=9,
								   edge='rising')
	try:
		reader.start()


		time.sleep(100)

	except KeyboardInterrupt:
		logger.info("Interrupted by user")
	except Exception as e:
		logger.error(f"Runtime error: {e}")
	finally:
		reader.stop()
		logger.info("Stopped")

if __name__ == '__main__':
	main()

