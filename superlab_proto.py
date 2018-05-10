import time
from datetime import datetime, timedelta
import threading
import json
import atexit
import RPi.GPIO as GPIO
import numpy as np
import cv2
import os.path
from courseCorrector import calcErr
from boto3 import Session
from botocore.exceptions import BotoCoreError, ClientError

class ScoreBoard:
    teams = []
    history = []

class Team:
    team_id = 66 #Default value to make sure the Team create process loads the TeamInfo json correctly
    scenes = []
    starting_score = 0
    current_score = 0

    def setTeam(self, teamid):
        self.team_id = teamid

    def addScenes(self, s):
        self.scenes.append(s)

class Scene:
    picks = []
    scene_id = ""
    def setScene(self, sceneid):
        self.scene_id = sceneid


    def addPicks(self, p):
        self.picks.append(p)

    @property
    def getPicks(self):
        return(self.picks)

class Pick:
    def __init__(self, name):
        self.name = name

    confidence_level = 0
    apiToCall = []

    def setPicks(self, confidence_level, apis):
        self.confidence_level = confidence_level
        self.apis = apis

master_data = ""
scoreboard = ScoreBoard()


confidence_level = 00
myApiCalls = {"detect_labels", "detect_faces", "detect_moderationlabels", "recognize_celebrities"}
session = Session(profile_name="default")
rekognition = session.client("rekognition")
teamID = ''
allStop = False
retryCapture = False

# Use BCM GPIO references
# instead of physical pin numbers
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Define GPIO signals to use
LeftPins = [17, 18, 27, 22]
RightPins = [6, 13, 19, 26]

# Set all pins as output
for p in LeftPins:
    GPIO.setup(p, GPIO.OUT)
    GPIO.output(p, False)

for p in RightPins:
    GPIO.setup(p, GPIO.OUT)
    GPIO.output(p, False)

def cleanup():
    GPIO.cleanup

def shutdown():
    cleanup()
    exit()

atexit.register(cleanup)

Seq = [[1, 0, 0, 1],
       [1, 0, 0, 0],
       [1, 1, 0, 0],
       [0, 1, 0, 0],
       [0, 1, 1, 0],
       [0, 0, 1, 0],
       [0, 0, 1, 1],
       [0, 0, 0, 1]]

WaitTime = 10 / float(4500)

# Load the teams confidence levels and API calls the teams want to call
def loadTeams():
    # Open the master file
    with open('teamInfo.json') as data_file:
        json_data = json.load(data_file)

    # Load the team predictions
    TeamPredictions = []
    teamcount = len(json_data["teams"])

    for t in range(teamcount):
        t = Team()
        TeamPredictions.append(t)

    counter = 0

    for team in json_data["teams"]:
        TeamPredictions[counter].setTeam(teamid=counter)
        Stations = []
        # Make sure we have 11 picks
        for i in range(11):
            s = Scene()
            Stations.append(s)
        stationCounter = 0
        for pick in team["picks"]:
            Stations[stationCounter].scene_id = pick["stationId"]

            p = Pick(pick["stationId"])
            p.confidence_level = pick["confidence"]
            apis = pick["apis"]
            apiToCall = [None] * 4
            for api in apis:
                if api["name"] == "detect_labels":
                    if api["value"] == "True":
                        apiToCall[0] = 1
                    else:
                        apiToCall[0] = 0
                elif api["name"] == "detect_faces":
                    if api["value"] == "True":
                        apiToCall[1] = 1
                    else:
                        apiToCall[1] = 0
                elif api["name"] == "recognize_celebrity":
                    if api["value"] == "True":
                        apiToCall[2] = 1
                    else:
                        apiToCall[2] = 0
                elif api["name"] == "detect_moderation_labels":
                    if api["value"] == "True":
                        apiToCall[3] = 1
                    else:
                        apiToCall[3] = 0

            p.apiToCall = apiToCall
            Stations[stationCounter].picks = p
            stationCounter = stationCounter + 1

        TeamPredictions[counter].scenes = Stations
        counter = counter + 1

    return TeamPredictions


