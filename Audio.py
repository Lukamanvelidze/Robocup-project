#! /usr/bin/env python
# -*- encoding: UTF-8 -*-

"""Example: Get Signal from Front Microphone & Calculate its rms Power"""

import qi
import argparse
import sys
import time
import numpy as np
import math


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
        self.nbOfFramesToProcess = 50
        self.framesCount=0
        self.micFront = []
        self.module_name = "SoundProcessingModule"
        self.micRear = []
        self.micRight = []
        self.micLeft = []
        self.invalid = False
        self.startTime = time.time()
        self.angle_values = []

        self.mic_positions = {
            "Front":  (0.041, 0.0, 0.0915),
            "Rear":   (-0.0577, 0.0, 0.0693),
            "Left":   (-0.0195, 0.0606, 0.0331),
            "Right":  (-0.0195, -0.0606, 0.0331)
        }

    def startProcessing(self):
        """
        Start processing
        """
        # ask for the front microphone signal sampled at 16kHz
        # if you want the 4 channels call setClientPreferences(self.module_name, 48000, 0, 0)
        self.audio_service.setClientPreferences(self.module_name, 48000, 0, 0)

        # chatgbt says 1 is all 4 and 0 is just 1 channel
        #self.audio_service.setClientPreferences(self.module_name, 48000, 1, 0)


        self.audio_service.subscribe(self.module_name)

        # test if all 4 mic are even activated (should look like this ['FrontLeft', 'FrontRight', 'RearLeft', 'RearRight'] )
        #self.audio_service.getMicrophones()         
        self.audio_service.getOutputVolume()


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
            micLeft  = audioData[0::4]
            micRight = audioData[1::4]
            #micFront = audioData[2::4]
            #micRear  = audioData[3::4]

            self.invalid = False

            # using timestamp to check the audio latency (time between him hearing something to calc and output of that rms)
            captureTime = (timeStamp[0] + timeStamp[1]) / 1e9
            currentTime = time.time() / 1e9
            latency = currentTime - captureTime
            #print("Audio-latency: %.3f seconds" % latency)

            # to see how many channels are used
            #print("Channels:", nbOfChannels)
            #print("Samples per channel:", nbOfSamplesByChannel)
            #print("InputBuffer lenght:", len(inputBuffer))

            # RMS in db per channel
            #print("  Left  RMS: %.2f dB" % self.calcRMSLevel(micLeft))
            #print("  Right RMS: %.2f dB" % self.calcRMSLevel(micRight))
            #print("  Front RMS: %.2f dB" % self.calcRMSLevel(micFront)) # somehow not working
            #print("  Rear  RMS: %.2f dB" % self.calcRMSLevel(micRear))  # somehow not working

            """
            # RMS linear per channel
            print("  Left  RMS: %.2f dB" % self.calcLinearRMS(micLeft))
            print("  Right RMS: %.2f dB" % self.calcLinearRMS(micRight))
            print("  Front RMS: %.2f dB" % self.calcLinearRMS(micFront)) # somehow not working
            print("  Rear  RMS: %.2f dB" % self.calcLinearRMS(micRear))  # somehow not working
            """

            # testing if there is even raw inout in mic (raw input no rms calc)
            #print("  Left Raw Max: %.4f" % max(np.abs(micLeft)))
            #print("  Right Raw Max: %.4f" % max(np.abs(micRight)))
            #print("  Front Raw Max: %.4f" % max(np.abs(micFront)))
            #print("  Front Raw Max: %.4f" % max(np.abs(micRear)))


            mic_distance_lr = self.distance(self.mic_positions["Left"], self.mic_positions["Right"])
            mic_distance_fr = self.distance(self.mic_positions["Front"], self.mic_positions["Rear"])
            sample_rate = 48000  # entspricht deiner setClientPreferences()

            #angle_lr = self.estimate_direction(micLeft, micRight, mic_distance_lr, sample_rate)
            #angle_fr = self.estimate_direction(micFront, micRear, mic_distance_fr, sample_rate)

            #print("direction (Left-Right): %.1f degrees" % angle_lr)
            #print("direction (Front-Rear): %.1f degrees" % angle_fr)

            #azimut_rad = math.radians(angle_lr)
            #elevation_rad = math.radians(angle_fr)

            #x = math.cos(elevation_rad) * math.cos(azimut_rad)
            #y = math.cos(elevation_rad) * math.sin(azimut_rad)  

            # Gesamtwinkel (z. B. für Richtung in 2D)
            #gesamtwinkel = math.degrees(math.atan2(y, x))

            """if ( degree < 0):
                gesamtwinkel = degree + 360
            """

            #print("sound source is coming at a %.2f degree angle from NAO (0/360 is right, 180 is left, 90 is front, 270 is rear)" % gesamtwinkel) 

            frameTime = time.time() - self.startTime

            tau = self.gcc_phat(micLeft, micRight, fs=sample_rate)
            angle_lr = self.angle_from_tdoa(tau, mic_distance_lr)

            rms_left = self.calcLinearRMS(micLeft)
            rms_right = self.calcLinearRMS(micRight)
            loudness = (rms_left + rms_right) / 2.0  # lineare Lautstärke, kein dB

            if not self.invalid:
                self.angle_values.append((angle_lr, loudness))

            """
            if (self.invalid == False):   
                print("Frame : %.0f________________________________" % self.framesCount)
            if (self.invalid == False):
                print("  Left  RMS: %.2f dB" % self.calcRMSLevel(micLeft))
                print("  Right RMS: %.2f dB" % self.calcRMSLevel(micRight))
            if (self.invalid == False):
                print("  Sound source angle: %f" % angle_lr)
                print("  Timestamp: %.2f seconds" % frameTime)
            """

        else:
            self.isProcessingDone = True

            if self.angle_values:
                sum_weighted = sum(angle * weight for angle, weight in self.angle_values)
                total_weight = sum(weight for _, weight in self.angle_values)

                if total_weight > 0:
                    avg_angle = sum_weighted / total_weight
                    print("\n rms-weighted average for %d Frames: %.1f degrees" %
                        (len(self.angle_values), avg_angle))

                    # Optionale Richtungserkennung
                    if avg_angle > 10:
                        richtung = "from right"
                    elif avg_angle < -10:
                        richtung = "from left"
                    else:
                        richtung = "front"
                    print(" Approximately: %s" % richtung)
                else:
                    print(" No signals with good values (Weight. = 0).")
            else:
                print(" No valid Frames for Calculation")

    def calcRMSLevel(self, data):
        rms = np.sqrt(np.mean(np.square(data)))
        if rms < 1e-10:    # just in case that its so quiet that the calc log(0) is not possible
            return -100.0  # very quiet
        return 20 * np.log10(rms)
    
    # calc linear rms (not in db)
    def calcLinearRMS(self, data):
        return np.sqrt(np.mean(np.square(data)))

    def convertStr2SignedInt(self, data):
        data_int16 = np.frombuffer(data, dtype=np.int16)
        return data_int16.astype(np.float32) / 32768.0

    
    def estimate_direction(self, mic1, mic2, mic_distance, sample_rate):
        corr = np.correlate(mic1, mic2, mode='full')
        lag = np.argmax(corr) - (len(mic1) - 1)
        time_diff = lag / float(sample_rate)
        try:
            angle = math.degrees(math.asin((time_diff * 343.0) / mic_distance))
        except ValueError:
            angle = 0.0  # asin schluckt manchmal NaN bei zu großen Werten
        return angle
    

    def gcc_phat(self, sig1, sig2, fs, max_tau=None, interp=16):
        n = len(sig1) + len(sig2)
        SIG1 = np.fft.rfft(sig1, n=n)
        SIG2 = np.fft.rfft(sig2, n=n)
        R = SIG1 * np.conj(SIG2)
        R /= np.abs(R) + 1e-15  # PHAT weighting
        cc = np.fft.irfft(R, n=(interp * n))
        max_shift = int(interp * n / 2)
        if max_tau:
            max_shift = np.minimum(int(interp * fs * max_tau), max_shift)
        cc = np.concatenate((cc[-max_shift:], cc[:max_shift+1]))
        shift = np.argmax(np.abs(cc)) - max_shift
        tau = shift / float(interp * fs)
        return tau
    
    def angle_from_tdoa(self, tau, mic_distance):
        try:
            angle = math.degrees(math.asin(tau * 343.0 / mic_distance))
        except ValueError:
            angle = 0.0  # falls asin überläuft
            #print("  Invalid Angle")
            self.invalid = True
        return angle

    def distance(self, mic1, mic2):
        x1, y1, z1 = mic1
        x2, y2, z2 = mic2
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)

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