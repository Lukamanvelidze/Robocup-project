import qi
import argparse
import sys
import time
import numpy as np
import wave
import socket
import tempfile
#run on python2.x
class SoundProcessingClient(object):
    def __init__(self, app, server_ip="127.0.0.1", server_port=65432):
        super(SoundProcessingClient, self).__init__()
        app.start()
        self.session = app.session
        self.audio_service = self.session.service("ALAudioDevice")
        self.module_name = "SoundProcessingClient"

        self.audio_rate = 16000
        self.nbOfFramesToProcess = 50
        self.framesCount = 0
        self.collected_samples = []
        self.recognized_words = []

        self.server_ip = server_ip
        self.server_port = server_port

    def startProcessing(self):
        self.audio_service.setClientPreferences(self.module_name, self.audio_rate, 3, 0)
        self.audio_service.subscribe(self.module_name)

        while self.framesCount < self.nbOfFramesToProcess:
            time.sleep(0.1)

        self.audio_service.unsubscribe(self.module_name)

        # Once enough data collected, send audio to server and get transcription
        self.sendAudioToServer()

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

    def convertSamplesToWavBytes(self, samples):
        # Save samples into a wav byte buffer (in-memory)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
            with wave.open(tmpfile.name, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.audio_rate)
                int_samples = (np.array(samples) * 32767).astype(np.int16)
                wf.writeframes(int_samples.tobytes())
            tmpfile.seek(0)
            with open(tmpfile.name, "rb") as f:
                wav_data = f.read()
        return wav_data

    def sendAudioToServer(self):
        wav_bytes = self.convertSamplesToWavBytes(self.collected_samples)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.server_ip, self.server_port))

            # Send length of audio data (4 bytes big-endian)
            length_bytes = len(wav_bytes).to_bytes(4, byteorder='big')
            sock.sendall(length_bytes)
            # Send audio bytes
            sock.sendall(wav_bytes)

            # Receive length of transcription (4 bytes)
            trans_length_bytes = self.recvall(sock, 4)
            trans_length = int.from_bytes(trans_length_bytes, byteorder='big')

            # Receive transcription bytes
            transcription_bytes = self.recvall(sock, trans_length)
            transcription_text = transcription_bytes.decode('utf-8')

            print("[INFO] Transcription received from server:", transcription_text)
            self.recognized_words = transcription_text.strip().split()

        except Exception as e:
            print("[ERROR] Failed to communicate with server:", e)
        finally:
            sock.close()

    def recvall(self, sock, n):
        # Helper function to receive exactly n bytes or fail
        data = b''
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                break
            data += packet
        return data

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="NAOqi IP")
    parser.add_argument("--port", type=int, default=9559, help="NAOqi Port")
    parser.add_argument("--server-ip", type=str, default="127.0.0.1", help="Whisper Server IP")
    parser.add_argument("--server-port", type=int, default=65432, help="Whisper Server Port")
    args = parser.parse_args()

    try:
        connection_url = "tcp://" + args.ip + ":" + str(args.port)
        app = qi.Application(["SoundProcessingClient", "--qi-url=" + connection_url])
    except RuntimeError:
        print("Can't connect to Naoqi.")
        sys.exit(1)

    module = SoundProcessingClient(app, args.server_ip, args.server_port)
    app.session.registerService("SoundProcessingClient", module)
    module.startProcessing()
    print("Recognized words:", module.recognized_words)
