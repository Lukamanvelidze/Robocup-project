# -*- encoding: UTF-8 -*-
import qi
import argparse
import sys
import time
import numpy as np
import math


class SoundProcessingModule(object):
    def __init__(self, app):
        super(SoundProcessingModule, self).__init__()
        app.start()
        session = app.session

        self.audio_service = session.service("ALAudioDevice")
        self.isProcessingDone = False
        self.nbOfFramesToProcess = 50
        self.framesCount = 0
        self.module_name = "SoundProcessingModule"
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
        self.audio_service.setClientPreferences(self.module_name, 48000, 0, 0)
        self.audio_service.subscribe(self.module_name)
        self.audio_service.getOutputVolume()

        while not self.isProcessingDone:
            time.sleep(1)

        self.audio_service.unsubscribe(self.module_name)

    def processRemote(self, nbOfChannels, nbOfSamplesByChannel, timeStamp, inputBuffer):
        self.framesCount += 1
        if self.framesCount > self.nbOfFramesToProcess:
            self.finishProcessing()
            return

        audioData = self.convertStr2SignedInt(inputBuffer)
        micLeft = audioData[0::4]
        micRight = audioData[1::4]

        self.invalid = False
        mic_distance_lr = self.distance(self.mic_positions["Left"], self.mic_positions["Right"])
        sample_rate = 48000

        tau = self.gcc_phat(micLeft, micRight, fs=sample_rate)
        angle_lr = self.angle_from_tdoa(tau, mic_distance_lr)

        rms_left = self.calcLinearRMS(micLeft)
        rms_right = self.calcLinearRMS(micRight)
        loudness = (rms_left + rms_right) / 2.0

        if not self.invalid:
            self.angle_values.append((angle_lr, loudness))

    def finishProcessing(self):
        self.isProcessingDone = True
        if not self.angle_values:
            print("No valid Frames for Calculation")
            return

        sum_weighted = sum(angle * weight for angle, weight in self.angle_values)
        total_weight = sum(weight for _, weight in self.angle_values)

        if total_weight > 0:
            avg_angle = sum_weighted / total_weight
            print("\nRMS-weighted average for %d Frames: %.1f degrees" %
                  (len(self.angle_values), avg_angle))

            if avg_angle > 10:
                direction = "from right"
            elif avg_angle < -10:
                direction = "from left"
            else:
                direction = "front"
            print("Approximately: %s" % direction)
        else:
            print("No signals with good values (Weight = 0).")

    def convertStr2SignedInt(self, data):
        data_int16 = np.frombuffer(data, dtype=np.int16)
        return data_int16.astype(np.float32) / 32768.0

    def calcRMSLevel(self, data):
        rms = np.sqrt(np.mean(np.square(data)))
        if rms < np.finfo(np.float32).eps:
            return -100.0
        return 20 * np.log10(rms)

    def calcLinearRMS(self, data):
        return np.sqrt(np.mean(np.square(data)))

    def gcc_phat(self, sig1, sig2, fs, max_tau=None, interp=16):
        n = len(sig1) + len(sig2)
        SIG1 = np.fft.rfft(sig1, n=n)
        SIG2 = np.fft.rfft(sig2, n=n)
        R = SIG1 * np.conj(SIG2)
        R /= np.abs(R) + np.finfo(np.float32).eps  # Use epsilon for stability
        cc = np.fft.irfft(R, n=(interp * n))
        max_shift = int(interp * n / 2)

        if max_tau:
            max_shift = min(int(interp * fs * max_tau), max_shift)

        cc = np.concatenate((cc[-max_shift:], cc[:max_shift+1]))
        shift = np.argmax(np.abs(cc)) - max_shift
        tau = shift / float(interp * fs)
        return tau

    def angle_from_tdoa(self, tau, mic_distance):
        try:
            angle = math.degrees(math.asin(tau * 343.0 / mic_distance))
        except ValueError:
            angle = 0.0
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
        connection_url = "tcp://" + args.ip + ":" + str(args.port)
        app = qi.Application(["SoundProcessingModule", "--qi-url=" + connection_url])
    except RuntimeError:
        print("Can't connect to Naoqi at ip \"%s\" on port %d.\nRun with -h for help." % (args.ip, args.port))
        sys.exit(1)

    module = SoundProcessingModule(app)
    module.startProcessing()
