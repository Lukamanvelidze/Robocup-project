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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="192.168.1.118",
                        help="Robot ip address")
    parser.add_argument("--port", type=int, default=9559,
                        help="Robot port number")

    args = parser.parse_args()


