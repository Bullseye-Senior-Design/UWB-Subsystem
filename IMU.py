# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT
import adafruit_bno055
import board

class IMU(Subsystem):
    def __init__(self):
        
        i2c = board.I2C() # uses board.SCL and board.SDA
        self.sensor = adafruit_bno055.BNO055_I2C(i2c)

        self.acceleration = []
        self.gyro = []
        self.comsThead = ComsThread()

    def getGyroData(self):
        return self.sensor.gyro
    
    def getAccelData(self):
        return self.sensor.acceleration
    
    def getMagData(self):
        return self.sensor.magnetic

    def periodic(self):
        #FOR DEBUG
        print("Gyro X:%.2f, Y: %.2f, Z: %.2f radians/s" % (self.getGyroData()))
        print("Accel X:%.2f, Y: %.2f, Z: %.2f m/s^2" % (self.getAccelData()))
        print("Mag X:%.2f, Y: %.2f, Z: %.2f microteslas" % (self.getMagData()))      
             
    def end(self):
        pass

def main():
    imu = IMU()
    while True:
        imu.periodic()