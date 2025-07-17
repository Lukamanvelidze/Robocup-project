import socket
import tempfile
import wave
import numpy as np
import whisper
import json
#run on python3.7
HOST = '127.0.0.1'
PORT = 65432

model = whisper.load_model("base")


def handle_client(conn):
    # Receive length of incoming audio
    length_bytes = conn.recv(4)
    length = int.from_bytes(length_bytes, byteorder='big')

    data = b''
    while len(data) < length:
        packet = conn.recv(4096)
        if not packet:
            break
        data += packet

    # Save to temp wav
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmpfile:
        with wave.open(tmpfile.name, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(data)

        result = model.transcribe(tmpfile.name,language="en")

        #segment_data = []
        for segment in result["segments"]:
            start = segment["start"]
            end = segment["end"]
            text=segment["text"]
            print(f"[{start:.2f}-{end:.2f}: {text}")
            """
            segment_data.append({
                "start":start,
                "end":end,
                "text":text
            })
            """

    # Send transcription back
    #transcription = json.dumps(segment_data).encode('utf-8')
    transcription = result["text"].encode('utf-8')
    trans_len = len(transcription)
    conn.send(trans_len.to_bytes(4, byteorder='big'))
    conn.send(transcription)


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    print("Whisper server running...")
    while True:
        print("will accept")
        conn, addr = s.accept()
        print("hass accepted")
        with conn:
            print(f"Connected by {addr}")
            handle_client(conn)

