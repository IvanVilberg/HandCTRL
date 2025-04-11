import time
import cv2
import HandTrakingModule as htm
import numpy as np
import json
import os
import subprocess
import gc
from pynput.mouse import Button, Controller
from Xlib import display


class HandControl:
    def __init__(self, w_cam=640, h_cam=360, config_file="config.json"):
        self.w_cam, self.h_cam = w_cam, h_cam

        screen = display.Display().screen()
        self.w_screen, self.h_screen = screen.width_in_pixels, screen.height_in_pixels

        self.config = self._load_config(config_file)

        self.smoothening = self.config["settings"]["smoothening"]
        self.adapter_for_cam = self.config["settings"]["adapter_for_cam"]
        self.delay_button_max = self.config["settings"]["click_delay"]

        self.reduction_ratio = 0.3
        self.reduced_x1 = int(self.w_cam * self.reduction_ratio / 2)
        self.reduced_y1 = int(self.h_cam * self.reduction_ratio / 2)
        self.reduced_x2 = self.w_cam - self.reduced_x1
        self.reduced_y2 = self.h_cam - self.reduced_y1

        self.mouse = Controller()

        # Variables for smoothing motion
        self.p_loc_x, self.p_loc_y = 0, 0 # Previous points
        self.c_loc_x, self.c_loc_y = 0, 0 # Current points

        self.right_button_is_pressed = False
        self.left_button_is_pressed = False


        self.hand_detector = htm.HandDetector(max_hands=2)

        self.delay_button = 0

        self.center_point = h_cam // 2

        self.last_app_launch_time = 0
        self.app_launch_cooldown = 2

        self.prev_img = None # Previous frame
        self.frame_counter = 0

    def _load_config(self, config_file):
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Config file {config_file} not found")

        with open(config_file, 'r') as f:
            config = json.load(f)
        return config

    # Comparing fingers with patterns
    def _check_gesture(self, fingers, hand_type, gesture_name):
        try:
            gesture = self.config["gestures"][hand_type][gesture_name]

            if "fingers_up" in gesture:
                if fingers == gesture["fingers_up"]:
                    return True

        except KeyError:
            print(f"Жест {gesture_name} не найден для {hand_type}")
            return False

    def _launch_application(self, command):
        try:
            subprocess.Popen(command.split(), shell=True)
            return True

        except Exception as e:
            print(f"Ошибка запуска: {e}")
            return False

    # Delay between gestures
    def _delay(self):
        self.delay_button += 1
        if self.delay_button > self.delay_button_max:
            self.delay_button = 0
            self.left_button_is_pressed = False
            self.right_button_is_pressed = False

    def _right_hand(self, img, landmarks_list):
        if not landmarks_list:
            return img

        fingers = self.hand_detector.fingers_up(landmarks_list)
        hand_type = "right_hand"

        if self._check_gesture(fingers, hand_type, "move_mouse"):
            x1, y1 = landmarks_list[8][1], landmarks_list[8][2]
            self._move_mouse(x1, y1)
            cv2.putText(img, "MOVE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

        elif self._check_gesture(fingers, hand_type, "left_one_click"):
            if not self.left_button_is_pressed and self.delay_button == 0:
                self.mouse.click(Button.left, 1)
                self.left_button_is_pressed = True
            else:
                self._delay()

        elif self._check_gesture(fingers, hand_type, "left_double_click"):
            if not self.left_button_is_pressed and self.delay_button == 0:
                self.mouse.click(Button.left, 2)
                self.left_button_is_pressed = True
            else:
                self._delay()

        elif self._check_gesture(fingers, hand_type, "right_click"):
            if not self.right_button_is_pressed and self.delay_button == 0:
                self.mouse.click(Button.right, 1)
                self.right_button_is_pressed = True
            else:
                self._delay()

        elif self._check_gesture(fingers, hand_type, "scroll_up"):
            self.mouse.scroll(0, 1)
            cv2.putText(img, "SCROLL UP", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            time.sleep(0.1)

        elif self._check_gesture(fingers, hand_type, "scroll_down"):
            self.mouse.scroll(0, -1)
            cv2.putText(img, "SCROLL DOWN", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)
            time.sleep(0.1)

        elif self._check_gesture(fingers, hand_type, "hold_and_move"):
            self.mouse.press(Button.left)
            self.left_button_is_pressed = True
            cv2.putText(img, "HOLD", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

        elif self._check_gesture(fingers, hand_type, "release"):
            self.mouse.release(Button.left)
            self.left_button_is_pressed = False
            cv2.putText(img, "RELEASE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        return img


    def _left_hand(self, img, landmarks_list):
        try:
            if not landmarks_list:
                return img

            fingers = self.hand_detector.fingers_up(landmarks_list)
            current_time = time.time()

            for id, cx, cy in landmarks_list[:21]:
                cv2.circle(img, (cx, cy), 7, (0, 0, 255), cv2.FILLED)

            if current_time - self.last_app_launch_time > self.app_launch_cooldown:
                for app_name, gesture_config in self.config["gestures"]["left_hand"]["app_launch"]["gestures"].items():
                    if fingers == gesture_config["fingers_up"]:
                        if self._launch_application(gesture_config["command"]):
                            cv2.putText(img, f"Launching {app_name}", (50, 80),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                        self.last_app_launch_time = current_time
                        break

        except Exception as e:
            print(f"Ошибка обработки левой руки: {e}")
        return img


    def _move_mouse(self, x1, y1):
        # Convert coordinates from camera to display
        x3 = np.interp(x1, (self.reduced_x1, self.reduced_x2), (0, self.w_screen))
        y3 = np.interp(y1, (
            self.reduced_y1 + self.adapter_for_cam,
            self.reduced_y2 + self.adapter_for_cam
        ), (0, self.h_screen))

        # Smoothening
        self.c_loc_x = self.p_loc_x + (x3 - self.p_loc_x) / self.smoothening
        self.c_loc_y = self.p_loc_y + (y3 - self.p_loc_y) / self.smoothening

        # Setup mouse position
        self.mouse.position = [(self.w_screen - self.c_loc_x), self.c_loc_y]

        self.p_loc_x, self.p_loc_y = self.c_loc_x, self.c_loc_y

    def _process_frame(self, img):
        try:
            if hasattr(self, 'prev_img'):
                del self.prev_img
            self.prev_img = img.copy()

            # Garbage collection
            self.frame_counter += 1
            if self.frame_counter % 30 == 0:
                gc.collect()

            img = self.hand_detector.find_hands(img) # Detection hands
            hands_data = self.hand_detector.find_position(img, draw=False) # Capture hands

            for hand in hands_data:
                landmarks = hand["landmarks"]
                hand_label = hand["label"]

                # Inversion of hands due to camera mirroring
                if hand_label == "left":
                    self._right_hand(img, landmarks)
                elif hand_label == "right":
                    self._left_hand(img, landmarks)

            # Gesture capture area
            cv2.rectangle(
                img,
                (self.reduced_x1, self.reduced_y1),
                (self.reduced_x2, self.reduced_y2),
                (0, 255, 0), 2
            )

            return img

        except Exception as e:
            print(f"Ошибка обработки кадра: {e}")
            return img



def main():
    w_cam, h_cam = 640, 360
    cap = cv2.VideoCapture(0)
    cap.set(3, w_cam)
    cap.set(4, h_cam)

    hand_contol = HandControl(w_cam, h_cam)

    while True:
        success, img = cap.read()
        if not success:
            break

        img = hand_contol._process_frame(img)


        cv2.putText(img, "Left: Apps | Right: Mouse", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)


        cv2.imshow("Hand Control", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Freeing up resources
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()