# Call this routine ONCE for each station
def StationScoring(image_path, stationid=0):
    global scoreboard
    for station in master_data["stations"]:
        #print(station["station_id"])
        if station["station_id"] == stationid:
            station_json = station

    #load the image file
    #with open('./master_images/station1.jpg', "rb")as imagefile:
    with open(image_path, "rb")as imagefile:
        bytes = imagefile.read()

    #Call all 4 Reko APIs

    #API #1 Detect_Labels
    detect_labels_response = rekognition.detect_labels(Image={'Bytes': bytes})
    #API #2 Detect_faces
    detect_faces_response = rekognition.detect_faces(Image={'Bytes': bytes})
    #API #3 detect_moderationlabels
    moderation_response = rekognition.detect_moderation_labels(Image={'Bytes': bytes})
    #API #4 recognize_celebrities":
    celebrity_response = rekognition.recognize_celebrities(Image={'Bytes': bytes})

    #Now that we have all the API calls - compare what the team predicted agains the master

    for team in TeamInfo:
        team_cl = team.scenes[stationid-1].picks.confidence_level

        #True Positives

        #did the team choose detect_labels API on this scene?
        #if yes, does the response with the Team's confidence level applied match the master response

        # Detect Labels
        if team.scenes[stationid-1].picks.apiToCall[0] == 1:
            print("Team # {} chose to call the detect_labels API against Station # {}".format(team.team_id, stationid))
            # What is the confidence level the team chose

            # take only the detect labels responses that are equal to or GREATER than the team_cl
            detect_label_hits = []
            for detect_label in detect_labels_response["Labels"]:
                if detect_label["Confidence"] >= float(team_cl):
                    # verify that this label is in the MasterFile
                    hit = False
                    for verify_detect_label in station_json["detect_labels"]:
                        if verify_detect_label["Name"] == detect_label["Name"]:
                            hit = True
                    if hit:
                        detect_label_hits.append(detect_label)
                        event = "Team # {} correctly matched a detect_labels object {} at Station # {} +1 point".format(team.team_id, detect_label["Name"], stationid)
                        print(event)
                        scoreboard.teams[team.team_id].current_score = scoreboard.teams[team.team_id].current_score + 1
                        scoreboard.history.append(event)


        # Detect Faces
        if team.scenes[stationid-1].picks.apiToCall[1] == 1:
            print("Team # {} chose to call the detect_faces API against Station # {}".format(team.team_id, stationid))

            detect_faces_hits = []
            for detect_face_label in detect_faces_response["FaceDetails"]:
                if detect_face_label["Confidence"] >= float(team_cl):
                    detect_faces_hits.append(detect_face_label)
                    event = "Team # {} correctly detected a face at Station # {} +1 point".format(team.team_id, stationid)
                    print(event)
                    scoreboard.teams[team.team_id].current_score = scoreboard.teams[team.team_id].current_score + 1
                    scoreboard.history.append(event)


        # Detect_moderationlabels
        if team.scenes[stationid-1].picks.apiToCall[2] == 1:
            print("Team # {} chose to call the moderation_labels API against Station # {}".format(team.team_id, stationid))

            moderation_hits = []
            #TODO
            #There are no moderation hits - come back to this code later

        # recognize_celebrities
        if team.scenes[stationid-1].picks.apiToCall[3] == 1:
            print("Team # {} chose to call the recognize_celebrities API against Station # {}".format(team.team_id, stationid))

            celebrity_hits = []
            if len(celebrity_response["CelebrityFaces"]) > 0:
                for celebrity in celebrity_response["CelebrityFaces"]:
                    if celebrity["MatchConfidence"] >= float(team_cl):
                        celebrity_hits.append(celebrity)
                        event = "Team # {} correctly detected a Celebrity {} at Station {}  +1 point".format(team.team_id, celebrity["Name"], stationid)
                        print(event)
                        scoreboard.teams[team.team_id].current_score = scoreboard.teams[team.team_id].current_score + 1
                        scoreboard.history.append(event)

