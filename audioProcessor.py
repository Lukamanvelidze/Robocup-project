# -*- coding: utf-8 -*-
import qi
import sys
import time
import numpy as np
import wave
import socket
import tempfile
import shutil
import os
import math
from naoqi import ALProxy

class AudioProcessor(object):
    def __init__(self, app, server_ip="127.0.0.1", server_port=65432):
        super(AudioProcessor, self).__init__()
        app.start()
        self.session = app.session
        self.audio_service = self.session.service("ALAudioDevice")
        self.module_name = "AudioProcessor"

        self.audio_rate = 16000
        self.nb_frames_to_collect = 50
        self.frames_count = 0

        self.collected_samples = [[], [], [], []]  # mic 0,1
        self.isProcessingDone = False

        self.server_ip = server_ip
        self.server_port = server_port

        self.session.registerService(self.module_name, self)

        self.mic_positions = {
            "Left":   (-0.0195, 0.0606, 0.0331),
            "Right":  (-0.0195, -0.0606, 0.0331)
        }

    def start(self):
        print("[INFO] Start collecting raw data from mic 0 and 1...")

        self.frames_count = 0
        self.collected_samples = [[], [], [], []]
        self.isProcessingDone = False

        self.audio_service.setClientPreferences(self.module_name, self.audio_rate, 0, 0)
        self.audio_service.subscribe(self.module_name)

        while not self.isProcessingDone:
            time.sleep(0.1)

        self.audio_service.unsubscribe(self.module_name)
        print("[INFO] Finished collecting audio frames.")

        angle = self.estimate_direction_gccphat(
            self.collected_samples[0],
            self.collected_samples[1],
            sample_rate=16000,
            frame_size=1600,
            mic_distance=self.mic_distance(self.mic_positions["Left"], self.mic_positions["Right"])
        )

        print("Final recognized angle (only front assumed):", angle, "degrees")
        
        print("[INFO] Sending audio to server...")
        recognized_words = self.sendAudioToServer() #word recog part

        return recognized_words, angle

    def processRemote(self, nb_channels, nb_samples_per_channel, time_stamp, input_buffer):
        samples = self.convert_bytes_to_floats(input_buffer)

        if self.frames_count < self.nb_frames_to_collect:
            for ch in range(4):
                self.collected_samples[ch].extend(samples[ch::4])
            self.frames_count += 1
            print("[DEBUG] Frame %f received" % self.frames_count)
        else:
            self.isProcessingDone = True

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
        R /= np.abs(R) + 1e-15
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
        c = 343.0
        n_frames = min(len(mic0_samples), len(mic1_samples)) // frame_size

        max_rms = 0
        best_angle = 0

        for i in range(n_frames):
            start = i * frame_size
            end = start + frame_size

            frame0 = mic0_samples[start:end]
            frame1 = mic1_samples[start:end]

            rms = (np.sqrt(np.mean(np.square(frame0))) + np.sqrt(np.mean(np.square(frame1)))) / 2
            if rms < 0.01:
                continue

            max_tau = mic_distance / c + 0.001

            tau = self.gcc_phat(frame0, frame1, fs=sample_rate, max_tau=max_tau)

            ratio = tau * c / mic_distance
            ratio = max(-1.0, min(1.0, ratio))
            angle_rad = math.asin(ratio)
            angle_deg = math.degrees(angle_rad)

            if rms > max_rms:
                max_rms = rms
                best_angle = angle_deg

        return best_angle

    def mic_distance(self, mic1, mic2):
        x1, y1, z1 = mic1
        x2, y2, z2 = mic2
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)

    def sendAudioToServer(self): #word recog part
        wav_bytes = self.convertSamplesToWavBytes()

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.server_ip, self.server_port))

            length_bytes = self.int_to_bytes(len(wav_bytes), 4)
            sock.sendall(length_bytes.encode())
            sock.sendall(wav_bytes)

            trans_length_bytes = self.recvall(sock, 4)
            trans_length = self.bytes_to_int(trans_length_bytes)
            transcription_bytes = self.recvall(sock, trans_length)
            transcription_text = transcription_bytes.decode('utf-8')

            print("[INFO] Transcription received from server:", transcription_text)
            return transcription_text.strip().split()

        except Exception as e:
            print("[ERROR] Failed to communicate with server:", e)
            return []
        finally:
            sock.close()

    def convertSamplesToWavBytes(self):
        samples = self.collected_samples[0]
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
                print("[WARN] Low signal on mic0")
                amplified = arr * 32767 * 5
            else:
                print("[DEBUG] Normalizing mic0")
                amplified = (arr / max_val) * 32767

            int_samples = np.clip(amplified, -32768, 32767).astype(np.int16)
            wf.writeframes(int_samples.tobytes())
        finally:
            wf.close()

        debug_path = os.path.expanduser("~/Desktop/nao_mic0_debug.wav")
        shutil.copy(tmpfile_name, debug_path)
        print("[DEBUG] Saved mic0 to:", debug_path)

        with open(tmpfile_name, "rb") as f:
            return f.read()

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
