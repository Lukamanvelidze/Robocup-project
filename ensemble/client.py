import argparse
import sys
import qi
import time
from audio_processor import AudioProcessor  # Merged class
from move import MoveClient
from naoqi import ALProxy

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="NAOqi IP")
    parser.add_argument("--port", type=int, default=9559, help="NAOqi Port")
    parser.add_argument("--server-ip", type=str, default="127.0.0.1", help="Whisper Server IP")
    parser.add_argument("--server-port", type=int, default=65432, help="Whisper Server Port")
    args = parser.parse_args()

    tts = ALProxy("ALTextToSpeech", args.ip, args.port)

    try:
        connection_url = "tcp://" + args.ip + ":" + str(args.port)
        app = qi.Application(["AudioProcessor", "--qi-url=" + connection_url])
    except RuntimeError:
        print("Can't connect to Naoqi.")
        sys.exit(1)

    processor = AudioProcessor(app, args.server_ip, args.server_port)
    moveMod = MoveClient(args.ip, args.port)

    max_attempt = 2
    attempt = 0
    target_word = "hi"

    while attempt < max_attempt:
        print("[INFO] Starting audio processing cycle...")
        recognized_words, angle = processor.start()
        normalized_words = [w.strip().lower().strip(".,!?\"") for w in recognized_words]

        print("Recognized words:", recognized_words)
        if target_word in normalized_words:
            tts.say("Ligma")
            attempt = 0

            angle = max(-90, min(90, angle))
            theta = angle * 3.14159 / 180.0  # degrees to radians
            moveMod.moveTo(0.2, 0, theta)

            tts.say("Marco")
        else:
            attempt += 1
            if attempt < max_attempt:
                print(f"[INFO] Attempt {attempt}, retrying after pause...")
                time.sleep(2)
            else:
                print("Max attempts reached")
                time.sleep(2)
                moveMod.rest()
