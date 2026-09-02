import cv2
import numpy as np
import requests
import time

# 서버 주소와 포트 설정
server_url = "http://192.168.1.4:7080/api/python"

# 특정 영역 내에서 지정된 색상 마스크의 비율을 계산하는 함수
def get_color_ratio(mask, region):
    mask_region = np.zeros_like(mask)
    cv2.fillPoly(mask_region, [region], 255)
    masked = cv2.bitwise_and(mask, mask_region)
    total_pixels = cv2.countNonZero(mask_region)
    color_pixels = cv2.countNonZero(masked)
    if total_pixels == 0:
        return 0
    return color_pixels / total_pixels

def detect_tangram_team_game():
    cap = cv2.VideoCapture(1)
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    boundary = (118, 185, 1798, 925)
    kernel = np.ones((5,5), np.uint8)
    
    # 빨간색의 HSV 범위 설정
    lower_red = np.array([0, 50, 50])
    upper_red = np.array([10, 255, 255])
    lower_red2 = np.array([170, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    
    # 파란색의 HSV 범위 설정
    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([130, 255, 255])

    # 노란색의 HSV 범위 설정
    lower_yellow = np.array([20, 50, 50])
    upper_yellow = np.array([40, 255, 255])

    # 초록색 범위 설정
    lower_green = np.array([35, 50, 50])
    upper_green = np.array([85, 255, 255])

    # Team 1 영역 설정 (왼쪽 절반)
    s_triangle_region_1_t1 = np.array([[548, 123], [388, 123], [388, 283]], np.int32).reshape((-1, 1, 2))
    s_triangle_region_2_t1 = np.array([[446, 779], [333, 892], [559, 892]], np.int32).reshape((-1, 1, 2))
    m_triangle_region_t1 = np.array([[479, 812], [639, 652], [639, 972]], np.int32).reshape((-1, 1, 2))
    l_triangle_region_1_t1 = np.array([[548, 123], [548, 451], [220, 451]], np.int32).reshape((-1, 1, 2))
    l_triangle_region_2_t1 = np.array([[548, 451], [220, 451], [220, 779]], np.int32).reshape((-1, 1, 2))
    rectangle_region_t1 = np.array([[388, 123], [388, 283], [220, 451], [220, 291]], np.int32).reshape((-1, 1, 2))
    square_region_t1 = np.array([[220, 779], [333, 666], [446, 779], [333, 892]], np.int32).reshape((-1, 1, 2))

    # Team 2 영역 설정 (오른쪽 절반으로 이동, x 좌표에 300 추가)
    s_triangle_region_1_t2 = np.array([[1367, 960], [1527, 960], [1527, 800]], np.int32).reshape((-1, 1, 2))
    s_triangle_region_2_t2 = np.array([[1469, 304], [1582, 191], [1356, 191]], np.int32).reshape((-1, 1, 2))
    m_triangle_region_t2 = np.array([[1436, 271], [1276, 111], [1276, 431]], np.int32).reshape((-1, 1, 2))
    l_triangle_region_1_t2 = np.array([[1367, 960], [1367, 632], [1695, 632]], np.int32).reshape((-1, 1, 2))
    l_triangle_region_2_t2 = np.array([[1367, 632], [1695, 632], [1695, 304]], np.int32).reshape((-1, 1, 2))
    rectangle_region_t2 = np.array([[1527, 960], [1527, 800], [1695, 632], [1695, 792]], np.int32).reshape((-1, 1, 2))
    square_region_t2 = np.array([[1695, 304], [1582, 417], [1469, 304], [1582, 191]], np.int32).reshape((-1, 1, 2))

    last_sent_time = time.time()  # 마지막 전송 시간 초기화

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 색상 마스크 생성
        mask_red1 = cv2.inRange(hsv, lower_red, upper_red)
        mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask_red = cv2.bitwise_or(mask_red1, mask_red2)
        mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
        mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
        mask_green = cv2.inRange(hsv, lower_green, upper_green)
        
        mask = cv2.bitwise_or(mask_red, mask_blue)
        mask = cv2.bitwise_or(mask, mask_yellow)
        mask = cv2.bitwise_or(mask, mask_green)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # Team 1 조건 확인
        red_triangle_inside_1_t1 = get_color_ratio(mask_red, s_triangle_region_1_t1) >= 0.8
        red_triangle_inside_2_t1 = get_color_ratio(mask_red, s_triangle_region_2_t1) >= 0.8
        yellow_triangle_inside_t1 = get_color_ratio(mask_yellow, m_triangle_region_t1) >= 0.8
        green_triangle_inside_1_t1 = get_color_ratio(mask_green, l_triangle_region_1_t1) >= 0.8
        green_triangle_inside_2_t1 = get_color_ratio(mask_green, l_triangle_region_2_t1) >= 0.8
        blue_rectangle_inside_1_t1 = get_color_ratio(mask_blue, rectangle_region_t1) >= 0.8
        blue_rectangle_inside_2_t1 = get_color_ratio(mask_blue, square_region_t1) >= 0.8

        # Team 2 조건 확인
        red_triangle_inside_1_t2 = get_color_ratio(mask_red, s_triangle_region_1_t2) >= 0.8
        red_triangle_inside_2_t2 = get_color_ratio(mask_red, s_triangle_region_2_t2) >= 0.8
        yellow_triangle_inside_t2 = get_color_ratio(mask_yellow, m_triangle_region_t2) >= 0.8
        green_triangle_inside_1_t2 = get_color_ratio(mask_green, l_triangle_region_1_t2) >= 0.8
        green_triangle_inside_2_t2 = get_color_ratio(mask_green, l_triangle_region_2_t2) >= 0.8
        blue_rectangle_inside_1_t2 = get_color_ratio(mask_blue, rectangle_region_t2) >= 0.8
        blue_rectangle_inside_2_t2 = get_color_ratio(mask_blue, square_region_t2) >= 0.8

        # Team 1 데이터 준비 (문자열 형태: "1,1,1,1,0,0,0")
        team1_conditions_list = [
            1 if red_triangle_inside_1_t1 else 0,
            1 if red_triangle_inside_2_t1 else 0,
            1 if yellow_triangle_inside_t1 else 0,
            1 if green_triangle_inside_1_t1 else 0,
            1 if green_triangle_inside_2_t1 else 0,
            1 if blue_rectangle_inside_1_t1 else 0,
            1 if blue_rectangle_inside_2_t1 else 0
        ]
        team1_conditions_str = ",".join(map(str, team1_conditions_list))

        # Team 2 데이터 준비 (문자열 형태: "1,1,1,1,0,0,0")
        team2_conditions_list = [
            1 if red_triangle_inside_1_t2 else 0,
            1 if red_triangle_inside_2_t2 else 0,
            1 if yellow_triangle_inside_t2 else 0,
            1 if green_triangle_inside_1_t2 else 0,
            1 if green_triangle_inside_2_t2 else 0,
            1 if blue_rectangle_inside_1_t2 else 0,
            1 if blue_rectangle_inside_2_t2 else 0
        ]
        team2_conditions_str = ",".join(map(str, team2_conditions_list))

        # 서버로 보낼 데이터 준비
        # 여기 수정함함
        conditions = team1_conditions_str|team2_conditions_str


        # 100ms마다 데이터 전송
        current_time = time.time()
        if current_time - last_sent_time >= 0.1:  # 100ms(0.1초) 간격 확인
            try:
                print(f"Sending data: {conditions}")  # 전송 데이터 확인
                response = requests.post(server_url, json=conditions, timeout=5)
                if response.status_code == 200:
                    print(f"서버로 데이터 전송 성공! 보낸 데이터: {conditions}")
                else:
                    print(f"서버 전송 실패: 상태 코드 {response.status_code}, 응답: {response.text}")
                last_sent_time = current_time  # 마지막 전송 시간 업데이트
            except requests.exceptions.RequestException as e:
                print(f"서버 전송 오류: {e}")

        # 영역 그리기
        cv2.rectangle(frame, (boundary[0], boundary[1]), (boundary[2], boundary[3]), (0, 255, 0), 2)
        
        # Team 1 영역
        cv2.polylines(frame, [s_triangle_region_1_t1], isClosed=True, color=(0, 0, 255), thickness=2)
        cv2.polylines(frame, [s_triangle_region_2_t1], isClosed=True, color=(0, 0, 255), thickness=2)
        cv2.polylines(frame, [m_triangle_region_t1], isClosed=True, color=(0, 255, 255), thickness=2)
        cv2.polylines(frame, [l_triangle_region_1_t1], isClosed=True, color=(0, 255, 0), thickness=2)
        cv2.polylines(frame, [l_triangle_region_2_t1], isClosed=True, color=(0, 255, 0), thickness=2)
        cv2.polylines(frame, [rectangle_region_t1], isClosed=True, color=(255, 0, 0), thickness=2)
        cv2.polylines(frame, [square_region_t1], isClosed=True, color=(255, 0, 0), thickness=2)

        # Team 2 영역
        cv2.polylines(frame, [s_triangle_region_1_t2], isClosed=True, color=(0, 0, 255), thickness=2)
        cv2.polylines(frame, [s_triangle_region_2_t2], isClosed=True, color=(0, 0, 255), thickness=2)
        cv2.polylines(frame, [m_triangle_region_t2], isClosed=True, color=(0, 255, 255), thickness=2)
        cv2.polylines(frame, [l_triangle_region_1_t2], isClosed=True, color=(0, 255, 0), thickness=2)
        cv2.polylines(frame, [l_triangle_region_2_t2], isClosed=True, color=(0, 255, 0), thickness=2)
        cv2.polylines(frame, [rectangle_region_t2], isClosed=True, color=(255, 0, 0), thickness=2)
        cv2.polylines(frame, [square_region_t2], isClosed=True, color=(255, 0, 0), thickness=2)

        # 상태 텍스트 표시 (Team 1)
        cv2.putText(frame, "Team 1", (50, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(frame, f"Red1: {red_triangle_inside_1_t1}", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if red_triangle_inside_1_t1 else (0, 0, 255), 2)
        cv2.putText(frame, f"Red2: {red_triangle_inside_2_t1}", (50, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if red_triangle_inside_2_t1 else (0, 0, 255), 2)
        cv2.putText(frame, f"Yellow: {yellow_triangle_inside_t1}", (50, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if yellow_triangle_inside_t1 else (0, 0, 255), 2)
        cv2.putText(frame, f"Green1: {green_triangle_inside_1_t1}", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if green_triangle_inside_1_t1 else (0, 0, 255), 2)
        cv2.putText(frame, f"Green2: {green_triangle_inside_2_t1}", (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if green_triangle_inside_2_t1 else (0, 0, 255), 2)
        cv2.putText(frame, f"Blue1: {blue_rectangle_inside_1_t1}", (50, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if blue_rectangle_inside_1_t1 else (0, 0, 255), 2)
        cv2.putText(frame, f"Blue2: {blue_rectangle_inside_2_t1}", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if blue_rectangle_inside_2_t1 else (0, 0, 255), 2)

        # 상태 텍스트 표시 (Team 2)
        cv2.putText(frame, "Team 2", (350, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(frame, f"Red1: {red_triangle_inside_1_t2}", (350, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if red_triangle_inside_1_t2 else (0, 0, 255), 2)
        cv2.putText(frame, f"Red2: {red_triangle_inside_2_t2}", (350, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if red_triangle_inside_2_t2 else (0, 0, 255), 2)
        cv2.putText(frame, f"Yellow: {yellow_triangle_inside_t2}", (350, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if yellow_triangle_inside_t2 else (0, 0, 255), 2)
        cv2.putText(frame, f"Green1: {green_triangle_inside_1_t2}", (350, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if green_triangle_inside_1_t2 else (0, 0, 255), 2)
        cv2.putText(frame, f"Green2: {green_triangle_inside_2_t2}", (350, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if green_triangle_inside_2_t2 else (0, 0, 255), 2)
        cv2.putText(frame, f"Blue1: {blue_rectangle_inside_1_t2}", (350, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if blue_rectangle_inside_1_t2 else (0, 0, 255), 2)
        cv2.putText(frame, f"Blue2: {blue_rectangle_inside_2_t2}", (350, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if blue_rectangle_inside_2_t2 else (0, 0, 255), 2)

        cv2.imshow("Tangram Team Game", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    detect_tangram_team_game()
