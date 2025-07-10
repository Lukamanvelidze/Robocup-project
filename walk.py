# -*- encoding: UTF-8 -*-

import math
import argparse
from naoqi import ALProxy

def main(robotIP="192.168.1.118", PORT=9559):
    motionProxy  = ALProxy("ALMotion", robotIP, PORT)
    postureProxy = ALProxy("ALRobotPosture", robotIP, PORT)

    # Wake up robot
    motionProxy.wakeUp()

    # Send robot to Pose Init
    postureProxy.goToPosture("StandInit", 0.5)

    # Example showing the moveTo command
    # The units for this command are meters and radians
    x  = 1          #that is forward
    y  = 0          # this is right
    theta  = math.pi/2
    motionProxy.moveTo(x, y, theta)
    # Will block until move Task is finished

    ########
    # NOTE #
    ########
    # If moveTo() method does nothing on the robot,
    # read the section about walk protection in the
    # Locomotion control overview page.

    # Go to rest position
    motionProxy.rest()

    def walk(self, robotIP, PORT, angle):
        motionProxy  = ALProxy("ALMotion", robotIP, PORT)
        postureProxy = ALProxy("ALRobotPosture", robotIP, PORT)

        # Wake up robot
        motionProxy.wakeUp()

        # Send robot to Pose Init
        postureProxy.goToPosture("StandInit", 0.5)

        # Example showing the moveTo command
        # The units for this command are meters and radians
        x  = 1          #that is forward
        y  = 0          # this is right
        #theta  = math.pi/2
        angle = max(-90, min(90, angle))  # nur innerhalb ±90°
        theta = math.radians(angle)
        motionProxy.moveTo(x, y, theta)
        # Will block until move Task is finished

        ########
        # NOTE #
        ########
        # If moveTo() method does nothing on the robot,
        # read the section about walk protection in the
        # Locomotion control overview page.

        # Go to rest position
        motionProxy.rest()

    def walk_slow(robotIP, PORT=9559):

        motionProxy  = ALProxy("ALMotion", robotIP, PORT)
        postureProxy = ALProxy("ALRobotPosture", robotIP, PORT)

        # Wake up robot
        motionProxy.wakeUp()

        # Send robot to Stand Init
        postureProxy.goToPosture("StandInit", 0.5)

        ###############################
        # First we defined each step
        ###############################
        footStepsList = []

        # 1) Step forward with your left foot
        footStepsList.append([["LLeg"], [[0.06, 0.1, 0.0]]])

        # 2) Sidestep to the left with your left foot
        #footStepsList.append([["LLeg"], [[0.00, 0.16, 0.0]]])

        # 3) Move your right foot to your left foot
        footStepsList.append([["RLeg"], [[0.00, -0.1, 0.0]]])

        # 4) Sidestep to the left with your left foot
        #footStepsList.append([["LLeg"], [[0.00, 0.16, 0.0]]])

        # 5) Step backward & left with your right foot
        #footStepsList.append([["RLeg"], [[-0.04, -0.1, 0.0]]])

        # 6)Step forward & right with your right foot
        #footStepsList.append([["RLeg"], [[0.00, -0.16, 0.0]]])

        # 7) Move your left foot to your right foot
        #footStepsList.append([["LLeg"], [[0.00, 0.1, 0.0]]])

        # 8) Sidestep to the right with your right foot
        #footStepsList.append([["RLeg"], [[0.00, -0.16, 0.0]]])

        ###############################
        # Send Foot step
        ###############################
        stepFrequency = 0.8
        clearExisting = False
        nbStepDance = 2 # defined the number of cycle to make

        for j in range( nbStepDance ):
            for i in range( len(footStepsList) ):
                try:
                    motionProxy.setFootStepsWithSpeed(
                        footStepsList[i][0],
                        footStepsList[i][1],
                        [stepFrequency],
                        clearExisting)
                except:
                    print ("This example is not allowed on this robot.")
                    exit()


        motionProxy.waitUntilMoveIsFinished()

        # Go to rest position
        motionProxy.rest()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="192.168.1.118",
                        help="Robot ip address")
    parser.add_argument("--port", type=int, default=9559,
                        help="Robot port number")

    args = parser.parse_args()
    main(args.ip, args.port)