def loadMasters():
    global master_data
    with open('master_json.json') as data_file:
        master_data = json.load(data_file)

def StartingScores():
    global TeamInfo
    global scoreboard
    #Create the ScoreBoard object
    teams = []
    for team in TeamInfo:
        t = Team()
        teams.append(t)

    scoreboard.teams = teams

    for i in range(len(TeamInfo)):
        pointsCharged = 0
        scoreboard.teams[i].team_id = TeamInfo[i].team_id
        #Iterate each scene - 1pt per API call - Max (min) starting score is -44
        for scene in TeamInfo[i].scenes:
            sceneId = scene.scene_id
            apis = scene.picks.apiToCall
            for l in range(4):
                if apis[l] == 1:
                    #Make the API call = Charge 1 point
                    pointsCharged = pointsCharged + 1

        scoreboard.teams[i].starting_score = -pointsCharged
        scoreboard.teams[i].current_score = scoreboard.teams[i].starting_score
        print("Team # {} will be charged {} points to begin the challenge".format(scoreboard.teams[i].team_id, scoreboard.teams[i].starting_score))

def leftwheel(dur, direction='forward'):
    global allStop
    global WaitTime
    global seq
    StepCounter = 0
    StepCount = len(Seq)
    StepDir = 1 # Set to 1 or 2 for clockwise
    if direction == 'reverse':
        StepDir = -1 # Set to -1 or -2 for anti-clockwise
    start = datetime.now()
    end = start + timedelta(seconds = dur)
    print("activating left wheel for {} seconds".format(str(dur)))
    while not allStop:
        for pin in range(0, 4):
            xpin = LeftPins[pin]  # Get GPIO
            if Seq[StepCounter][pin] != 0:
                GPIO.output(xpin, True)
            else:
                GPIO.output(xpin, False)

        StepCounter += StepDir

        # If we reach the end of the sequence
        # start again
        if (StepCounter >= StepCount):
            StepCounter = 0
        if (StepCounter < 0):
            StepCounter = StepCount + StepDir

        # Wait before moving on
        time.sleep(WaitTime)
        if datetime.now() >= end:
            allStop = True


def rightwheel(dur, direction='forward'):
    # Start main loop
    global allStop
    global WaitTime
    global seq
    StepCounter = 0
    StepCount = len(Seq)
    StepDir = -1  # Set to 1 or 2 for clockwise
    # Set to -1 or -2 for anti-clockwise
    if direction == 'reverse':
        StepDir = 1 # Set to -1 or -2 for anti-clockwise
    try:
        start = datetime.now()
        end = start + timedelta(seconds=dur)
        print("activating right wheel for {} seconds".format(str(dur)))
        while not allStop:
            for pin in range(0, 4):
                xpin = RightPins[pin]  # Get GPIO
                if Seq[StepCounter][pin] != 0:
                    GPIO.output(xpin, True)
                else:
                    GPIO.output(xpin, False)

            StepCounter += StepDir

            # If we reach the end of the sequence
            # start again
            if (StepCounter >= StepCount):
                StepCounter = 0
            if (StepCounter < 0):
                StepCounter = StepCount + StepDir

            # Wait before moving on
            time.sleep(WaitTime)
            if datetime.now() >= end:
                allStop = True
    except Exception:
        print(Exception.args)


def bothwheels(dur, direction='forward'):
    global allStop
    global WaitTime
    global seq
    Right_StepCounter = 0
    Left_StepCounter = 0
    StepCount = len(Seq)
    leftDir = 1
    rightDir = -1
    if direction == 'reverse':
        leftDir = -1
        rightDir = 1
    start = datetime.now()
    end = start + timedelta(seconds=dur)
    print("activating tank mode for {} seconds".format(str(dur)))
    while not allStop:
        for pin in range(0, 4):
            lpin = LeftPins[pin]
            rpin = RightPins[pin]
            if Seq[Right_StepCounter][pin] != 0:
                GPIO.output(rpin, True)
            else:
                GPIO.output(rpin, False)

            if Seq[Left_StepCounter][pin] != 0:
                GPIO.output(lpin, True)
            else:
                GPIO.output(lpin, False)

        Right_StepCounter += rightDir
        Left_StepCounter += leftDir

        # If we reach the end of the sequence
        # start again
        if (Right_StepCounter >= StepCount):
            Right_StepCounter = 0
        if (Right_StepCounter < 0):
            Right_StepCounter = StepCount + rightDir

        if (Left_StepCounter >= StepCount):
            Left_StepCounter = 0
        if (Left_StepCounter < 0):
            Left_StepCounter = StepCount + leftDir

        # Wait before moving on
        time.sleep(WaitTime)
        if datetime.now() >= end:
            allStop = True


