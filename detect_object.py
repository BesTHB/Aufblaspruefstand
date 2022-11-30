import cv2
import numpy as np
from matplotlib import pyplot as plt


# src: https://www.youtube.com/watch?v=lbgl2u6KrDU
# src: https://www.youtube.com/watch?v=UlM2bpqo_o0


aruco_params = cv2.aruco.DetectorParameters_create()
aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_50)

# connect with webcam
# (iterate through numbers in order to find the correct webcam, if multiple are available)
cap = cv2.VideoCapture(0)

# set displayed size of the webcam image/video
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# read webcam in infinite loop
while cap.isOpened():
    # get current webcam imgage
    ret, img = cap.read()

    # detect aruco markers in current webcam image
    corners, ids, _ = cv2.aruco.detectMarkers(img, aruco_dict, parameters=aruco_params)

    # draw polygon around aruco markers
    int_corners = np.int0(corners)
    cv2.polylines(img, int_corners, True, (0, 255,0), 2)

    try:
        # calculate the length of the polygon around the first detected aruco marker
        aruco_perimeter = cv2.arcLength(corners[0], True)  # in pixels

        # calculate center of polygon and display a text
        x, y = corners[0][0].mean(axis=0)
        cv2.putText(img, str(ids[0][0]), (int(x), int(y)), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 0), 1)

        # translate pixels to mm
        # (since the aruco marker is a square of side length 50mm, the length of the surrounding polygon must be 200mm)
        pixel_mm_ration = aruco_perimeter / 200

    # if currently no aruco marker is detected in the webcam image, corners[0] will throw an IndexError
    except IndexError:
        pass

    # show current webcam image
    cv2.imshow('Webcam', img)

    # break loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        print('Abbruch durch Nutzer')
        break

# close connection to webcam and destroy webcam window
cap.release()
cv2.destroyAllWindows()
