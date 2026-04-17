#!/usr/bin/env python3
"""Set a GPIO pin low.

Usage:
  python set_gpio_low.py --pin 17 --backend sysfs
  python set_gpio_low.py --pin 17 --backend rpi --mode bcm

Backends:
  rpi   - Use RPi.GPIO (Raspberry Pi). Requires RPi.GPIO installed.
  sysfs - Use /sys/class/gpio interface (generic Linux). Usually requires root.
"""

from __future__ import annotations
import argparse
import logging
import os
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def set_low_rpi(pin: int, mode: str = "bcm") -> None:
    try:
        import RPi.GPIO as GPIO
    except Exception as e:
        raise RuntimeError("RPi.GPIO backend requested but RPi.GPIO is not available") from e

    if mode.lower() == "bcm":
        GPIO.setmode(GPIO.BCM)
    else:
        GPIO.setmode(GPIO.BOARD)

    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)
    # Small delay to ensure value is set before cleanup
    time.sleep(0.01)
    GPIO.cleanup()


def set_low_sysfs(pin: int) -> None:
    gpio_path = f"/sys/class/gpio/gpio{pin}"

    try:
        if not os.path.exists(gpio_path):
            with open("/sys/class/gpio/export", "w") as f:
                f.write(str(pin))

        # Wait for the kernel to create the gpio directory
        for _ in range(20):
            if os.path.exists(gpio_path):
                break
            time.sleep(0.01)

        direction_path = os.path.join(gpio_path, "direction")
        value_path = os.path.join(gpio_path, "value")

        with open(direction_path, "w") as f:
            f.write("out")

        with open(value_path, "w") as f:
            f.write("0")

    except PermissionError as e:
        raise RuntimeError("Permission denied while accessing /sys/class/gpio. Try running with sudo.") from e
    except FileNotFoundError as e:
        raise RuntimeError("sysfs GPIO interface not available on this system.") from e


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Set a GPIO pin low.")
    p.add_argument("--pin", "-p", type=int, required=True, help="GPIO pin number (BCM or physical depending on mode)")
    p.add_argument("--backend", "-b", choices=("rpi", "sysfs"), default="sysfs", help="Backend to use")
    p.add_argument("--mode", "-m", choices=("bcm", "board"), default="bcm", help="Pin numbering mode for rpi backend")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    try:
        if args.backend == "rpi":
            logging.info(f"Using RPi.GPIO backend, mode={args.mode}, pin={args.pin}")
            set_low_rpi(args.pin, args.mode)
        else:
            logging.info(f"Using sysfs backend, pin={args.pin}")
            set_low_sysfs(args.pin)

    except Exception as e:
        logging.error("Failed to set GPIO low: %s", e)
        return 2

    logging.info("Pin set low successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