def correctLeft(delta):
    global allStop
    left = 0
    forward = 0
    right = 0
    reverse = 0

    if delta > 2.5:
        # this is probably bad news
        right = 2.5
        forward = 1.0
        left = 2.5
        reverse = 2.75

    elif delta > 1.551 and delta <= 2.5:
        right = 2.0
        forward = 1.0
        left = 2.0
        reverse = 2.5

    elif delta >= .75 and delta <= 1.55:
        right = 1.5
        forward = .75
        left = 1.5
        reverse = 2.00

    elif delta >= .25 and delta <= .74:
        right = 1.0
        forward = .5
        left = 1.0
        reverse = 1.25

    allStop = False
    leftwheel(float(left))

    allStop = False
    bothwheels(float(forward))

    allStop = False
    rightwheel(float(right))

    allStop = False
    bothwheels(float(reverse), direction='reverse')


def correctRight(delta):
    global allStop
    left = 0
    forward = 0
    right = 0
    reverse = 0

    if delta > 2.5:
        # this is probably bad news
        right = 2.5
        forward = 1.0
        left = 2.5
        reverse = 2.75

    elif delta > 1.551 and delta <= 2.5:
        right = 2.0
        forward = 1.0
        left = 2.0
        reverse = 2.5

    elif delta >= .75 and delta <= 1.55:
        right = 1.5
        forward = .75
        left = 1.5
        reverse = 2.00

    elif delta >= .25 and delta <= .74:
        right = 1.0
        forward = .5
        left = 1.0
        reverse = 1.25

    allStop = False
    rightwheel(float(right))

    allStop = False
    bothwheels(float(forward))

    allStop = False
    leftwheel(float(left))

    allStop = False
    bothwheels(float(reverse), direction='reverse')


def shutdownorder(args):
    if args[0].lower() == "quit":
            print("quit command received, shutting down")
            shutdown()
    elif args[0].lower() == "exit":
            print("exit command received, shutting down")
            shutdown()
    else:
        return False


def getImageNum():
    increment = "0"
    if os.path.isfile('./captures/capture1.png'):
        for x in range(2, 15):
            print("debug - looping for new file number")
            filename = './captures/capture' + str(x) + '.png'
            if os.path.isfile(filename):
                print("debug - {} already exists".format(filename))
                pass
            else:
                increment = str(x)
                break
    else:
        #no capture1.png
        increment = "1"
    return increment


def clearCaptures():
    folder = './captures'

    for file in os.listdir(folder):
        print('found {} to delete'.format(file))
        print('deleting {} '.format('./captures/' + file))
        os.remove('./captures/' + file)

