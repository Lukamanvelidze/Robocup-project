# -*- coding: utf-8 -*-
import qi
import sys
import time
import argparse
import numpy as np
import math
from naoqi import ALProxy

class RawMicDataCollector(object):
    def __init__(self, app):
        super(RawMicDataCollector, self).__init__()
        app.start()
        self.session = app.session
        self.audio_service = self.session.service("ALAudioDevice")
        self.module_name = "RawMicDataCollector"
        self.isProcessingDone = False
        self.audio_rate = 16000
        self.nb_frames_to_collect = 50
        self.frames_count = 0

        # Nur für die zwei Mikrofone 0 und 1
        self.collected_samples = [[], []]

        self.session.registerService(self.module_name, self)

        self.mic_positions = {
            "Left":   (-0.0195, 0.0606, 0.0331),
            "Right":  (-0.0195, -0.0606, 0.0331)
        }

    def start(self):
        print("[INFO] Start collecting raw data from mic 0 and 1...")

        self.frames_count = 0
        self.collected_samples = [[], []]

        # Alle 4 Kanäle abgreifen, aber wir nehmen nur 0 und 1
        self.audio_service.setClientPreferences(self.module_name, self.audio_rate, 0, 0)
        self.audio_service.subscribe(self.module_name)

        while self.isProcessingDone == False:
            time.sleep(0.1)

        self.audio_service.unsubscribe(self.module_name)
        print("[INFO] Finished collecting audio frames.")

        # Nach dem Sammeln aller Frames Winkel berechnen
        angle = self.estimate_direction_gccphat(
            self.collected_samples[0],
            self.collected_samples[1],
            sample_rate=16000,
            frame_size=1600,
            mic_distance=self.mic_distance(self.mic_positions["Left"], self.mic_positions["Right"])
        )

        print("Final recognized angle (only front assumed): " , angle , " degrees")
        self.move_head("192.168.1.118", 9559, angle)
        time.sleep(5)
        self.walk(self, "192.168.1.118", 9559, angle)

    def processRemote(self, nb_channels, nb_samples_per_channel, time_stamp, input_buffer):
        samples = self.convert_bytes_to_floats(input_buffer)
        if self.frames_count < self.nb_frames_to_collect:
            # Nur Mikrofon 0 und 1 rausfiltern
            mic0_samples = samples[0::4]
            mic1_samples = samples[1::4]
            self.collected_samples[0].extend(mic0_samples)
            self.collected_samples[1].extend(mic1_samples)

            self.frames_count += 1
            print("[DEBUG] Frame %f received" % self.frames_count)
        else:
            self.isProcessingDone = True

    def sonar(robotIP):
        PORT = 9559

        # Create proxy to ALMemory
        memoryProxy = ALProxy("ALMemory", robotIP, PORT)
        # Create proxy to ALSonar
        sonarProxy = ALProxy("ALSonar", robotIP, PORT)


        # Subscribe to sonars, this will launch sonars (at hardware level)
        # and start data acquisition.
        sonarProxy.subscribe("myApplication")

        SD = [0.0,0.0]
        # Now you can retrieve sonar data from ALMemory.
        # Get sonar left first echo (distance in meters to the first obstacle).
        SL = memoryProxy.getData("Device/SubDeviceList/US/Left/Sensor/Value")

        # Same thing for right.
        SR = memoryProxy.getData("Device/SubDeviceList/US/Right/Sensor/Value")

        # Unsubscribe from sonars, this will stop sonars (at hardware level)
        sonarProxy.unsubscribe("myApplication")
        return SD

    # Please read Sonar ALMemory keys section
    # if you want to know the other values you can get.

    def get_gyro(robotIP):
        PORT = 9559
        Gyr = [0.0,0.0]
        # Create proxy to ALMemory
        try:
            memoryProxy = ALProxy("ALMemory", robotIP, PORT)
        except:
            print ("Could not create proxy to ALMemory")

        # Get the Gyrometers Values
        GyrX = memoryProxy.getData("Device/SubDeviceList/InertialSensor/GyrX/Sensor/Value")
        GyrY = memoryProxy.getData("Device/SubDeviceList/InertialSensor/GyrY/Sensor/Value")
        print ("Gyrometers value X: %.3f, Y: %.3f" % (GyrX, GyrY))
        Gyr[0] = GyrX
        Gyr[1] = GyrY
        return GyrX

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

    def move_head(self, ip, port, angle):
        session = qi.Session()
        session.connect("tcp://" + ip + ":" + str(port))
        motion = session.service("ALMotion")
        names = ["HeadYaw" , "HeadPitch"]
        angles = [angle, 0.0]
        fractionMaySpeed = 0.2
        motion.setAngles(names, angles, fractionMaySpeed)
        time.sleep(2)
        motion.setAngles(["HeadYaw","HeadPitch"], [0.0 , 0.0],0.2)

    def convert_bytes_to_floats(self, data):
        int16_data = np.frombuffer(data, dtype=np.int16)
        float_data = int16_data.astype(np.float32) / 32768.0
        return float_data.tolist()

    def gcc_phat(self, sig1, sig2, fs, max_tau=None, interp=16):
        n = len(sig1) + len(sig2)
        nfft = 1 << (n-1).bit_length()

        SIG1 = np.fft.fft(sig1, n=nfft)
        SIG2 = np.fft.fft(sig2, n=nfft)
        R = SIG1 * np.conj(SIG2)
        R /= np.abs(R) + 1e-15  # PHAT weighting
        cc = np.fft.irfft(R)
        max_shift = int(min(max_tau * fs if max_tau else nfft // 2, nfft // 2))
        cc = np.concatenate((cc[-max_shift:], cc[:max_shift+1]))

        interp_len = len(cc) * interp
        cc_interp = np.interp(np.linspace(0, len(cc)-1, interp_len), np.arange(len(cc)), cc)

        shift = np.argmax(cc_interp) - interp_len // 2
        tau = shift / float(interp * fs)

        if max_tau and abs(tau) > max_tau:
            return 0.0
        return tau

    def estimate_direction_gccphat(self, mic0_samples, mic1_samples, sample_rate=16000, frame_size=1600, mic_distance=0.12):
        c = 343.0  # Schallgeschwindigkeit m/s
        n_frames = min(len(mic0_samples), len(mic1_samples)) // frame_size

        max_rms = 0
        best_angle = 0

        for i in range(n_frames):
            start = i * frame_size
            end = start + frame_size

            frame0 = mic0_samples[start:end]
            frame1 = mic1_samples[start:end]

            # RMS Mittelwert aus beiden Mics (Stärke des Signals)
            rms = (np.sqrt(np.mean(np.square(frame0))) + np.sqrt(np.mean(np.square(frame1)))) / 2
            if rms < 0.01:  # zu leise -> ignorieren
                continue

            # Maximal erlaubte Verzögerung (max tau) = Abstand / Schallgeschwindigkeit + kleine Reserve
            max_tau = mic_distance / c + 0.001

            tau = self.gcc_phat(frame0, frame1, fs=sample_rate, max_tau=max_tau)
            
            # Winkel berechnen
            ratio = tau * c / mic_distance
            ratio = max(-1.0, min(1.0, ratio))  # absichern wegen asin-Domain
            angle_rad = math.asin(ratio)
            angle_deg = math.degrees(angle_rad)

            # Nur wenn Signal stark ist, nehme Winkel mit maximaler Lautstärke
            if rms > max_rms:
                max_rms = rms
                best_angle = angle_deg

        return best_angle

    def mic_distance(self, mic1, mic2):
        x1, y1, z1 = mic1
        x2, y2, z2 = mic2
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="NAOqi IP")
    parser.add_argument("--port", type=int, default=9559, help="NAOqi Port")
    args = parser.parse_args()

    try:
        connection_url = f"tcp://{args.ip}:{args.port}"
        app = qi.Application(["RawMicDataCollector", f"--qi-url={connection_url}"])
    except RuntimeError:
        print("Can't connect to Naoqi at ip ", args.ip, " on port ", args.port,".")
        sys.exit(1)

    collector = RawMicDataCollector(app)
    app.session.registerService("RawMicDataCollector", collector)
    collector.start()

    for i, samples in enumerate(collector.collected_samples):
        print("Mic " ,i, " collected " ,len(samples), " samples")