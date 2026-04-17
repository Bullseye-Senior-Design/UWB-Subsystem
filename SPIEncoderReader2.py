import spidev
import time
import RPi.GPIO as GPIO

# Initialize SPI
spi = spidev.SpiDev()
spi.open(0, 0) # Bus 0, Device 0 (CE0)

# Settings based on datasheet
# Max frequency response is 5kHz, so a 1MHz clock is plenty safe
spi.max_speed_hz = 1000000 
# SPI Mode: The timing diagram suggests Mode 0 or 1. 
# Most Hall sensors use Mode 0 (CPOL=0, CPHA=0)
spi.mode = 0 

pin = 24  # GPIO pin connected to SS (Slave Select) of the encoder

#GPIO.setmode(GPIO.BCM)

#GPIO.setup(pin, GPIO.OUT)
#GPIO.output(pin, GPIO.LOW)

def get_encoder_value():
    # To read 2 bytes, we send 2 dummy bytes
    # The SS line is automatically pulled low by xfer2
    resp = spi.xfer2([0x00, 0x00], 50000)
    print (f"SPI Response: {resp}")
    
    # Combine the two 8-bit bytes into one 16-bit integer
    # (High Byte << 8) OR (Low Byte)
    full_word = (resp[0] << 8) | resp[1]
    
    # The encoder is 14-bit. 
    # Usually, the 14 bits are the MSBs or LSBs of the 16-bit word.
    # If the datasheet outputs raw 14-bit data shifted left:
    # position = (full_word >> 2) 
    
    # If it is raw 14-bit data in the 14 LSBs:
    position = full_word & 0x3FFF
    
    return position

def convert_to_degrees(raw_value):
    # 360 degrees / 16384 steps
    return (raw_value * 360.0) / 16384.0

try:
    print("Reading ERCFS Encoder (Press Ctrl+C to stop)...")
    while True:
        raw = get_encoder_value()
        deg = convert_to_degrees(raw)
        #print("am here")
        print(f"Raw: {raw:5} | Degrees: {deg:6.2f}")
        time.sleep(0.1) # Update rate is 0.6ms, so 100ms is safe for display

except KeyboardInterrupt:
    spi.close()
    GPIO.cleanup()
    print("\nCommunication stopped.")