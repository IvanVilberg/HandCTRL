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

        self.handDetector = htm.HandDetector(maxHands=2)

        self.delayButton = 0
        self.centerPoint = h_cam // 2
        self.scroll_direction = 0
        self.last_app_launch_time = 0
        self.app_launch_cooldown = 2

        self.prev_img = None
        self.frame_counter = 0

    def __del__(self):
        if hasattr(self, 'handDetector'):
            del self.handDetector
        gc.collect()

    # Load config file in the program
    def _load_config(self, config_file):
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Config file {config_file} not found")

        with open(config_file, 'r') as f:
            config = json.load(f)
        return config

    # Function for check gestures with config
    def _check_gesture(self, fingers, hand_type, gesture_name):
        try:
            gesture = self.config["gestures"][hand_type][gesture_name]
            if "fingers_up" in gesture:
                if fingers == gesture["fingers_up"]:
                    return True

            if all(k in gesture for k in ["min_fingers_up", "max_fingers_up"]):
                fingers_count = sum(fingers)
                return gesture["min_fingers_up"] <= fingers_count <= gesture["max_fingers_up"]

            return False
        except KeyError:
            print(f"Жест {gesture_name} не найден для {hand_type}")
            return False

    # Start application
    def _launch_application(self, command):
        try:
            subprocess.Popen(command.split(), shell=True)
            return True
        except Exception as e:
            print(f"Ошибка запуска: {e}")
            return False

    def _right_hand(self, img, landmarks_list):
        if not landmarks_list:
            return img

        fingers = self.handDetector.fingers_up(landmarks_list)

        # Движение мыши - подняты указательный и средний пальцы
        if fingers == [0, 1, 1, 0, 0]:
            x1, y1 = landmarks_list[8][1], landmarks_list[8][2]  # Указательный
            x2, y2 = landmarks_list[12][1], landmarks_list[12][2]  # Средний
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            self._move_mouse(cx, cy)
            cv2.putText(img, "MOVE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

        # Левый клик - подняты большой и указательный пальцы
        elif fingers == [1, 1, 0, 0, 0]:
            self.mouse.click(Button.left, 1)
            cv2.putText(img, "LEFT CLICK", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Правый клик - подняты 3 пальца
        elif fingers == [1, 1, 1, 0, 0]:
            self.mouse.click(Button.right, 1)
            cv2.putText(img, "RIGHT CLICK", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Удержание - кулак
        elif fingers == [0, 0, 0, 0, 0]:
            if not self.LeftButtonPressed:
                self.mouse.press(Button.left)
                self.LeftButtonPressed = True
            cv2.putText(img, "HOLD", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

        # Отпускание - ладонь
        elif fingers == [1, 1, 1, 1, 1]:
            if self.LeftButtonPressed:
                self.mouse.release(Button.left)
                self.LeftButtonPressed = False
            cv2.putText(img, "RELEASE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        return img

    def _left_hand(self, img, landmarks_list):
        try:
            if not landmarks_list:
                return img

            fingers = self.handDetector.fingers_up(landmarks_list)
            current_time = time.time()

            # Отрисовка маркеров
            for id, cx, cy in landmarks_list[:21]:  # Ограничение 21 точки
                cv2.circle(img, (cx, cy), 7, (0, 0, 255), cv2.FILLED)

            # Проверка жестов запуска
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
        x3 = np.interp(x1, (self.frameReduction, (self.wCam - self.frameReduction)), (0, self.wScreen))
        y3 = np.interp(y1, (
        self.frameReduction + self.adapterForCam, (self.hCam - self.frameReduction + self.adapterForCam)),
                       (0, self.hScreen))

        self.cLocX = self.pLocX + (x3 - self.pLocX) / self.smoothening
        self.cLocY = self.pLocY + (y3 - self.pLocY) / self.smoothening

        self.mouse.position = [(self.wScreen - self.cLocX), self.cLocY]
        self.pLocX, self.pLocY = self.cLocX, self.cLocY

    def _process_frame(self, img):
        try:
            # Освобождаем память от предыдущего кадра
            if hasattr(self, 'prev_img'):
                del self.prev_img
            self.prev_img = img.copy()

            # Периодическая сборка мусора
            self.frame_counter += 1
            if self.frame_counter % 30 == 0:
                gc.collect()

            # Сначала находим руки на изображении
            img = self.handDetector.find_hands(img)

            # Затем получаем позиции landmarks
            hands_data = self.handDetector.findPosition(img, draw=False, allHands=True)

            # Обрабатываем не более 2 рук
            max_hands = min(len(hands_data), 2)
            for i in range(max_hands):
                if i == 0:  # Правая рука
                    self._right_hand(img, hands_data[i])
                else:  # Левая рука
                    self._left_hand(img, hands_data[i])

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

        # Подпись для режима левой руки
        cv2.putText(img, "Left: Apps | Right: Mouse", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # Display
        cv2.imshow("Hand Control", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()