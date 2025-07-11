# -*- encoding: UTF-8 -*-

import math
import argparse
from naoqi import ALProxy
import shutil
class MoveClient(object):
    def __init__(self, server_ip="nao1.local", server_port=65432):
        super(MoveClient,self).__init__()
        self.motionProxy = ALProxy("ALMotion", server_ip, server_port)
        self.postureProxy = ALProxy("ALRobotPosture", server_ip, server_port)

    def posture_init(self):
        self.motionProxy.wakeUp()
        #self.postureProxy.goToPosture("StandInit", 0.5)

    def rest(self):
        self.motionProxy.rest()

    def moveTo(self,x,y,theta):
        # x is lef and right, y is for and towards in meters
        self.motionProxy.moveTo(x,y,theta)
        # Will block until move Task is finished so we cant use any if statements to stop it from walking

    # Walk only one step at a time so we can use sonar sensor to detect obstacles
    def walk_slow(self):
        ip = "192.168.1.118"
        PORT = 9559
        footStepsList = []

        # 1.Step left foot forward
        footStepsList.append([["LLeg"], [[0.06, 0.1, 0.0]]])
        # 2) Move your right foot to your left foot
        footStepsList.append([["RLeg"], [[0.00, -0.1, 0.0]]])
        # made one step forward (repeat n times)

        stepFrequency = 0.8
        clearExisting = False
        n = 2 # defined the number of cycle to make

        for j in range( n ):
            if (self.get_sensor_data(ip,PORT) == 0):
                break
            for i in range( len(footStepsList) ):
                try:
                    self.motionProxy.setFootStepsWithSpeed(
                        footStepsList[i][0],
                        footStepsList[i][1],
                        [stepFrequency],
                        clearExisting)
                except:
                    print ("This example is not allowed on this robot.")
                    exit()
    
        self.motionProxy.waitUntilMoveIsFinished()

    def get_sensor_data(self, ip, PORT):

        memoryProxy = ALProxy("ALMemory", ip, PORT)
        sonarProxy = ALProxy("ALSonar", ip, PORT)

        sonarProxy.subscribe("myApplication")

        Gyr = [0.0,0.0]
        GyrX = memoryProxy.getData("Device/SubDeviceList/InertialSensor/GyrX/Sensor/Value")
        GyrY = memoryProxy.getData("Device/SubDeviceList/InertialSensor/GyrY/Sensor/Value")
        print ("Gyrometers value X: %.3f, Y: %.3f" % (GyrX, GyrY))
        Gyr[0] = GyrX
        Gyr[1] = GyrY
        
        SD = [0.0,0.0]
        # Now you can retrieve sonar data from ALMemory.
        # Get sonar left first echo (distance in meters to the first obstacle).
        SD[0] = memoryProxy.getData("Device/SubDeviceList/US/Left/Sensor/Value")

        # Same thing for right.
        SD[1] = memoryProxy.getData("Device/SubDeviceList/US/Right/Sensor/Value")
        print ("Sonar value L: %.3f, R: %.3f" % (SD[0], SD[1]))
        # Unsubscribe from sonars, this will stop sonars (at hardware level)
        sonarProxy.unsubscribe("myApplication")
        return SD, Gyr

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="192.168.1.118",
                        help="Robot ip address")
    parser.add_argument("--port", type=int, default=9559,
                        help="Robot port number")

    args = parser.parse_args()