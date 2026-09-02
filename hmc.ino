#include <SoftwareSerial.h>
#include <Wire.h>

SoftwareSerial mySerial(2, 3); // RX, TX
#define HMC5883L_ADDRESS 0x1E  // HMC5883L의 기본 I2C 주소

const char* ssid = "";
const char* password = "";
const char* serverUrl = ""; // 서버 IP 주소
const int serverPort = 7080;
bool isTcpConnected = false;

// AT 명령 실행 및 응답 확인 함수 - 타임아웃 단축
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

// 초기 설정
void setup() {
    Serial.begin(9600);
    mySerial.begin(9600);
    Wire.begin();
  
    // HMC5883L 초기화
    Wire.beginTransmission(HMC5883L_ADDRESS);
    Wire.write(0x00);
    Wire.write(0x70);
    Wire.endTransmission();

    Wire.beginTransmission(HMC5883L_ADDRESS);
    Wire.write(0x01);
    Wire.write(0xA0);
    Wire.endTransmission();

    Wire.beginTransmission(HMC5883L_ADDRESS);
    Wire.write(0x02);
    Wire.write(0x00);
    Wire.endTransmission();

    // WiFi 연결
    if (connectWiFi()) {
        // 초기 TCP 연결 설정
        connectTCP();
    }
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
    delay(1000); // 연결 대기시간 단축
    
    if (mySerial.find("CONNECT")) {
        Serial.println("TCP 연결 성공");
        isTcpConnected = true;
        return true;
    } else if (mySerial.find("ALREADY CONNECTED")) {
        Serial.println("이미 TCP 연결됨");
        isTcpConnected = true;
        return true;
    } else {
        Serial.println("TCP 연결 실패");
        isTcpConnected = false;
        return false;
    }
}

void loop() {
    int16_t x, y, z;
    
    // 센서 데이터 읽기
    Wire.beginTransmission(HMC5883L_ADDRESS);
    Wire.write(0x03);
    Wire.endTransmission();
    Wire.requestFrom(HMC5883L_ADDRESS, 6);
    
    if (Wire.available() == 6) {
        x = (Wire.read() << 8) | Wire.read();
        z = (Wire.read() << 8) | Wire.read();
        y = (Wire.read() << 8) | Wire.read();
    }
    
    // TCP 연결 확인 및 재연결
    if (!isTcpConnected) {
        if (!connectTCP()) {
            delay(1000); // 재연결 실패시 짧은 대기
            return;
        }
    }
    
    // JSON 데이터 생성
    String postData = "{\"diagram\":0,\"x\":" + String(x) + ",\"y\":" + String(y) + ",\"z\":" + String(z) + "}"; 
    
    // HTTP 요청 헤더 작성
    String httpRequest = "POST /api/arduino HTTP/1.1\r\n";
    httpRequest += "Host: " + String(serverUrl) + ":" + String(serverPort) + "\r\n";
    httpRequest += "Content-Type: application/json\r\n";
    httpRequest += "Content-Length: " + String(postData.length()) + "\r\n";
    httpRequest += "Connection: keep-alive\r\n\r\n";
    httpRequest += postData;

    // 데이터 전송
    mySerial.print("AT+CIPSEND=");
    mySerial.println(httpRequest.length());
    
    if (mySerial.find(">")) {
        mySerial.print(httpRequest);
        if (mySerial.find("SEND OK")) {
            Serial.println("데이터 전송: " + postData);
        } else {
            Serial.println("전송 실패");
            isTcpConnected = false; // 연결 상태 업데이트
        }
    } else {
        Serial.println("CIPSEND 오류");
        isTcpConnected = false;
        mySerial.println("AT+CIPCLOSE");
    }
    
    // 전송 간격 설정
    delay(100); // 더 빠른 전송 주기
}
