import qi
import argparse
import sys
import time
import numpy as np
import whisper
import wave
import tempfile

class SoundProcessingModule(object):
    def __init__(self, app):
        super(SoundProcessingModule, self).__init__()
        app.start()
        self.session = app.session
        self.audio_service = self.session.service("ALAudioDevice")
        self.module_name = "SoundProcessingModule"

        self.audio_rate = 16000
        self.nbOfFramesToProcess = 50
        self.framesCount = 0
        self.collected_samples = []
        self.recognized_words = []

        # Load Whisper model (choose "base", "small", "medium", etc.)
        self.whisper_model = whisper.load_model("base")

    def startProcessing(self):
        self.audio_service.setClientPreferences(self.module_name, self.audio_rate, 3, 0)
        self.audio_service.subscribe(self.module_name)

        while self.framesCount < self.nbOfFramesToProcess:
            time.sleep(0.1)

        self.audio_service.unsubscribe(self.module_name)

        # Once enough data collected, save to wav and transcribe
        self.transcribeAudio()

    def processRemote(self, nbOfChannels, nbOfSamplesByChannel, timeStamp, inputBuffer):
        if self.framesCount < self.nbOfFramesToProcess:
            self.framesCount += 1
            samples = self.convertStr2SignedInt(inputBuffer)
            self.collected_samples.extend(samples)

    def convertStr2SignedInt(self, data):
        signedData = []
        for i in range(0, len(data), 2):
            sample = data[i] + (data[i+1] << 8)
            if sample >= 32768:
                sample -= 65536
            signedData.append(sample / 32768.0)  # Normalized
        return signedData

    def transcribeAudio(self):
        # Save audio to a temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
            with wave.open(tmpfile.name, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.audio_rate)
                # Convert float [-1,1] to int16
                int_samples = (np.array(self.collected_samples) * 32767).astype(np.int16)
                wf.writeframes(int_samples.tobytes())

            print("[INFO] Transcribing audio...")
            result = self.whisper_model.transcribe(tmpfile.name)
            print("Transcription result:", result["text"])
            self.recognized_words = result["text"].strip().split()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9559)
    args = parser.parse_args()

    try:
        connection_url = "tcp://" + args.ip + ":" + str(args.port)
        app = qi.Application(["SoundProcessingModule", "--qi-url=" + connection_url])
    except RuntimeError:
        print("Can't connect to Naoqi.")
        sys.exit(1)

    module = SoundProcessingModule(app)
    app.session.registerService("SoundProcessingModule", module)
    module.startProcessing()
    print("Recognized words:", module.recognized_words)
