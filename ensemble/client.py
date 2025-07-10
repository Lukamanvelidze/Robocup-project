import argparse
import sys
import qi

from word_recog import *
from move import *
from SoundLocalization import * # including walking already 

from naoqi import ALProxy

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="NAOqi IP")
    parser.add_argument("--port", type=int, default=9559, help="NAOqi Port")
    parser.add_argument("--server-ip", type=str, default="127.0.0.1", help="Whisper Server IP")
    parser.add_argument("--server-port", type=int, default=65432, help="Whisper Server Port")
    args = parser.parse_args()

    tts=ALProxy("ALTextToSpeech",args.ip,args.port)i

    
    

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
    
    #connect to sound localization
    try:
        connection_url = f"tcp://{args.ip}:{args.port}"
        app = qi.Application(["RawMicDataCollector", f"--qi-url={connection_url}"])
    except RuntimeError:
        print("Can't connect to Naoqi at ip ", args.ip, " on port ", args.port,".")
        sys.exit(1)

    collector = RawMicDataCollector(app)
    app.session.registerService("RawMicDataCollector", collector)
    collector.start()


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




