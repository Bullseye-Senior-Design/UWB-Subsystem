import smbus2
import time
import struct

# Configuration
I2C_BUS = 1         
I2C_ADDR = 0x50     

# Register mapping for Quaternions
REG_QUAT = 0x51    # Starts at 0x51 and spans to 0x54

def read_sensor_data(bus, reg, length):
    """
    Reads a block of bytes from the I2C sensor and unpacks them into 
    signed 16-bit little-endian integers.
    """
    try:
        data = bus.read_i2c_block_data(I2C_ADDR, reg, length)
        format_string = '<' + 'h' * (length // 2)
        return struct.unpack(format_string, bytearray(data))
    except Exception as e:
        print(f"I2C Read Error at register {hex(reg)}: {e}")
        return None

def main():
    with smbus2.SMBus(I2C_BUS) as bus:
        print(f"Connected to I2C bus {I2C_BUS}. Reading Quaternions...")
        
        while True:
            # We must read 8 bytes this time (4 quaternion components * 2 bytes each)
            quat_data = read_sensor_data(bus, REG_QUAT, 8)
            
            if quat_data:
                # Formula: Quaternion = Raw Value / 32768.0
                q0 = quat_data[0] / 32768.0  # W (Scalar)
                q1 = quat_data[1] / 32768.0  # X
                q2 = quat_data[2] / 32768.0  # Y
                q3 = quat_data[3] / 32768.0  # Z
                
                print(f"Quaternion -> W: {q0:6.3f} | X: {q1:6.3f} | Y: {q2:6.3f} | Z: {q3:6.3f}")
                
            time.sleep(0.1)

if __name__ == "__main__":
    main()