
import time
import threading
from datetime import datetime
import logging

logger = logging.getLogger("ProximitySensor")
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

import RPi.GPIO as GPIO

class LimitSwitchReader:
	def __init__(self, pin: int, active_high: bool = True, pull_up: bool = True, debounce_ms: int = 50,
				 edge: str = 'both'):
		"""Create a gpio pin reader.

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
		self.state = False  # True after rising edge, False after falling edge

	def _gpio_callback(self, channel):
		# Read the current pin state to determine edge direction
		current_value = GPIO.input(channel)
		
		# Set state based on edge detection
		# If current value is HIGH, it was a rising edge -> state = True
		# If current value is LOW, it was a falling edge -> state = False
		with self._lock:
			self.state = bool(current_value)
		
		logger.debug(f"GPIO callback triggered on pin {channel}, state={self.state}")

	def start(self):
		"""Start monitoring the GPIO pin"""
		self._running = True

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

	def get_state(self):
		"""Get the current edge state (True=rising edge occurred, False=falling edge occurred)"""
		with self._lock:
			return self.state

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

	reader = LimitSwitchReader(pin=4,
								   active_high=True,
								   pull_up=True,
								   debounce_ms=1,
								   edge='both')  # Changed to 'both' to detect both edges
	try:
		reader.start()
		# measure frequency every second
		interval = 2.0
		while True:
			time.sleep(interval)
			# Read and display the current state
			current_state = reader.get_state()
			logger.info(f"Current state: {current_state} ({'RISING edge' if current_state else 'FALLING edge'})")

	except KeyboardInterrupt:
		logger.info("Interrupted by user")
	except Exception as e:
		logger.error(f"Runtime error: {e}")
	finally:
		reader.stop()
		logger.info("Stopped")

if __name__ == '__main__':
	main()

