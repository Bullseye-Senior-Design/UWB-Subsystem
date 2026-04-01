#!/usr/bin/env python3
# ERC 05SPI 360 Reader for Raspberry Pi (bit-banged open-drain SPI)
# Works with any 3.3 V → 5 V level shifter (pull-up MUST be on 5 V side)

import RPi.GPIO as GPIO
import time

# ================== PIN ASSIGNMENTS (BCM numbering) ==================
CS_PIN   = 22   # Change if you used a different pin
CLK_PIN  = 17
DATA_PIN = 27

# ====================================================================
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Setup CS and CLK as outputs
GPIO.setup(CS_PIN,  GPIO.OUT)
GPIO.setup(CLK_PIN, GPIO.OUT)
GPIO.output(CS_PIN,  GPIO.HIGH)
GPIO.output(CLK_PIN, GPIO.LOW)

# DATA will be switched between INPUT (high-Z) and OUTPUT LOW
print("=== ERCS SPI 360 Reader (Raspberry Pi) ===")
print(f"Using pins: CS={CS_PIN}, CLK={CLK_PIN}, DAT={DATA_PIN}")
print("Pull-up resistor must be on the 5V encoder side of the level shifter!\n")

def spi_byte(tx):
    """Send one byte and read response (open-drain style on DAT)"""
    rx = 0
    for bit in range(7, -1, -1):
        # Drive bit (1 = high-Z so pull-up on 5V side wins, 0 = drive low)
        if tx & (1 << bit):
            GPIO.setup(DATA_PIN, GPIO.IN)          # high-Z
        else:
            GPIO.setup(DATA_PIN, GPIO.OUT)
            GPIO.output(DATA_PIN, GPIO.LOW)

        GPIO.output(CLK_PIN, GPIO.HIGH)            # clock rising edge
        if GPIO.input(DATA_PIN):
            rx |= (1 << bit)
        GPIO.output(CLK_PIN, GPIO.LOW)             # falling edge
    return rx

def read_encoder():
    """Read full frame and return 14-bit angle or -1 on error"""
    rx = [0] * 10

    GPIO.output(CS_PIN, GPIO.LOW)
    time.sleep(0.00001)          # 10 µs minimum after /SS low

    rx[0] = spi_byte(0xAA)
    for i in range(1, 10):
        rx[i] = spi_byte(0xFF)

    GPIO.output(CS_PIN, GPIO.HIGH)

    # Data bytes: rx[2]=MSB, rx[3]=LSB, rx[4]=~MSB, rx[5]=~LSB
    data = (rx[2] << 8) | rx[3]
    inv  = (rx[4] << 8) | rx[5]

    # Print raw bytes for debugging
    print("Raw RX : ", end="")
    for b in rx:
        print(f"{b:02X} ", end="")
    print()

    print(f"Data   : 0x{data:04X}   ~Data : 0x{inv:04X}   XOR = 0x{data ^ inv:04X}")

    if (data ^ inv) == 0xFFFF:
        angle = ((data & 0x3FFF) * 360.0) / 16384.0
        print(f"→ VALID ANGLE: {angle:.2f}°")
        return angle
    else:
        print("→ CRC / Communication Error")
        return -1

try:
    while True:
        read_encoder()
        print("-" * 50)
        time.sleep(0.2)          # 5 reads per second — change as needed

except KeyboardInterrupt:
    print("\nStopped by user")
finally:
    GPIO.cleanup()