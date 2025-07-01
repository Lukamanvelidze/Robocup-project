#! /usr/bin/env python
# -*- encoding: UTF-8 -*-

"""Example: Get Signal from Front Microphone & Calculate its rms Power"""

import qi
import argparse
import sys
import time
import numpy as np


class SoundProcessingModule(object):
    """
    A simple get signal from the front microphone of Nao & calculate its rms power.
    It requires numpy.
    """

    def __init__( self, app):
        """
        Initialise services and variables.
        """
        super(SoundProcessingModule, self).__init__()
        app.start()
        session = app.session

        # Get the service ALAudioDevice.
        self.audio_service = session.service("ALAudioDevice")
        self.isProcessingDone = False
        self.nbOfFramesToProcess = 20
        self.framesCount=0
        self.micFront = []
        self.module_name = "SoundProcessingModule"
        self.micRear = []

    def startProcessing(self):
        """
        Start processing
        """
        # ask for the front microphone signal sampled at 16kHz
        # if you want the 4 channels call setClientPreferences(self.module_name, 48000, 0, 0)
        self.audio_service.setClientPreferences(self.module_name, 48000, 0, 0)
        self.audio_service.subscribe(self.module_name)

        while self.isProcessingDone == False:
            time.sleep(1)

        self.audio_service.unsubscribe(self.module_name)

    def processRemote(self, nbOfChannels, nbOfSamplesByChannel, timeStamp, inputBuffer):
        """
        Compute RMS for all 4 microphones: front, rear, left, right
        """
        self.framesCount += 1

        if self.framesCount <= self.nbOfFramesToProcess:
            # Umwandeln in float-Liste [-1.0, 1.0]
            audioData = self.convertStr2SignedInt(inputBuffer)

            # Split in einzelne Kanäle
            micFront = audioData[0::4]
            micRear = audioData[1::4]
            micLeft = audioData[2::4]
            micRight = audioData[3::4]

            # RMS pro Kanal
            print("Frame %d:" % self.framesCount)
            print("  Left RMS: %.2f dB" % self.calcRMSLevel(micFront))
            print("  Right  RMS: %.2f dB" % self.calcRMSLevel(micRear))
            print("  Rear  RMS: %.2f dB" % self.calcRMSLevel(micLeft)) #not working
            print("  Front RMS: %.2f dB" % self.calcRMSLevel(micRight)) #not working
        else:
            self.isProcessingDone = True

    def calcRMSLevel(self,data) :
        """
        Calculate RMS level
        """
        rms = 20 * np.log10( np.sqrt( np.sum( np.power(data,2) / len(data)  )))
        return rms

    def convertStr2SignedInt(self, data) :
        """
        This function takes a string containing 16 bits little endian sound
        samples as input and returns a vector containing the 16 bits sound
        samples values converted between -1 and 1.
        """
        signedData=[]
        ind=0
        for i in range (0,len(data)/2) :
            signedData.append(data[ind]+data[ind+1]*256)
            ind=ind+2

        for i in range (0,len(signedData)) :
            if signedData[i]>=32768 :
                signedData[i]=signedData[i]-65536

        for i in range (0,len(signedData)) :
            signedData[i]=signedData[i]/32768.0

        return signedData


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="192.168.1.118",
                        help="Robot IP address. On robot or Local Naoqi: use '127.0.0.1'.")
    parser.add_argument("--port", type=int, default=9559,
                        help="Naoqi port number")

    args = parser.parse_args()
    try:
        # Initialize qi framework.
        connection_url = "tcp://" + args.ip + ":" + str(args.port)
        app = qi.Application(["SoundProcessingModule", "--qi-url=" + connection_url])
    except RuntimeError:
        print ("Can't connect to Naoqi at ip \"" + args.ip + "\" on port " + str(args.port) +".\n"
               "Please check your script arguments. Run with -h option for help.")
        sys.exit(1)
    MySoundProcessingModule = SoundProcessingModule(app)
    app.session.registerService("SoundProcessingModule", MySoundProcessingModule)
    MySoundProcessingModule.startProcessing()