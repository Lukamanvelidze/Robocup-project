import argparse
import sys
import qi

from word_recog import *
from move import *
#import audio localization 

from naoqi import ALProxy

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="NAOqi IP")
    parser.add_argument("--port", type=int, default=9559, help="NAOqi Port")
    parser.add_argument("--server-ip", type=str, default="127.0.0.1", help="Whisper Server IP")
    parser.add_argument("--server-port", type=int, default=65432, help="Whisper Server Port")
    args = parser.parse_args()

    tts=ALProxy("ALTextToSpeech",args.ip,args.port)
    moveMod = MoveClient(args.ip, args.port)

    moveMod.posture_init()
    #moveMod.rest()
    #tts.say("Marco")

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
               
    max_attempt = 2
    attempt = 0
    word = "Hi"

    while attempt < max_attempt: # or while goal not reach
        print("Recognized words:", module.recognized_words)
        if word in module.recognized_words:
            tts.say("Ligma")
            attempt = 0

            # use start and end frames (in second) for sound localization 
            # determine the direction -> feed it to move.py function

            # move.py function
            # after n sec of moving, recalibrate with tts->word_recog & sound local
            
            tts.say("Marco")
            module.startProcessing()
           
        elif word not in module.recognized_words:
            attempt +=1
            if attempt<max_attempt:
                print(attempt)
                time.sleep(2)
                #tts.say("Marco")
                module.startProcessing()
            else:
                time.sleep(2)
                moveMod.moveTo(0.2,0,0)
                #tts.say("Im done playing with you!")
                print("bye")
                moveMod.rest()




"""
sound localization 

need the franes from word recog

then the direction of localization will be feed to move.py
"""



"""
At start of programm, tts Marco
-> word_recog
if Polo: 1
else: 2

1:
move.py
after move certrain distant
tts -> word_recog

2: reask in word_recog.py

"""
