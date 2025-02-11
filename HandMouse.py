import cv2
import numpy as np
import HandTrakingModule as htm
import time
from pynput.mouse import Button, Controller
import keyboard
import ctypes


class HandControl:
    def __init__(self, wCam=640, hCam=360, smoothening=7 ):
        # Set cam resolution
        self.wCam, self.hCam = wCam, hCam
        self.smoothening = smoothening

        self.user32 = ctypes.windll.user32
        self.wScreen, self.hScreen = self.user32.GetSystemMetrics(0), self.user32.GetSystemMetrics(1)

        self.frameReduction = int(self.wCam * 0.1)
        self.adapterForCam = 50

        self.mouse = Controller()

        # Smoothening variables
        self.pLocX, self.pLocY = 0, 0
        self.cLocX, self.cLocY = 0, 0
        self.clickSmother = 0
        self.RightButtonPressed = False
        self.LeftButtonPressed = False

        self.handDetector = htm.HandDetector(maxHands=1)

        self.delayButton = 0;

        self.centerPoint = hCam // 2
        self.scroll_direction = 0

    def process_frame(self, img):
        img = self.handDetector.findHand(img)
        landmarksList = self.handDetector.findPosition(img, draw=False)

        if not self.delayButton == 30 and not (self.RightButtonPressed or self.LeftButtonPressed):
            self.delayButton += 1
        elif self.delayButton == 30:
            self.RightButtonPressed, self.LeftButtonPressed = False, False


        if len(landmarksList) != 0:
            # Set coordinates for:
            # Thumb
            # Index finger
            # Middle finger
            x0, y0 = landmarksList[4][1], landmarksList[4][2]
            x1, y1 = landmarksList[8][1], landmarksList[8][2]
            x2, y2 = landmarksList[12][1], landmarksList[12][2]

            holdAMoveX1, holdAMoveY1 = landmarksList[9][1], landmarksList[9][2]
            holdAMoveX2, holdAMoveY2 = landmarksList[0][1], landmarksList[0][2]

            fingers = self.handDetector.fingersUp()

            # Draw rectangle for mouse control
            cv2.rectangle(img, (self.frameReduction, self.frameReduction + self.adapterForCam),
                          ((self.wCam - self.frameReduction), (self.hCam - self.frameReduction + self.adapterForCam)),
                          (255, 0, 0), 2)

            # Move mouse if only index finger up
            if fingers[1] == 1 and fingers[2] == 1 and fingers.count(1) == 2:
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                cv2.circle(img, (cx, cy), 15, (255, 0, 255), cv2.FILLED)
                self._move_mouse(cx, cy)


            # Clicking mode if index and middle fingers are up
            if fingers[0] == 1 and fingers[4] == 0:
                self._handle_clicking(img, fingers)

            # Hold mode if all fingers down
            if fingers.count(0) == 5:
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                self._hold_button_and_move(cx, cy)

            # Stop mode if all fingers up
            if fingers.count(1) == 5:
                self.mouse.release(Button.left)

            # Scroll mode if only pinky use
            if fingers[0] == 0 and fingers.count(1) == 4:
                self._handle_scrolling(landmarksList[20][2])

        return img

    def _move_mouse(self, x1, y1):
        x3 = np.interp(x1, (self.frameReduction, (self.wCam - self.frameReduction)), (0, self.wScreen))
        y3 = np.interp(y1, (
        self.frameReduction + self.adapterForCam, (self.hCam - self.frameReduction + self.adapterForCam)),
                       (0, self.hScreen))

        self.cLocX = self.pLocX + (x3 - self.pLocX) / self.smoothening
        self.cLocY = self.pLocY + (y3 - self.pLocY) / self.smoothening

        self.mouse.position = [(self.wScreen - self.cLocX), self.cLocY]
        self.pLocX, self.pLocY = self.cLocX, self.cLocY

    def _handle_clicking(self, img, fingers):
        lengthMB, img, lineInfoIM = self.handDetector.findDistance(12, 11, img)
        lengthIB, img, lineInfoIB = self.handDetector.findDistance(8, 7, img)



        if not self.LeftButtonPressed and lengthIB < 10:
            self.mouse.click(Button.left, 1)
            self.RightButtonPressed, self.LeftButtonPressed = False, True
        elif not self.RightButtonPressed and lengthMB < 10:
            self.mouse.click(Button.right, 1)
            self.RightButtonPressed, self.LeftButtonPressed = True, False

        self.clickSmother = 0

    def _hold_button_and_move(self, cx, cy):
        if not self.LeftButtonPressed:
            self.mouse.press(Button.left)
            self.LeftButtonPressed = True
        self._move_mouse(cx, cy)

    def _handle_scrolling(self, y):

        if y < self.centerPoint - 20:
            if self.scroll_direction != 1:
                self.scroll_direction = 1
                self.scrolling_mode = True
        elif y > self.centerPoint + 20:
            if self.scroll_direction != -1:
                self.scroll_direction = -1
                self.scrolling_mode = True
        else:
            self.scroll_direction = 0
            self.scrolling_mode = False


        if self.scrolling_mode:
            if self.scroll_direction == 1:
                self.mouse.scroll(0, 0.2)  # Scroll up
            elif self.scroll_direction == -1:
                self.mouse.scroll(0, -0.2)  # Scroll down


def main():
    wCam, hCam = 640, 360
    cap = cv2.VideoCapture(0)
    cap.set(3, wCam)
    cap.set(4, hCam)

    handControl = HandControl(wCam, hCam)

    pTime = 0

    while True:
        success, img = cap.read()
        if not success:
            break

        img = handControl.process_frame(img)

        # FPS calculation
        cTime = time.time()
        fps = 1 / (cTime - pTime)
        pTime = cTime

        cv2.putText(img, f"FPS: {int(fps)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Display
        cv2.imshow("Hand Control", img)
        if cv2.waitKey(1) & 0xFF == ord('q') or keyboard.is_pressed("space"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
