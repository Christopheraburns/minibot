import cv2
import numpy as np


def getLaneWidth(img, debug=False, saveImages=False):
    boundaries = [
        ([70, 58, 52], [255, 120, 100])  #blue
    ]

    try:
        for (lower, upper) in boundaries:
            # create numpy arrays from the boundaries
            lower = np.array(lower, dtype="uint8")
            upper = np.array(upper, dtype="uint8")

            # find the colors within the specified boundaries and apply the mask
            mask = cv2.inRange(img, lower, upper)
            blue = cv2.bitwise_and(img, img, mask=mask)

            # cv2.imshow("blue", np.hstack([img, blue]))
            # cv2.waitKey(0)

        # cut the image in half vertically to find and calculate left and right lane lines
        leftcrop = blue[0:130, 0:320].copy()
        rightcrop = blue[0:130, 320:640].copy()

        if saveImages:
            cv2.imwrite("./captures/course-correction-leftlane.png", leftcrop)
            cv2.imwrite("./captures/course-correction-rightlane.png", rightcrop)


        # get left edge co-ords
        edge = cv2.Canny(leftcrop, 100, 200)
        ans = []
        for y in range(0, edge.shape[0]):
            for x in range(0, edge.shape[1]):
                if edge[y, x] != 0:
                    ans = ans + [[x, y]]
        ans = np.array(ans)
        leftedge = ans[-1][0]

        if debug:
            print("Lane leftedge calculated at: {}".format(leftedge))

        # get right edge co-ords
        ans = []
        edge = cv2.Canny(rightcrop, 100, 200)
        for y in range(0, edge.shape[0]):
            for x in range(0, edge.shape[1]):
                if edge[y, x] != 0:
                    ans = ans + [[x, y]]
        ans = np.array(ans)
        rightedge = ans[-1][0]

        if debug:
            print("Lane right edge calculated at: {}".format(rightedge))

        # Get the lane width (we know that is 11.5CM)
        lanewidth = (320 - leftedge) + ((320 - leftedge) + rightedge)
    except Exception as e:
        print("Error: courseCorrector.py: getLaneWidth(): {}".format(e))

    return lanewidth

def calcErr(img, debug=False, saveImages=False):
    try:
        # Crop the calibration image
        if debug:
            print("COURSECORRECTOR:: Cropping course correction image..")
            cropped = img[350:480, 0:640].copy()

        if saveImages:
            cv2.imwrite("./captures/course-correction-cropped.png", cropped)

        if debug:
            print("COURSECORRECTOR:: calculating boundaries for image cropping")
        boundaries = [
            ([0, 0, 97], [90, 90, 200])  #red  # red
        ]

        if debug:
            print("COURSECORRECTOR:: creating numpy arrays from boundaries")
        for (lower, upper) in boundaries:
            # create numpy arrays from the boundaries
            lower = np.array(lower, dtype="uint8")
            upper = np.array(upper, dtype="uint8")

            # find the colors within the specified boundaries and apply the mask
            mask = cv2.inRange(cropped, lower, upper)
            red = cv2.bitwise_and(cropped, cropped, mask=mask)

        if debug:
            print("COURSECORRECTOR:: using Canny Edge detection to find lines")
        edge = cv2.Canny(red, 100, 200).copy()

        if debug:
            print("COURSECORRECTOR:: saving masked-applied image")
        if saveImages:
            cv2.imwrite("./captures/course-correction-masked.png", edge)

        if debug:
            print("COURSECORRECTOR:: calculting deviation from center...")

        ans = []
        for y in range(0, edge.shape[0]):
            for x in range(0, edge.shape[1]):
                if edge[y, x] != 0:
                    ans = ans + [[x, y]]
        ans = np.array(ans)

        centerline = ans[-1][0]
        if debug:
            print("COURSECORRECTOR:: centerline was found at X coord: {}".format(centerline))

        lanewidth = getLaneWidth(cropped, debug, saveImages)
        if debug:
            print("COURSECORRECTOR:: lanewidth calculated at: {}".format(lanewidth))

        calibrationFactor = 20 / lanewidth
        if debug:
            print("COURSECORRECTOR:: calibration factor calculated at: {}".format(calibrationFactor))

        # should be at 320 +/- 12
        if centerline > 332:  # offset to the right
            # How much offset -
            rightoffset = (centerline - 320)
            offsetInCM = rightoffset * calibrationFactor
            if debug:
                print("Centerline is offset to the right by {} pixels or {} CM(s)".format(rightoffset, offsetInCM))
            return "right", offsetInCM

        elif centerline < 308:  # offset to the left
            leftoffset = (320 - centerline)
            offsetInCM = leftoffset * calibrationFactor
            if debug:
                print("Centerline is offset to the left by {} pixel or {} CM(s)".format(leftoffset, offsetInCM))
            return "left", offsetInCM
        else:
            if debug:
                print("bot is on center")
            return "centered", 0
    except Exception as e:
        print("Error: courseCorrector.py: calcErr(): {}".format(e))


