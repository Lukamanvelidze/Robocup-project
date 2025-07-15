# -*- encoding: UTF-8 -*-

import math
import argparse
import numpy as np
from naoqi import ALProxy
import shutil
class MoveClient(object):
    def __init__(self, server_ip="nao1.local", server_port=65432):
        super(MoveClient,self).__init__()
        self.motionProxy = ALProxy("ALMotion", server_ip, server_port)
        self.postureProxy = ALProxy("ALRobotPosture", server_ip, server_port)
        
    def get_sensor(self, ip , port):
        memProx = ALProxy("ALMemory", ip, port)
        #GyrX = memProx.getData("Device/SubDeviceList/InertialSensor/GyrX/Sensor/Value")
        angle = memProx.getData("Device/SubDeviceList/InertialSensor/AngleY/Sensor/Value") 
        return angle

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
        ip = "nao1.local"
        port = 9559
        footStepsList = []

        # 1.Step left foot forward
        footStepsList.append([["LLeg"], [[0.06, 0.1, 0.0]]])
        # 2) Move your right foot to your left foot
        footStepsList.append([["RLeg"], [[0.00, -0.1, 0.0]]])
        # made one step forward (repeat n times)

        stepFrequency = 0.8
        clearExisting = False
        n = 5 # defined the number of cycle to make

        for j in range( n ):
            if(np.abs(self.get_sensor(ip, port)) > 1.5):
                self.postureProxy.goToPosture("StandInit", 1.0)
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="192.168.1.118",
                        help="Robot ip address")
    parser.add_argument("--port", type=int, default=9559,
                        help="Robot port number")

    args = parser.parse_args()
