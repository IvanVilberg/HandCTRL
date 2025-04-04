import cv2
import HandTrakingModule as htm
import numpy as np
import json
import os
from pynput.mouse import Button, Controller
from Xlib import display
# For Windows
# import ctypes


class HandControl:
    def __init__(self, w_cam=640, h_cam=360, config_file="config.json"):
        # Set cam resolution
        self.wCam, self.hCam = w_cam, h_cam

        # For Windows
        # self.user32 = ctypes.windll.user32
        # self.wScreen, self.hScreen = self.user32.GetSystemMetrics(0), self.user32.GetSystemMetrics(1)

        screen = display.Display().screen()
        self.wScreen, self.hScreen = screen.width_in_pixels, screen.height_in_pixels


        # Settings from config file
        self.config = self._load_config(config_file)

        self.smoothening = self.config["settings"]["smoothening"]
        self.frameReduction = int(self.wCam * self.config["settings"]["frame_reduction"])
        self.adapterForCam = self.config["settings"]["adapter_for_cam"]
        self.delayButtonMax = self.config["settings"]["click_delay"]

        self.mouse = Controller()

        # Smoothening variables
        self.pLocX, self.pLocY = 0, 0
        self.cLocX, self.cLocY = 0, 0
        self.clickSmother = 0
        self.RightButtonPressed = False
        self.LeftButtonPressed = False

        self.handDetector = htm.HandDetector(maxHands=1)

        self.delayButton = 0
        self.centerPoint = h_cam // 2
        self.scroll_direction = 0


    # Load config file in the program
    def _load_config(self, config_file):
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Config file {config_file} not found")

        with open(config_file, 'r') as f:
            config = json.load(f)
        return config

    # Function for check gestures with config
    def _check_gesture(self, fingers, gesture_name):
        gesture = self.config["gestures"][gesture_name]

        if "fingers_up" in gesture:
            if fingers == gesture["fingers_up"]:
                return True

        if "min_fingers_up" in gesture and "max_finges_up" in gesture:
            fingers_up_count = sum(fingers)
            if gesture["min_fingers_up"] <= fingers_up_count <= gesture["max_fingers_up"]:
                return True

        return False


    def process_frame(self, img):
        img = self.handDetector.findHand(img)
        landmarks_list = self.handDetector.findPosition(img, draw=False)

        if not self.delayButton == 30 and not (self.RightButtonPressed or self.LeftButtonPressed):
            self.delayButton += 1
        elif self.delayButton == self.delayButtonMax:
            self.RightButtonPressed, self.LeftButtonPressed = False, False


        if len(landmarks_list) != 0:
            fingers = self.handDetector.fingersUp()

            # Draw rectangle for mouse control
            cv2.rectangle(img, (self.frameReduction, self.frameReduction + self.adapterForCam),
                          ((self.wCam - self.frameReduction), (self.hCam - self.frameReduction + self.adapterForCam)),
                          (255, 0, 0), 2)

            # Move mouse if only index finger up
            if self._check_gesture(fingers, "move_mouse"):
                x1, y1 = landmarks_list[8][1], landmarks_list[8][2]
                x2, y2 = landmarks_list[12][1], landmarks_list[12][2]
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                cv2.circle(img, (cx, cy), 15, (255, 0, 255), cv2.FILLED)
                self._move_mouse(cx, cy)


            # Left click
            if self._check_gesture(fingers, "left_click"):
                gesture = self.config["gestures"]["left_click"]
                length, img, _ = self.handDetector.findDistance(
                    gesture["landmarks"][0], gesture["landmarks"][1], img)

                if not self.LeftButtonPressed and length < gesture["distance_threshold"]:
                    self.mouse.click(Button.left, 1)
                    self.RightButtonPressed, self.LeftButtonPressed = False, True
                self.clickSmother = 0

            # Right click
            if self._check_gesture(fingers, "right_click"):
                gesture = self.config["gestures"]["right_click"]
                length, img, _ = self.handDetector.findDistance(
                    gesture["landmarks"][0], gesture["landmarks"][1], img)

                if not self.RightButtonPressed and length < gesture ["distance_threshold"]:
                    self.mouse.click(Button.right, 1)
                    self.RightButtonPressed, self.LeftButtonPressed = True, False
                self.clickSmother = 0

            # Hold mode if all fingers down
            if self._check_gesture(fingers, "hold_and_move"):
                x1, y1 = landmarks_list[8][1], landmarks_list[8][2]
                x2, y2 = landmarks_list[12][1], landmarks_list[12][2]
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                if not self.LeftButtonPressed:
                    self.mouse.press(Button.left)
                    self.LeftButtonPressed = True
                self._move_mouse(cx, cy)


            if self._check_gesture(fingers, "release"):
                self.mouse.release(Button.left)

            if self._check_gesture(fingers, "scroll"):
                gesture = self.config["gestures"]["scroll"]
                y = landmarks_list[gesture["landmark"]][2]

                if y < self.centerPoint - gesture["scroll_threshold"]:
                    self.mouse.scroll(0, 1)
                elif y > self.centerPoint + gesture["scroll_threshold"]:
                    self.mouse.scroll(0, -1)

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
        scroll_threshold = 20

        if y < self.centerPoint - scroll_threshold:
            self.mouse.scroll(0, 1)  # Scroll up
        elif y > self.centerPoint + scroll_threshold:
            self.mouse.scroll(0, -1)  # Scroll down


def main():
    wCam, hCam = 640, 360
    cap = cv2.VideoCapture(0)
    cap.set(3, wCam)
    cap.set(4, hCam)

    handControl = HandControl(wCam, hCam)



    while True:
        success, img = cap.read()
        if not success:
            break

        img = handControl.process_frame(img)

        # Display
        cv2.imshow("Hand Control", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
