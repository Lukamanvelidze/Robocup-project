import qi
import argparse
import sys
import time
import numpy as np
import wave
import os
import tempfile
import platform


class SoundProcessingClient(object):
    def __init__(self, app):
        app.start()
        self.session = app.session
        self.audio_service = self.session.service("ALAudioDevice")
        self.module_name = "SoundProcessingClient"

        self.audio_rate = 16000
        self.framesCount = 0
        self.nbOfFramesToProcess = 200  # ~1.25s of audio

        self.collected_samples = []

        #  Register the processRemote callback with the session
       

    def startProcessing(self):
        #  1 channel, 16-bit, little endian, 16000 Hz
        self.audio_service.setClientPreferences(self.module_name, self.audio_rate, 1, 0)
        self.audio_service.subscribe(self.module_name)

        print("Subscribed. Waiting to collect audio...")

        while self.framesCount < self.nbOfFramesToProcess:
            print("lol")
            time.sleep(0.1)

        self.audio_service.unsubscribe(self.module_name)
        print("Unsubscribed. Saving audio...")

        wav_file = self.write_wav_file(self.collected_samples)
        self.play_wav_file(wav_file)

    def processRemote(self, nbOfChannels, nbOfSamplesByChannel, timeStamp, inputBuffer):
        print("processRemote called: frame")

        if self.framesCount < self.nbOfFramesToProcess:
            self.framesCount += 1

            # Parse input buffer
            samples = np.frombuffer(inputBuffer, dtype=np.int16)

            # Use channel 0 if multichannel
            if nbOfChannels > 1:
                samples = samples[::nbOfChannels]

            self.collected_samples.append(samples.tobytes())

    def write_wav_file(self, raw_buffers):
        tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        with wave.open(tmpfile.name, 'wb') as wf:
            wf.setnchannels(1)         # Mono
            wf.setsampwidth(2)         # 16-bit
            wf.setframerate(self.audio_rate)
            wf.writeframes(b''.join(raw_buffers))
        return tmpfile.name

    def play_wav_file(self, wav_path):
        system = platform.system()
        if system == "Darwin":  # macOS
            os.system("afplay '{}'".format(wav_path))
        elif system == "Linux":
            os.system("aplay '{}'".format(wav_path))
        elif system == "Windows":
            os.system("start /min wmplayer '{}'".format(wav_path.replace("/", "\\")))
        else:
            print("Unsupported OS: cannot auto-play audio")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="192.168.1.118", help="NAOqi IP")
    parser.add_argument("--port", type=int, default=9559, help="NAOqi Port")
    args = parser.parse_args()

    try:
        connection_url = "tcp://" + args.ip + ":" + str(args.port)
        app = qi.Application(["SoundProcessingClient", "--qi-url=" + connection_url])
    except RuntimeError:
        print("Can't connect to Naoqi.")
        sys.exit(1)

    # Register the service before running
    module = SoundProcessingClient(app)
    module.startProcessing()