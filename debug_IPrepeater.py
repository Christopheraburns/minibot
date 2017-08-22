import RPi.GPIO as GPIO
import time
import pygame.mixer
from boto3 import Session
from contextlib import closing
import os
import socket


session = Session(profile_name="default")
ip = ' '
GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP)
requestCount = 0

def playAudio(audioFile):
    # Use pygame libaries to play the audio file we have just created
    print("sending audio to the speakers...")
    pygame.init()
    pygame.mixer.music.load(audioFile)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy() == True:
        continue
    pygame.quit()

def callPolly(tts, filename):
    print("making call to Polly for TTS...")
    polly = session.client("polly")
    response = polly.synthesize_speech(Text=tts, OutputFormat="ogg_vorbis", VoiceId="Emma")

    if "AudioStream" in response:
        print("...Polly returned an audiostream")
        # write the data stream to an audio file on disk that can be re-used later
        with closing(response["AudioStream"]) as stream:
            output = os.path.join("ip.ogg")
            try:
                with open(output, "wb") as file:
                    file.write(stream.read())
            except IOError as ioe:
                print("obtainIPAddress(): IOError: {}".format(ioe))
    else:
        print("...Polly did NOT return an audiostream!")

def obtainIPAddress():
    global ip
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 1027))
        ip = s.getsockname()[0]
        print("socket result: {}".format(ip))
        # Modify the IP address
        mod_ip = ''
        for c in ip:
            new_c = c + ' '
            mod_ip += new_c
        ip = str.replace(mod_ip, '.', 'dot')
    except Exception as e:
        print("obtainIPaddress(): Error: {}".format(e) )

def repeatIP():
    global ip
    global requestCount
    filename = "repeat_ip.ogg"
    if requestCount >= 0 and requestCount <= 2:
        tts = "My IP address is " + str(ip) + "."

    callPolly(tts, filename)
    playAudio("ip.ogg")

while True:
    input_state = GPIO.input(23)
    if input_state == False:
        print('Button Pressed')
        obtainIPAddress()
        repeatIP()
        time.sleep(0.2)