import cv2
import time
import numpy as np
import HandTrakingModule as htm
import math

from ctypes import cast,POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

cap = cv2.VideoCapture(0)

pTime = 0

devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(
    IAudioEndpointVolume._iid_, CLSCTX_ALL, None
)
volume = cast(interface, POINTER(IAudioEndpointVolume))
volumeRange = volume.GetVolumeRange()
#volume.SetMasterVolumeLevel( , None)
#-63.5 0.0 0.5
minVol = volumeRange[0]
maxVol = volumeRange[1]

detector = htm.HandDetector(detectionCon=0.7)

while True:
    success, img = cap.read()
    img = detector.find_hands(img)
    lmList = detector.findPosition(img, draw=False)

    if len(lmList) != 0:
        print(lmList[4], lmList[8])

        x1, y1 = lmList[4][1], lmList[4][2]
        x2, y2 = lmList[8][1], lmList[8][2]

        cv2.circle(img, (x1,y1), 15, (255, 0 ,255), cv2.FILLED)
        cv2.circle(img, (x2, y2), 15, (255, 0, 255), cv2.FILLED)
        cv2.line(img, (x1,y1), (x2, y2), (255, 0, 255), 3)

        lengthVolumeLine = math.hypot(x2 - x1, y2 - y1)

        vol = np.interp(lengthVolumeLine, [50, 300], [minVol, maxVol])
        volume.SetMasterVolumeLevel(vol, None)


    cTime = time.time()
    fps = 1 / (cTime - pTime)
    pTime = cTime

    cv2.putText(img, str(int(fps)), (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                1, (0, 255, 0), 2)

    cv2.imshow("img", img)
    cv2.waitKey(1)