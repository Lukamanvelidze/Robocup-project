import qi
import numpy as np
import wave
import socket
import tempfile
import shutil
import os

import sys
import time


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
        self.collected_samples = [[], [], [], []]  # One list per mic

        self.server_ip = server_ip
        self.server_port = server_port

        self.session.registerService(self.module_name, self)
        print("[INFO] Subscribing to ALAudioDevice...")
        #self.audio_service.setClientPreferences(self.module_name, self.audio_rate, 0, 0)  # Use 0 channels = all mics
        #self.audio_service.subscribe(self.module_name)

    def startProcessing(self):
        
        self.framesCount = 0
        self.collected_samples = [[], [], [], []]

        self.audio_service.setClientPreferences(self.module_name, self.audio_rate, 0, 0)

        self.audio_service.subscribe(self.module_name)
        print("[INFO] Waiting for audio frames from NAO...")
        while self.framesCount < self.nbOfFramesToProcess:
            time.sleep(0.1)

        print("[INFO] Unsubscribing from ALAudioDevice...")
        self.audio_service.unsubscribe(self.module_name)

        print("[INFO] Sending audio to server...")
        self.sendAudioToServer()

    def processRemote(self, nbOfChannels, nbOfSamplesByChannel, timeStamp, inputBuffer):
        #print("[DEBUG] processRemote called")
        #print("  Channels:", nbOfChannels)
        #print("  Samples per channel:", nbOfSamplesByChannel)
        #print("  Input buffer length:", len(inputBuffer))

        samples = self.convertStr2SignedInt(inputBuffer)

        if self.framesCount == 0:
            #print("  Raw buffer first 20:", list(inputBuffer[:20]))
            #print("  Decoded samples (first 16):", samples[:16])

        if self.framesCount < self.nbOfFramesToProcess:
            for ch in range(4):
                channel_samples = samples[ch::4]
                self.collected_samples[ch].extend(channel_samples)

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

    def convertSamplesToWavBytes(self):
        wav_data_per_channel = []

        for mic_index in range(4):
            samples = self.collected_samples[mic_index]
            arr = np.array(samples)
            max_val = np.max(np.abs(arr)) if len(arr) else 0

            tmpfile = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmpfile_name = tmpfile.name
            tmpfile.close()

            wf = wave.open(tmpfile_name, 'wb')
            try:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.audio_rate)

                if max_val < 0.01:
                    print("[WARN] Low signal on mic", mic_index)
                    amplified = arr * 32767 * 5
                else:
                    print("[DEBUG] Normalizing mic", mic_index)
                    amplified = (arr / max_val) * 32767

                int_samples = np.clip(amplified, -32768, 32767).astype(np.int16)
                wf.writeframes(int_samples.tostring())
            finally:
                wf.close()

            debug_path = os.path.expanduser("~/Desktop/nao_mic{}_debug.wav".format(mic_index))
            shutil.copy(tmpfile_name, debug_path)
            print("[DEBUG] Saved mic{} to:".format(mic_index), debug_path)

            with open(tmpfile_name, "rb") as f:
                wav_data_per_channel.append(f.read())

        return wav_data_per_channel[0]  # send only mic0 audio to Whisper

    def sendAudioToServer(self):
        wav_bytes = self.convertSamplesToWavBytes()

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