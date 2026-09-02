import cv2
import pyautogui
from cvzone.HandTrackingModule import HandDetector
import time

# 웹캠 초기화
cap = cv2.VideoCapture(0)
cap.set(3, 640)  # 카메라 너비
cap.set(4, 480)  # 카메라 높이

# 손 추적기 초기화
detector = HandDetector(maxHands=1, detectionCon=0.8)

# 화면 해상도 가져오기
#screen_w, screen_h = pyautogui.size()
screen_w, screen_h = 3840, 2160
print(f"[INFO] 화면 해상도: {screen_w}x{screen_h}")

# 시작 후 3초 기다렸다가 브라우저 포커스 주기
time.sleep(3)
pyautogui.moveTo(2803, 846)
pyautogui.click()

# 클릭 딜레이 제어용
click_cooldown = 1  # 초
last_click_time = time.time() - click_cooldown

while True:
    success, img = cap.read()
    if not success:
        break

    hands, img = detector.findHands(img)

    if hands:
        hand = hands[0]
        lmList = hand["lmList"]
        fingers = detector.fingersUp(hand)

        # 손바닥 중심 기준으로 커서 이동
        cx, cy = hand['center']  # 손 중심 좌표 (카메라 기준)

        # 화면 좌표로 변환
        x_offset = -1000
        cam_w, cam_h = 640, 480  # 카메라 해상도 기준
        cursor_x = int((cx / cam_w) * screen_w) + x_offset
        cursor_y = int((cy / cam_h) * screen_h)
        pyautogui.moveTo(cursor_x, cursor_y)

        # 모든 손가락이 접히면 클릭 (주먹)
        if fingers == [0, 0, 0, 0, 0]:
            now = time.time()
            if now - last_click_time >= click_cooldown:
                pyautogui.click()
                print("[CLICK] 주먹 감지! 클릭 실행")
                last_click_time = now

    cv2.imshow("Hand Mouse", img)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
