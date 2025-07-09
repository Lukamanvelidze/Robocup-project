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
        self.nbOfFramesToProcess = 20
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
            micLeftRaw  = audioData[0::4]
            micRightRaw = audioData[1::4]
            #micLeftRaw = audioData[2::4]    #was Front
            #micRightRaw  = audioData[3::4]  #was Rear
            micLeft = self.simple_bandpass(micLeftRaw, 48000, 100, 6000)
            micRight = self.simple_bandpass(micRightRaw, 48000, 100, 6000)
            #print("frame size: ", len(inputBuffer))

            #print("raw left first10: ", micLeftRaw[:10])
            #print("filtered left first 10: ", micLeft)

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

            
            # RMS linear per channel
            print("  Left  RMS: %.6f " % self.calcLinearRMS(micLeft))
            print("  Right RMS: %.6f " % self.calcLinearRMS(micRight))
            #print("  Front RMS: %.2f dB" % self.calcLinearRMS(micFront)) # somehow not working
            #print("  Rear  RMS: %.2f dB" % self.calcLinearRMS(micRear))  # somehow not working
            

            # testing if there is even raw inout in mic (raw input no rms calc)
            #print("  Left Raw Max: %.4f" % max(np.abs(micLeft)))
            #print("  Right Raw Max: %.4f" % max(np.abs(micRight)))
            #print("  Front Raw Max: %.4f" % max(np.abs(micFront)))
            #print("  Front Raw Max: %.4f" % max(np.abs(micRear)))


            mic_distance_lr = self.distance(self.mic_positions["Left"], self.mic_positions["Right"])
            #print("distance: ", mic_distance_lr)
            #mic_distance_fr = self.distance(self.mic_positions["Front"], self.mic_positions["Rear"])
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

            tau = self.gcc_phat(micLeft, micRight, fs=sample_rate, max_tau=0.000353)
            print("Tau: %.6f s" % tau)
            angle_lr = self.angle_from_tdoa(tau, mic_distance_lr)
            print("angle is: ", angle_lr,"tau ist: ", tau,)

            c = 343.0

            ratio = tau * c / mic_distance_lr
            ratio = max(-1.0, min(1.0, ratio))
            angleRad = np.arcsin(ratio)
            angleDeg = np.degrees(angleRad)
            print("Angle: %.2f" % angleDeg)

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
                    
                    self.move_head("192.168.1.118", 9559, avg_angle)

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

    def move_head(self, ip, port, angle):
        session = qi.Session()
        session.connect("tcp://" + ip + ":" + str(port))
        motion = session.service("ALMotion")
        names = ["HeadYaw" , "HeadPitch"]
        angles = [angle, 0.0]
        fractionMaySpeed = 0.2
        motion.setAngles(names, angles, fractionMaySpeed)
        time.sleep(2)
        motion.setAngles(["HeadYaw","Headpitch"], [0.0 , 0.0],0.2)

    def simple_bandpass(self, data, fs, lowcut, highcut):
        if highcut <= lowcut:
            raise ValueError("highcut must be > lowcut")
        if fs <= 0:
            raise ValueError("Sample rate must be > 0")
        if len(data) < 2:
            return data
        
        fft = np.fft.rfft(data)
        freqs = np.fft.rfftfreq(len(data), 1.0 / fs)
        band_mask = (freqs >= lowcut) & (freqs <= highcut)
        fft[~band_mask] = 0

        filtered = np.fft.irfft(fft)
        filtered = np.nan_to_num(filtered)
        return filtered.astype(np.float32)

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

    def gcc_phat(self, sig1, sig2, fs, max_tau=None, interp=16):
        sig1 = np.array(sig1)
        sig2 = np.array(sig2)
        n = len(sig1) + len(sig2)
        nfft = 1 << (n-1).bit_length()

        SIG1 = np.fft.fft(sig1, n=nfft)
        SIG2 = np.fft.fft(sig2, n=nfft)
        R = SIG1 * np.conj(SIG2)
        R /= np.abs(R) + 1e-15  # PHAT weighting
        cc = np.fft.irfft(R).real
        max_shift = nfft // 2
        cc = np.concatenate((cc[-max_shift:], cc[:max_shift+1]))

        interp_len = len(cc)*interp
        cc_interp = np.interp(
            np.linspace(0, len(cc-1), interp_len), np.arange(len(cc)),cc
        )

        shift = np.argmax(cc_interp) - interp_len // 2
        tau = float(shift) / (interp * fs)

        if max_tau and abs(tau) > max_tau:
            return 0.0
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