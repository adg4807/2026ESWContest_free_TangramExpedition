import cv2
import numpy as np
import requests

# 서버 주소와 포트 설정
server_url = "http://192.168.1.19:7080/api/python"

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

def detect_tangram():
    cap = cv2.VideoCapture(0)
    
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


    # 작은 삼각형 영역 설정(red) 270
    s_triangle_region_1 = np.array([[340*2, 0], [340*2, 170*2], [255*2, 85*2]], np.int32)
    s_triangle_region_1 = s_triangle_region_1.reshape((-1, 1, 2))
    s_triangle_region_2 = np.array([[170*2, 170*2], [255*2, 255*2], [85*2, 255*2]], np.int32)
    s_triangle_region_2 = s_triangle_region_2.reshape((-1, 1, 2))

    # 중간 삼각형 영역 설정(yellow)
    m_triangle_region = np.array([[340*2, 170*2], [340*2, 340*2], [170*2, 340*2]], np.int32)
    m_triangle_region = m_triangle_region.reshape((-1, 1, 2))

    # 큰 삼각형 영역 설정(green)
    l_triangle_region_1 = np.array([[0, 0], [340*2, 0], [170*2, 170*2]], np.int32)
    l_triangle_region_1 = l_triangle_region_1.reshape((-1, 1, 2))
    l_triangle_region_2 = np.array([[0, 0], [0, 340*2], [170*2, 170*2]], np.int32)
    l_triangle_region_2 = l_triangle_region_2.reshape((-1, 1, 2))
    
    # 평행사변형 영역 설정(blue)
    rectangle_region = np.array([[0, 340*2], [170*2, 340*2], [255*2, 255*2], [85*2, 255*2]], np.int32)
    rectangle_region = rectangle_region.reshape((-1, 1, 2))

    # 정사각형 영역 설정(blue)
    square_region = np.array([[340*2, 170*2], [255*2, 85*2], [170*2, 170*2], [255*2, 255*2]], np.int32)
    square_region = square_region.reshape((-1, 1, 2))


    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 빨간색, 파란색, 노란색, 초록색, 분홍색 마스크 생성
        mask_red1 = cv2.inRange(hsv, lower_red, upper_red)
        mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask_red = cv2.bitwise_or(mask_red1, mask_red2)      
        mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
        mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
        mask_green = cv2.inRange(hsv, lower_green, upper_green)

        
        # 모든 색상 마스크 결합
        mask = cv2.bitwise_or(mask_red, mask_blue)
        mask = cv2.bitwise_or(mask, mask_yellow)
        mask = cv2.bitwise_or(mask, mask_green)
        
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        cv2.rectangle(frame, (boundary[0], boundary[1]), (boundary[2], boundary[3]), (0, 255, 0), 2)
        cv2.polylines(frame, [s_triangle_region_1], isClosed=True, color=(0, 0, 255), thickness=2)
        cv2.polylines(frame, [s_triangle_region_2], isClosed=True, color=(0, 0, 255), thickness=2)
        cv2.polylines(frame, [m_triangle_region], isClosed=True, color=(0, 255, 255), thickness=2)
        cv2.polylines(frame, [l_triangle_region_1], isClosed=True, color=(0, 255, 0), thickness=2)
        cv2.polylines(frame, [l_triangle_region_2], isClosed=True, color=(0, 255, 0), thickness=2)
        cv2.polylines(frame, [rectangle_region], isClosed=True, color=(255, 0, 0), thickness=2)
        cv2.polylines(frame, [square_region], isClosed=True, color=(255, 0, 0), thickness=2)

        red_triangle_inside_1 = get_color_ratio(mask_red, s_triangle_region_1) >= 0.8
        red_triangle_inside_2 = get_color_ratio(mask_red, s_triangle_region_2) >= 0.8
        yellow_triangle_inside = get_color_ratio(mask_yellow, m_triangle_region) >= 0.8
        green_triangle_inside_1 = get_color_ratio(mask_green, l_triangle_region_1) >= 0.8
        green_triangle_inside_2 = get_color_ratio(mask_green, l_triangle_region_2) >= 0.8
        blue_rectangle_inside_1 = get_color_ratio(mask_blue, rectangle_region) >= 0.8
        blue_rectangle_inside_2 = get_color_ratio(mask_blue, square_region) >= 0.8

        # 서버로 보낼 데이터 준비
        conditions = [
                1 if red_triangle_inside_1 else 0,
                1 if red_triangle_inside_2 else 0,
                1 if yellow_triangle_inside else 0,
                1 if green_triangle_inside_1 else 0,
                1 if green_triangle_inside_2 else 0,
                1 if blue_rectangle_inside_1 else 0,
                1 if blue_rectangle_inside_2 else 0
        ]
        conditions_str = ",".join(map(str, conditions_list))  # "1,1,1,1,0,0,0" 형태로 변환

        # 2000ms마다 데이터 전송
        current_time = time.time()
        if current_time - last_sent_time >= 2:  # 2000ms(2초) 간격 확인
            try:
                print(f"Sending data: {conditions_str}")  # 전송 데이터 확인
                response = requests.post(server_url, json={"data": conditions_str}, timeout=5)
                if response.status_code == 200:
                    print(f"서버로 데이터 전송 성공! 보낸 데이터: {conditions_str}")
                else:
                    print(f"서버 전송 실패: 상태 코드 {response.status_code}, 응답: {response.text}")
                last_sent_time = current_time  # 마지막 전송 시간 업데이트
            except requests.exceptions.RequestException as e:
                print(f"서버 전송 오류: {e}")
       

        """
        cv2.putText(frame, f"Red1: {red_triangle_inside_1}", (50, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if red_triangle_inside_1 else (0, 0, 255), 2)
        cv2.putText(frame, f"Red2: {red_triangle_inside_2}", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if red_triangle_inside_2 else (0, 0, 255), 2)
        cv2.putText(frame, f"Yellow: {yellow_triangle_inside}", (50, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if yellow_triangle_inside else (0, 0, 255), 2)
        cv2.putText(frame, f"Green1: {green_triangle_inside_1}", (50, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if green_triangle_inside_1 else (0, 0, 255), 2)
        cv2.putText(frame, f"Green2: {green_triangle_inside_2}", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if green_triangle_inside_2 else (0, 0, 255), 2)
        cv2.putText(frame, f"Blue1: {blue_rectangle_inside_1}", (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if blue_rectangle_inside_1 else (0, 0, 255), 2)
        cv2.putText(frame, f"Blue2: {blue_rectangle_inside_2}", (50, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if blue_rectangle_inside_2 else (0, 0, 255), 2)
        """
        cv2.imshow("Tangram Detection", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    detect_tangram()
