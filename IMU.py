# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT
import board
import digitalio
import busio

import adafruit_bno055

class IMU():
    def __init__(self):
        
        i2c = board.I2C() # uses board.SCL and board.SDA
        self.sensor = adafruit_bno055.BNO055_I2C(i2c)

        self.acceleration = []
        self.gyro = []

    def getGyroData(self):
        return self.sensor.gyro
    
    def getAccelData(self):
        return self.sensor.acceleration
    
    def getMagData(self):
        return self.sensor.magnetic

    def getEulerData(self):
        return self.sensor.euler   

    def periodic(self):
        #FOR DEBUG
        #print("Gyro X:%.2f, Y: %.2f, Z: %.2f radians/s" % (self.getGyroData()))
        #print("Accel X:%.2f, Y: %.2f, Z: %.2f m/s^2" % (self.getAccelData()))
        #print("Mag X:%.2f, Y: %.2f, Z: %.2f microteslas" % (self.getMagData()))  
        orientation = self.getEulerData()
        if all(v is not None for v in orientation):
            heading, roll, pitch = orientation
            print(f"Heading: {heading:.2f}°, Roll: {roll:.2f}°, Pitch: {pitch:.2f}°")
        else:
            print("Waiting for sensor data...")    
             
    def end(self):
        pass

def main():
    imu = IMU()
    while True:
        imu.periodic()

if __name__ == "__main__":
    main()