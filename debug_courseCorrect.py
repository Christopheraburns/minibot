import cv2
import numpy as np
import matplotlib.pyplot as plt


img = cv2.imread('course-correct.png')

height, width, depth = img.shape
print('height: {}, width: {}'.format(height, width))
cropped = img[350:480, 0:640].copy()


def getLaneWidth(img):
    boundaries = [
        ([70, 58, 52], [255, 120, 100])  #blue
    ]

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

    # get left edge co-ords
    edge = cv2.Canny(leftcrop, 100, 200)
    ans = []
    for y in range(0, edge.shape[0]):
        for x in range(0, edge.shape[1]):
            if edge[y, x] != 0:
                ans = ans + [[x, y]]
    ans = np.array(ans)
    leftedge = ans[-1][0]

    # get right edge co-ords
    ans = []
    edge = cv2.Canny(rightcrop, 100, 200)
    for y in range(0, edge.shape[0]):
        for x in range(0, edge.shape[1]):
            if edge[y, x] != 0:
                ans = ans + [[x, y]]
    ans = np.array(ans)
    rightedge = ans[-1][0]

    # Get the lane width (we know that is 11.5CM)
    lanewidth = (320 - leftedge) + ((320 - leftedge) + rightedge)


    return lanewidth

    '''
    # Determine if the lane is off-center, which way, and by how much
    leftmargin = leftedge
    rightmargin = 320 - rightedge

    calibrationFactor = 11.5 / lanewidth
   

    if leftmargin > rightmargin:  # we are misaligned to the left
        # How much?  - Half of the difference of the margins
        diff = leftmargin - rightmargin
        offsetInPixels = diff / 2
        offsetInCM = offsetInPixels * calibrationFactor
        print("Misaligned to the left by {} CM(s)".format(offsetInCM))
    elif rightmargin > leftmargin:  # we are misaligned to the right
        # How Much - Half of the difference of the margins
        diff = rightmargin - leftmargin
        offsetInPixels = diff / 2
        offsetInCM = offsetInPixels * calibrationFactor
        print("Misaligned to the right by {} CM(s)".format(offsetInCM))

    plt.subplot(131), plt.title('LeftCrop'), plt.imshow(leftcrop)
    plt.subplot(132), plt.title('RightCrop'), plt.imshow(rightcrop)
    plt.subplot(133), plt.title('blue'), plt.imshow(blue)
    plt.show()
    '''

boundaries = [  #B->G->R in CV2 - not R->G->B
    ([0, 0, 97], [100, 100, 200]) #red
]

for(lower, upper) in boundaries:
    # create numpy arrays from the boundaries
    lower = np.array(lower, dtype="uint8")
    upper = np.array(upper, dtype="uint8")

    #find the colors within the specified boundaries and apply the mask
    mask = cv2.inRange(cropped, lower, upper)
    red = cv2.bitwise_and(cropped, cropped, mask = mask)

    cv2.imshow("red", np.hstack([cropped, red]))
    cv2.waitKey(0)


edge = cv2.Canny(red, 100, 200).copy()

cv2.imshow("redCanny", edge)
cv2.waitKey(0)


ans = []
for y in range(0, edge.shape[0]):
    for x in range(0, edge.shape[1]):
        if edge[y, x] != 0:
            ans = ans + [[x, y]]
ans = np.array(ans)

print(ans)

centerline = ans[-1][0]

lanewidth = getLaneWidth(cropped)

calibrationFactor = 20 / lanewidth

# should be at 320 +/- 12
if centerline > 332: # offset to the right
    # How much offset -
    rightoffset = (centerline - 320)
    offsetInCM = rightoffset * calibrationFactor
    print("offset to the right by {} pixels or {} CM(s)".format(rightoffset, offsetInCM))
if centerline < 308: # offset to the left
    leftoffset = (320 - centerline)
    offsetInCM = leftoffset * calibrationFactor
    print("offset to the left by {} pixel or {} CM(s)".format(leftoffset, offsetInCM))
