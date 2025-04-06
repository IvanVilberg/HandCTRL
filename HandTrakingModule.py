import cv2
import mediapipe as mp
import time
import keyboard
import math


class HandDetector:
    def __init__(self, mode = False, maxHands = 2, modelComplexity=1,
                 detectionCon = 0.5, trackCon = 0.5):
        self.mode = mode
        self.maxHands = maxHands
        self.modelComplexity = modelComplexity
        self.detectionCon = detectionCon
        self.trackCon = trackCon

        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(
            self.mode,
            self.maxHands,
            self.modelComplexity,
            self.detectionCon,
            self.trackCon)
        self.mpDraw = mp.solutions.drawing_utils
        self.tipIds = [4, 8, 12, 16, 20]
        self.lm_list = []

    def find_hands(self, img, draw = True):
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(imgRGB)
        # print(results.multi_hand_landmarks)

        if self.results.multi_hand_landmarks:
            for handLms in self.results.multi_hand_landmarks:
                if draw:
                    self.mpDraw.draw_landmarks(img, handLms, self.mpHands.HAND_CONNECTIONS)

        return img

    def findPosition(self, img, handNo=0, draw=True, allHands=False):
            if allHands:
                hands_data = []
                if self.results.multi_hand_landmarks:
                    for hand in self.results.multi_hand_landmarks:
                        single_hand = []
                        for id, lm in enumerate(hand.landmark):
                            h, w, c = img.shape
                            cx, cy = int(lm.x * w), int (lm.y * h)
                            single_hand.append([id, cx, cy])
                            if draw:
                                cv2.circle(img, (cx, cy), 7, (255, 0, 0), cv2.FILLED)
                        hands_data.append(single_hand)
                return hands_data
            else:
                self.lm_list = []
                if self.results.multi_hand_landmarks:
                    myHand = self.results.multi_hand_landmarks[handNo]
                    for id, lm in enumerate(myHand.landmark):
                        h, w, c = img.shape
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        self.lm_list.append([id, cx, cy])
                        if draw:
                            cv2.circle(img, (cx, cy), 7, (255, 0, 0), cv2.FILLED)
                return self.lm_list

    def fingers_up(self, landmarks=None):
        if landmarks is None:
            if not hasattr(self, 'lm_list') or not self.lm_list:
                return []
            landmarks = self.lm_list

        fingers = []
        # for thumb
        if landmarks[self.tipIds[0]][1] > landmarks[self.tipIds[0] - 1][1]:
            fingers.append(1)
        else:
            fingers.append(0)

        # for 2-5 fingers
        for id in range(1, 5):
            if landmarks[self.tipIds[id]][2] < landmarks[self.tipIds[id] - 2][2]:
                fingers.append(1)
            else:
                fingers.append(0)
        return fingers

    def findDistance(self, p1, p2, img, draw=True, r=15, t=3):
        if not hasattr(self, 'lm_list') or len(self.lm_list) == 0:
            return 0, img, [0,0,0,0,0,0]

        x1, y1 = self.lm_list[p1][1], self.lm_list[p1][2]
        x2, y2 = self.lm_list[p2][1], self.lm_list[p2][2]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        if draw:
            cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), t)
            cv2.circle(img, (x1, y1), r, (255, 0, 255), cv2.FILLED)
            cv2.circle(img, (x2, y2), r, (255, 0, 255), cv2.FILLED)
            cv2.circle(img, (cx, cy), r, (0, 0, 255), cv2.FILLED)

        length = math.hypot(x2 - x1, y2 - y1)
        return length, img, [x1, y1, x2, y2, cx, cy]
