#include <SoftwareSerial.h>
#include <Wire.h>
#include <MechaQMC5883.h>

SoftwareSerial mySerial(2, 3); // RX, TX
MechaQMC5883 qmc;

const char* ssid = "";
const char* password = "";
const char* serverUrl = ""; // 서버 IP 주소
const int serverPort = 7080;
bool isTcpConnected = false;

// AT 명령 실행 및 응답 확인 함수 - 타임아웃 감소
boolean SendCommand(String command, String expectedResponse, int timeout = 2000) {
    mySerial.println(command);
    long int time = millis();
    while ((millis() - time) < timeout) {
        if (mySerial.find((char*)expectedResponse.c_str())) {
            return true;
        }
    }
    return false;
}

// WiFi 및 서버 연결 설정
void setup() {
    Serial.begin(9600);
    mySerial.begin(9600);
    qmc.init();
    Wire.setClock(400000); // I2C 클럭 속도 향상

    // AT 명령 이전에 ESP8266 초기화
    mySerial.println("AT+RST");
    delay(1000);
    mySerial.println("AT+CWMODE=1");
    delay(500);

    // WiFi 연결
    connectWiFi();
}

// WiFi 연결 함수
boolean connectWiFi() {
    String connectCmd = "AT+CWJAP=\"" + String(ssid) + "\",\"" + String(password) + "\"";
    if (!SendCommand(connectCmd, "OK", 10000)) {
        Serial.println("WiFi 연결 실패");
        return false;
    }
    Serial.println("WiFi 연결 성공!");
    return true;
}

// TCP 연결 함수
boolean connectTCP() {
    String cmd = "AT+CIPSTART=\"TCP\",\"" + String(serverUrl) + "\"," + String(serverPort);
    mySerial.println(cmd);
    delay(500); // 연결 대기 시간 단축
    
    if (mySerial.find("CONNECT") || mySerial.find("ALREADY CONNECTED")) {
        Serial.println("TCP 연결 성공");
        isTcpConnected = true;
        return true;
    } else {
        Serial.println("TCP 연결 실패");
        isTcpConnected = false;
        return false;
    }
}

unsigned long lastSendTime = 0;
const unsigned long sendInterval = 200; // 200ms마다 데이터 전송

void loop() {
    unsigned long currentTime = millis();
    
    // 전송 간격 체크
    if (currentTime - lastSendTime < sendInterval) {
        return;
    }
    
    lastSendTime = currentTime;
    
    int x, y, z;
    qmc.read(&x, &y, &z);
    
    // TCP 연결이 없으면 연결 시도
    if (!isTcpConnected) {
        if (!connectTCP()) {
            delay(500);
            return;
        }
    }
    
    // JSON 데이터 생성
    String postData = "{\"diagram\":2,\"x\":" + String(x) + ",\"y\":" + String(y) + ",\"z\":" + String(z) + "}"; 
    int postDataLength = postData.length();
    
    // HTTP 요청 헤더 작성 - 최소화
    String httpRequest = "POST /api/arduino HTTP/1.1\r\n";
    httpRequest += "Host: " + String(serverUrl) + ":" + String(serverPort) + "\r\n";
    httpRequest += "Content-Type: application/json\r\n";
    httpRequest += "Content-Length: " + String(postDataLength) + "\r\n";
    httpRequest += "Connection: keep-alive\r\n\r\n";
    httpRequest += postData;
    
    // 데이터 길이 전송
    mySerial.print("AT+CIPSEND=");
    mySerial.println(httpRequest.length());
    
    // 응답 대기 및 데이터 전송 - 응답 확인 단순화
    if (mySerial.find(">")) {
        mySerial.print(httpRequest);
        
        unsigned long sendTime = millis();
        if (mySerial.find("SEND OK") || (millis() - sendTime > 1000)) {
            // 데이터 전송 성공 또는 타임아웃
            if (millis() - sendTime <= 1000) {
                Serial.println("데이터 전송: " + postData);
            } else {
                Serial.println("전송 대기 시간 초과, 연결 재설정");
                isTcpConnected = false;
            }
        } else {
            Serial.println("전송 실패");
            isTcpConnected = false;
        }
    } else {
        Serial.println("CIPSEND 오류");
        isTcpConnected = false;
        mySerial.println("AT+CIPCLOSE");
    }
}