# Call this routine ONCE for each station
def StationScoring(image_path, stationid=0):
    global scoreboard
    for station in master_data["stations"]:
        #print(station["station_id"])
        if station["station_id"] == stationid:
            station_json = station

    #load the image file
    #with open('./master_images/station1.jpg', "rb")as imagefile:
    with open(image_path, "rb")as imagefile:
        bytes = imagefile.read()

    #Call all 4 Reko APIs

    #API #1 Detect_Labels
    detect_labels_response = rekognition.detect_labels(Image={'Bytes': bytes})
    #API #2 Detect_faces
    detect_faces_response = rekognition.detect_faces(Image={'Bytes': bytes})
    #API #3 detect_moderationlabels
    moderation_response = rekognition.detect_moderation_labels(Image={'Bytes': bytes})
    #API #4 recognize_celebrities":
    celebrity_response = rekognition.recognize_celebrities(Image={'Bytes': bytes})

    #Now that we have all the API calls - compare what the team predicted agains the master

    for team in TeamInfo:
        team_cl = team.scenes[stationid-1].picks.confidence_level

        #True Positives

        #did the team choose detect_labels API on this scene?
        #if yes, does the response with the Team's confidence level applied match the master response

        # Detect Labels
        if team.scenes[stationid-1].picks.apiToCall[0] == 1:
            print("Team # {} chose to call the detect_labels API against Station # {}".format(team.team_id, stationid))
            # What is the confidence level the team chose

            # take only the detect labels responses that are equal to or GREATER than the team_cl
            detect_label_hits = []
            for detect_label in detect_labels_response["Labels"]:
                if detect_label["Confidence"] >= float(team_cl):
                    # verify that this label is in the MasterFile
                    hit = False
                    for verify_detect_label in station_json["detect_labels"]:
                        if verify_detect_label["Name"] == detect_label["Name"]:
                            hit = True
                    if hit:
                        detect_label_hits.append(detect_label)
                        event = "Team # {} correctly matched a detect_labels object {} at Station # {} +1 point".format(team.team_id, detect_label["Name"], stationid)
                        print(event)
                        scoreboard.teams[team.team_id].current_score = scoreboard.teams[team.team_id].current_score + 1
                        scoreboard.history.append(event)


        # Detect Faces
        if team.scenes[stationid-1].picks.apiToCall[1] == 1:
            print("Team # {} chose to call the detect_faces API against Station # {}".format(team.team_id, stationid))

            detect_faces_hits = []
            for detect_face_label in detect_faces_response["FaceDetails"]:
                if detect_face_label["Confidence"] >= float(team_cl):
                    detect_faces_hits.append(detect_face_label)
                    event = "Team # {} correctly detected a face at Station # {} +1 point".format(team.team_id, stationid)
                    print(event)
                    scoreboard.teams[team.team_id].current_score = scoreboard.teams[team.team_id].current_score + 1
                    scoreboard.history.append(event)


        # Detect_moderationlabels
        if team.scenes[stationid-1].picks.apiToCall[2] == 1:
            print("Team # {} chose to call the moderation_labels API against Station # {}".format(team.team_id, stationid))

            moderation_hits = []
            #TODO
            #There are no moderation hits - come back to this code later

        # recognize_celebrities
        if team.scenes[stationid-1].picks.apiToCall[3] == 1:
            print("Team # {} chose to call the recognize_celebrities API against Station # {}".format(team.team_id, stationid))

            celebrity_hits = []
            if len(celebrity_response["CelebrityFaces"]) > 0:
                for celebrity in celebrity_response["CelebrityFaces"]:
                    if celebrity["MatchConfidence"] >= float(team_cl):
                        celebrity_hits.append(celebrity)
                        event = "Team # {} correctly detected a Celebrity {} at Station {}  +1 point".format(team.team_id, celebrity["Name"], stationid)
                        print(event)
                        scoreboard.teams[team.team_id].current_score = scoreboard.teams[team.team_id].current_score + 1
                        scoreboard.history.append(event)

