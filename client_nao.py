# -*- coding: utf-8 -*-

import qi
import argparse
import sys
import time
import numpy as np
import wave
import socket
import tempfile
import shutil
import os

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

        self.session.registerService(self.module_name, self)
        print("[INFO] Subscribing to ALAudioDevice...")
        self.audio_service.setClientPreferences(self.module_name, self.audio_rate, 3, 0)
        self.audio_service.subscribe(self.module_name)

    def startProcessing(self):
        print("[INFO] Waiting for audio frames from NAO...")
        while self.framesCount < self.nbOfFramesToProcess:
            time.sleep(0.1)

        print("[INFO] Unsubscribing from ALAudioDevice...")
        self.audio_service.unsubscribe(self.module_name)

        print("[INFO] Sending audio to server...")
        self.sendAudioToServer()

    def processRemote(self, nbOfChannels, nbOfSamplesByChannel, timeStamp, inputBuffer):
        print("[DEBUG] processRemote called")
        print("  Channels:", nbOfChannels)
        print("  Samples per channel:", nbOfSamplesByChannel)
        print("  Input buffer length:", len(inputBuffer))

        if self.framesCount == 1:
            print("  Raw input buffer (first 20):", list(inputBuffer[:20]))
            print("  Input types:", [type(v) for v in inputBuffer[:5]])
            samples = self.convertStr2SignedInt(inputBuffer)
            print("  Decoded samples (first 10):", samples[:10])
        else:
            samples = self.convertStr2SignedInt(inputBuffer)

        if self.framesCount < self.nbOfFramesToProcess:
            self.collected_samples.extend(samples)
            self.framesCount += 1
            print("  Frame count incremented to:", self.framesCount)

    def convertStr2SignedInt(self, data):
        signedData = []
        if len(data) % 2 != 0:
            print("[WARN] Odd-length input buffer")
            return signedData

        for i in range(0, len(data), 2):
            lo = data[i]
            hi = data[i+1]
            sample = (hi << 8) | lo
            if sample >= 32768:
                sample -= 65536
            signedData.append(sample / 32768.0)

        return signedData

    def convertSamplesToWavBytes(self, samples):
        tmpfile = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmpfile_name = tmpfile.name
        tmpfile.close()

        wf = wave.open(tmpfile_name, 'wb')
        try:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.audio_rate)

            arr = np.array(samples)
            max_val = np.max(np.abs(arr))

            if max_val == 0:
                print("[WARN] All-zero audio — silence detected.")
                int_samples = np.zeros_like(arr, dtype=np.int16)
            else:
                print("[DEBUG] Normalizing audio — max sample before scaling:", max_val)
                arr = arr / max_val
                int_samples = (arr * 32767).astype(np.int16)

            wf.writeframes(int_samples.tostring())
        finally:
            wf.close()

        debug_path = os.path.expanduser("~/Desktop/nao_audio_debug.wav")
        shutil.copy(tmpfile_name, debug_path)
        print("[DEBUG] Saved audio to:", debug_path)

        with open(tmpfile_name, "rb") as f:
            wav_data = f.read()

        return wav_data

    def sendAudioToServer(self):
        wav_bytes = self.convertSamplesToWavBytes(self.collected_samples)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.server_ip, self.server_port))

            length_bytes = self.int_to_bytes(len(wav_bytes), 4)
            sock.sendall(length_bytes)
            sock.sendall(wav_bytes)

            trans_length_bytes = self.recvall(sock, 4)
            trans_length = self.bytes_to_int(trans_length_bytes)
            transcription_bytes = self.recvall(sock, trans_length)
            transcription_text = transcription_bytes.decode('utf-8')

            print("[INFO] Transcription received from server:", transcription_text)
            self.recognized_words = transcription_text.strip().split()

        except Exception as e:
            print("[ERROR] Failed to communicate with server:", e)
        finally:
            sock.close()

    def recvall(self, sock, n):
        data = b''
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                break
            data += packet
        return data

    def int_to_bytes(self, value, length):
        return ''.join([chr((value >> (8 * i)) & 0xFF) for i in reversed(range(length))])

    def bytes_to_int(self, bytestr):
        result = 0
        for b in bytestr:
            result = (result << 8) + ord(b)
        return result

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

    print("connected to nao, now try to server")
    module = SoundProcessingClient(app, args.server_ip, args.server_port)
    print("connect to server")
    print("start recording")
    module.startProcessing()
    print("Recognized words:", module.recognized_words)

