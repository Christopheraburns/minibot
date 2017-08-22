from boto3 import Session
from botocore.exceptions import BotoCoreError, ClientError


confidence_level = 00
myApiCalls = {"detect_labels", "detect_faces", "detect_moderationlabels", "recognize_celebrities"}

session = Session(profile_name="default")
rekognition = session.client("rekognition")



with open('./captures/capture1.png', "rb")as imagefile:
    bytes = imagefile.read()
    for api in myApiCalls:
        if api == "detect_labels":
            # response = rekognition.detect_labels(Image={'Bytes': imagefile.read()})
            response = rekognition.detect_labels(Image={'Bytes': bytes})
            print("Detect Labels API call...")
            print("#########################")
            for label in response["Labels"]:
                if label["Confidence"] > float(confidence_level):
                    # store the label somewhere
                    print(label)
            print(" ")

        elif api == "detect_faces":
            # response = rekognition.detect_faces(Image={'Bytes': imagefile.read()})
            response = rekognition.detect_faces(Image={'Bytes': bytes})
            print("Detect Faces API Call ...")
            print("#########################")
            print("# of faces: " + str(len(response["FaceDetails"])))
            print(" ")
        elif api == "detect_moderationlabels":
            # response = rekognition.detect_moderation_labels(Image={'Bytes': imagefile.read()})
            response = rekognition.detect_moderation_labels(Image={'Bytes': bytes})
            print("Detect Moderation Labels...")
            print("##########################")
            if len(response["ModerationLabels"]) > 0:
                for mod in response["ModerationLabels"]:
                    print(mod)
            else:
                print("None")
            print(" ")
        elif api == "recognize_celebrities":
            # response = rekognition.recognize_celebrities(Image={'Bytes': imagefile.read()})
            response = rekognition.recognize_celebrities(Image={'Bytes': bytes})
            print("Recognize Celebrities API Call....")
            print("###########################")
            if len(response["CelebrityFaces"]) > 0:
                for celebrity in response["CelebrityFaces"]:
                    if celebrity['Face']['Confidence'] > confidence_level:
                        print(celebrity['Name'])

            else:
                print("None")
            # for face in response["Face"]:
            # if face["Confidence"] > float(confidence_level):
            # store the label somewhere
            # print(face)