def captureImage():
    global retryCapture
    # TODO
    # Investigate intermittent error (AttributeError: 'NoneType' object has no attribute shape)
    print("capturing image")
    # Snap a pic

    try:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
    except Exception:
        # Image Capture probably failed - retry
        retryCapture = True


    if not retryCapture:
        # flip the image since camera is upside down
        rows, cols, depth = frame.shape
        M = cv2.getRotationMatrix2D((cols/2, rows/2), 180, 1)
        frame = cv2.warpAffine(frame, M, (cols, rows))

        #scale the image down for better performance to AWS
        frame = cv2.resize(frame,None, fx=.5, fy=.5, interpolation=cv2.INTER_AREA)
        incr = getImageNum()
        cv2.imwrite('./captures/capture' + incr + '.png', frame)

        StationScoring(image_path='./captures/capture' + incr + '.png', stationid=incr)

        #print("Scene #: {}".format(incr))
        #print("image captured and saved..")

        # Send the image to AWS for analysis
        # with open('./captures/capture' + incr + '.png', "rb")as imagefile:
        #with open('./captures/capture' + incr + '.png', "rb")as imagefile:
        #    bytes = imagefile.read()
        #    for api in myApiCalls:
        #        if api == "detect_labels":
        #            # response = rekognition.detect_labels(Image={'Bytes': imagefile.read()})
        #            response = rekognition.detect_labels(Image={'Bytes': bytes})
        #            print("Detect Labels API call...")
        #            print("#########################")
        #            for label in response["Labels"]:
        #                if label["Confidence"] > float(confidence_level):
        #                    # store the label somewhere
        #                    print(label)
        #            print(" ")

        #        elif api == "detect_faces":
                    # response = rekognition.detect_faces(Image={'Bytes': imagefile.read()})
        #            response = rekognition.detect_faces(Image={'Bytes': bytes})
        #            print("Detect Faces API Call ...")
        #            print("#########################")
        #            print("# of faces: " + str(len(response["FaceDetails"])))
        #            print(" ")
        #        elif api == "detect_moderationlabels":
        #            # response = rekognition.detect_moderation_labels(Image={'Bytes': imagefile.read()})
        #            response = rekognition.detect_moderation_labels(Image={'Bytes': bytes})
        #            print("Detect Moderation Labels...")
        #           print("##########################")
        #            if len(response["ModerationLabels"]) > 0:
        #                for mod in response["ModerationLabels"]:
        #                    print(mod)
        #            else:
        #                print("None")
        #            print(" ")
        #        elif api == "recognize_celebrities":
        #            # response = rekognition.recognize_celebrities(Image={'Bytes': imagefile.read()})
        #            response = rekognition.recognize_celebrities(Image={'Bytes': bytes})
        #            print("Recognize Celebrities API Call....")
        #            print("###########################")
        #            if len(response["CelebrityFaces"]) > 0:
        #                for celebrity in response["CelebrityFaces"]:
        #                    if celebrity['Face']['Confidence'] > confidence_level:
        #                        print(celebrity['Name'])

        #            else:
        #                print("None")


def courseCorrection(debug=False, saveImages=False):
    print("executing course correction...")
    try:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        # flip the image since camera is upside down
        rows, cols, depth = frame.shape
        M = cv2.getRotationMatrix2D((cols / 2, rows / 2), 180, 1)
        frame = cv2.warpAffine(frame, M, (cols, rows))
        cv2.imwrite('./captures/course-correct.png', frame)
        retryCapture = False

        print("Calculating alignment error...")
        # Pass the image to our course corrector
        direction, variation = calcErr(frame, debug, saveImages)
        print("directional misalignment: {} deviation of {} CM(s)".format(direction, variation))
        if variation > .25:
            if direction == "right":
                print("Correcting to the right: {} CM(s)".format(variation))
                correctRight(variation)
            elif direction == "left":
                print("Correcting to the left: {} CM(s)".format(variation))
                correctLeft(variation)
            else:
                print("no correction required at this point")
        else:
            print("deviation within acceptable range, no correction needed")
    except Exception as e:
        retryCapture = True
        print("Error: superlab.py: courseCorrection(): {}".format(e))


