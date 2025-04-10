import cv2
import mediapipe as mp
import math


class HandDetector:
    def __init__(self, mode = False, max_hands = 2, model_complexity=1,
                 detection_con = 0.5, track_con = 0.5):
        # Settings for mediapipe
        self.mode = mode # Setup stream
        self.max_hands = max_hands
        self.model_complexity = model_complexity # AI model
        self.detection_con = detection_con # Confidence in detection
        self.track_con = track_con # Confidence in capture

        # Init only Mediapipe hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            self.mode,
            self.max_hands,
            self.model_complexity,
            self.detection_con,
            self.track_con)

        self.mp_draw = mp.solutions.drawing_utils # Visualization of bones

        self.tip_ids = [4, 8, 12, 16, 20] # Fingertips
        # 4 - thumb
        # 8 - index
        # 12 - middle
        # 16 - ring
        # 20 - pinky

        self.lm_list = [] # List of landmarks

        self.results = None # Frame to process

    def find_hands(self, img, draw = True):
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) # Convert from BGR to RGB for Mediapipe

        self.results = self.hands.process(img_rgb) # Processing frame

        # Rendering hands
        if self.results.multi_hand_landmarks:
            for hand_lms in self.results.multi_hand_landmarks:
                if draw:
                    self.mp_draw.draw_landmarks(img, hand_lms, self.mp_hands.HAND_CONNECTIONS)

        return img

    def find_position(self, img, draw=True):
        hands_data = []

        if self.results.multi_hand_landmarks and self.results.multi_handedness:
            # Iterating over detected hands
            for hand_landmarks, handedness in zip(self.results.multi_hand_landmarks,
                                                  self.results.multi_handedness):
                hand_info = {
                    "landmarks": [],
                    "label": handedness.classification[0].label.lower()  # Determining the type of hand
                                                                        # (left or right)
                }

                # Convert from coordinates to pixels
                for id, lm in enumerate(hand_landmarks.landmark):
                    h, w, _ = img.shape
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    hand_info["landmarks"].append([id, cx, cy])

                    if draw:
                        cv2.circle(img, (cx, cy), 7, (255, 0, 0), cv2.FILLED)
                hands_data.append(hand_info)

        return hands_data

    def fingers_up(self, landmarks=None):
        if landmarks is None:
            if not hasattr(self, 'lm_list') or not self.lm_list:
                return []
            landmarks = self.lm_list

        fingers = []

        # for thumb
        if landmarks[self.tip_ids[0]][1] > landmarks[self.tip_ids[0] - 1][1]:
            fingers.append(1) # Finger is up
        else:
            fingers.append(0) # Finger is down

        # for 2-5 fingers
        for id in range(1, 5):
            if landmarks[self.tip_ids[id]][2] < landmarks[self.tip_ids[id] - 2][2]:
                fingers.append(1)
            else:
                fingers.append(0)

        return fingers

    def find_distance(self, p1, p2, img, draw=True, r=15, t=3):
        if not hasattr(self, 'lm_list') or len(self.lm_list) == 0:
            return 0, img, [0,0,0,0,0,0]

        x1, y1 = self.lm_list[p1][1], self.lm_list[p1][2]
        x2, y2 = self.lm_list[p2][1], self.lm_list[p2][2]

        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        if draw:
            # The line between the points
            cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), t)
            # The points
            cv2.circle(img, (x1, y1), r, (255, 0, 255), cv2.FILLED)
            cv2.circle(img, (x2, y2), r, (255, 0, 255), cv2.FILLED)
            # The center point
            cv2.circle(img, (cx, cy), r, (0, 0, 255), cv2.FILLED)

        length = math.hypot(x2 - x1, y2 - y1)
        return length, img, [x1, y1, x2, y2, cx, cy]
