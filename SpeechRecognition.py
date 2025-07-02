import time
from naoqi import ALProxy

ROBOT_IP = "192.168.1.118"




# Creates a proxy on the speech-recognition module
asr = ALProxy("ALSpeechRecognition", ROBOT_IP, 9559)

asr.setLanguage("English")

mem = ALProxy("ALMemory", ROBOT_IP, 9559)


# Example: Adds "yes", "no" and "please" to the vocabulary (without wordspotting)
vocabulary = ["yes", "no", "please", "polo"]
asr.setVocabulary(vocabulary, False)

# Start the speech recognition engine with user Test_ASR
asr.subscribe("Test_ASR")
print ('Speech recognition engine started')

for _ in range(10):
    data = mem.getData("WordRecognized")
    print("Recognized",data)
    

time.sleep(20)
asr.unsubscribe("Test_ASR")