def navControl(modelB):
    global allStop
    # Read the nav control document
    if modelB == True:
        print("loading Model-B navigation")
        navigation = open('navigation-modelb', "r")
    else:
        navigation = open("navigation", "r")

    commands = navigation.readlines()
    # remove newline character
    commands = [x.strip() for x in commands]
    x = 1
    for command in commands:
        if command.startswith("#") or command.startswith(" "):
            # ignore this line
            pass
        elif command == "course-correct":
            courseCorrection(debug=True,saveImages=True)
        elif command == "capture":
            allStop = True
            captureImage()
            for x in range(5):
                if retryCapture:
                    captureImage()
                else:
                    break
        elif command.startswith("forward"):
            allStop = False
            action = command.split(" ")
            bothwheels(float(action[1]))
        elif command.startswith("reverse"):
            allStop = False
            action = command.split(" ")
            bothwheels(float(action[1]), "reverse")
        elif command.startswith("rev-left"):
            allStop = False
            action = command.split(" ")
            leftwheel(float(action[1]), direction='reverse')
        elif command.startswith("rev-right"):
            allStop = False
            action = command.split(" ")
            rightwheel(float(action[1]), direction='reverse')
        else: # a turn order
            if command != " ":
                if command.startswith("left"):
                    allStop = False
                    # turn left
                    action = command.split(" ")
                    leftwheel(float(action[1]))
                elif command.startswith("right"):
                    allStop = False
                    # turn right
                    action = command.split(" ")
                    rightwheel(float(action[1]))
        x+=1


def argsverified(args):
    global allStop
    try:
        if args[0].lower() == "course-correct":
            debug = False
            save = False
            if len(args) > 1:
                debug = args[1].lower()
                print("course-correct debug flag set to {}".format(debug))
            if len(args) > 2:
                save = args[2].lower()
                print("course-correct save image flag set to {}".format(save))

            courseCorrection(debug=debug, saveImages=save)
            return True

        if args[0].lower() == "clear-captures":
            clearCaptures()
            return True

        if args[0].lower() == "stop":
            # Lock the brakes
            allStop = True
            # Issue stop command here and re-prompt
            return False

        if args[0].lower() == 'capture':
            # don't need a second parameter
            return True

        if args[0].lower() == 'navigate':
            return True

        if len(args) < 2:
            print("minibot requires a command and a duration for the command.  i.e Forward 5")
            return False

        if not isinstance(float(args[1]), float):
            print("The command duration must be an integer")
            return False
    except Exception:
        #Print error then return
        print(Exception.args)
        pass

    return True

#Load Teams
TeamInfo = loadTeams()

#Create the scoreboard and calculate Starting Points
StartingScores()

#Load the master scores
loadMasters()

input_var = ""
while True:
    try:
        input_var = input("Enter a command: ")
        args = input_var.split(' ')
        if len(args) > 0:
            if not shutdownorder(args):
                if argsverified(args):
                    if args[0].lower() == "forward":
                        # unlock the brakes
                        allStop = False
                        dur = float(args[1])
                        # Drive both motors
                        threading.Thread(target=bothwheels(dur)).start()
                    elif args[0].lower() == "left":
                        # unlock the brakes
                        allStop = False
                        # Drive the left motor to turn left
                        threading.Thread(target=leftwheel(float(args[1]))).start()
                    elif args[0].lower() == "right":
                        # Unlock the brakes
                        allStop = False
                        # Drive the right motor to turn right
                        threading.Thread(target=rightwheel(float(args[1]))).start()
                    elif args[0].lower() == "capture":
                        # take an image
                        threading.Thread(target=captureImage).start()
                    elif args[0].lower() == "navigate":
                        clearCaptures()
                        modelB = False
                        if args[1].lower() == "modelb":
                            modelB = True
                        # initiate auto-nav
                        if len(args) > 2:
                            teamID = str(args[2])
                        threading.Thread(target=navControl(modelB=modelB)).start()
                    elif args[0].lower() == "rev-left":
                        # reverse left
                        allStop = False
                        threading.Thread(target=leftwheel(float(args[1]), direction='reverse')).start()
                    elif args[0].lower() == "rev-right":
                        # reverse left
                        allStop = False
                        threading.Thread(target=rightwheel(float(args[1]), direction='reverse')).start()
                    elif args[0].lower() == "reverse":
                        # reverse
                        allStop = False
                        threading.Thread(target=bothwheels(float(args[1]), direction='reverse')).start()

        else:
            print("minibot requires a movement command and duration. i.e Forward 5")
    except Exception:
        # ignore all exceptions here - focus on straying alive
        pass