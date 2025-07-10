#!/usr/bin/env python
# -*- encoding: UTF-8 -*-

import qi
import sys
import time
import numpy as np
import math

class SimpleBeamformer(object):
    def __init__(self, app):
        super(SimpleBeamformer, self).__init__()
        app.start()
        self.session = app.session
        self.audio_service = self.session.service("ALAudioDevice")

        self.module_name = "SimpleBeamformer"
        self.is_processing_done = False
        self.frames_to_process = 50
        self.frames_processed = 0

        # Mic positions in meters (approximate NAO mic spacing)
        self.mic_positions = {
            "Left": (-0.0195, 0.0606, 0.0331),
            "Right": (-0.0195, -0.0606, 0.0331)
        }
        self.mic_distance = self.calc_distance(self.mic_positions["Left"], self.mic_positions["Right"])
        self.sample_rate = 48000  # Must match setClientPreferences

    def start(self):
        # Subscribe to audio input: client preferences: clientName, sampleRate, channels, precision
        # Channels = 0 for 1 channel, 1 for all 4 channels
        self.audio_service.setClientPreferences(self.module_name, self.sample_rate, 1, 0)
        self.audio_service.subscribe(self.module_name)
        print "Subscribed to audio stream, processing..."

        while not self.is_processing_done:
            time.sleep(0.1)

        self.audio_service.unsubscribe(self.module_name)
        print "Unsubscribed from audio stream."

    def processRemote(self, nbChannels, nbSamplesPerChannel, timestamp, inputBuffer):
        # Called by NAOqi when new audio arrives
        self.frames_processed += 1
        if self.frames_processed > self.frames_to_process:
            self.is_processing_done = True
            return

        audio_data = self.convert_buffer(inputBuffer)

        # Extract left and right channels (assuming 4 channels interleaved: L, R, ..., ...)
        mic_left = audio_data[0::4]
        mic_right = audio_data[1::4]

        angle = self.beamforming_angle(mic_left, mic_right)
        print "Frame {}: Estimated sound angle: {:.1f} degrees".format(self.frames_processed, angle)

    def convert_buffer(self, data):
        # Convert raw buffer to float32 normalized between -1 and 1
        data_int16 = np.frombuffer(data, dtype=np.int16)
        return data_int16.astype(np.float32) / 32768.0

    def calc_distance(self, p1, p2):
        return math.sqrt(sum((c1 - c2) ** 2 for c1, c2 in zip(p1, p2)))

    def beamforming_angle(self, sig1, sig2):
        # Delay and sum beamforming - find time delay between signals by cross-correlation

        speed_of_sound = 343.0  # m/s

        # Cross-correlate signals
        corr = np.correlate(sig1, sig2, "full")
        max_corr_index = np.argmax(corr)

        # Calculate lag in samples
        lag = max_corr_index - (len(sig1) - 1)

        # Convert lag to time delay in seconds
        time_delay = float(lag) / self.sample_rate

        # Calculate angle from time delay
        # max possible delay = mic_distance / speed_of_sound
        max_delay = self.mic_distance / speed_of_sound
        if abs(time_delay) > max_delay:
            # Invalid delay, clamp
            time_delay = np.sign(time_delay) * max_delay

        # Compute angle in radians: asin(time_delay * speed_of_sound / mic_distance)
        try:
            angle_rad = math.asin(time_delay * speed_of_sound / self.mic_distance)
            angle_deg = math.degrees(angle_rad)
        except ValueError:
            # Numerical issues from asin domain error
            angle_deg = 0.0

        return angle_deg


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="127.0.0.1",
                        help="Robot IP address. Use 127.0.0.1 if running on the robot.")
    parser.add_argument("--port", type=int, default=9559, help="Naoqi port number.")
    args = parser.parse_args()

    try:
        connection_url = "tcp://{}:{}".format(args.ip, args.port)
        app = qi.Application(["SimpleBeamformer", "--qi-url=" + connection_url])
    except RuntimeError:
        print "Can't connect to Naoqi at ip {} on port {}.".format(args.ip, args.port)
        sys.exit(1)

    beamformer = SimpleBeamformer(app)
    app.session.registerService("SimpleBeamformer", beamformer)
    beamformer.start()
