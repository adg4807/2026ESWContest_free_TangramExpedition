#include <SoftwareSerial.h>

const char* ssid = "119";
const char* password = "";
const char* serverUrl = "192.168.1.5";
const int serverPort = 7080;

const int button1Pin = 2;
const int led1Pin = 9;
const int button2Pin = 3;
const int led2Pin = 10;

bool led1On = false;
bool led2On = false;
unsigned long led1StartTime = 0;
unsigned long led2StartTime = 0;

SoftwareSerial esp(4, 5); // RX, TX

// 버튼 상태 큐
bool send1Pending = false;
bool send2Pending = false;
unsigned long lastButtonCheck = 0;
const unsigned long buttonCheckInterval = 50; // 버튼 상태 체크 간격 (ms)

boolean SendCommand(String command, String expectedResponse, int timeout = 5000);

void setup() {
  pinMode(button1Pin, INPUT_PULLUP);
  pinMode(button2Pin, INPUT_PULLUP);
  pinMode(led1Pin, OUTPUT);
  pinMode(led2Pin, OUTPUT);

  Serial.begin(9600);
  esp.begin(9600);

  delay(2000);
  Serial.println("ESP 초기화 중...");
  sendAT("AT");
  sendAT("AT+CWMODE=1");

  String connectCmd = "AT+CWJAP=\"" + String(ssid) + "\",\"" + String(password) + "\"";
  if (!sendATWait(connectCmd, "OK", 15000)) {
    Serial.println("WiFi 연결 실패");
    while (true);
  }
  Serial.println("WiFi 연결 성공!");
}

void loop() {
  // 버튼 누름 감지
  if (digitalRead(button1Pin) == LOW && !led1On) {
    Serial.println("버튼 1 눌림 감지");
    digitalWrite(led1Pin, HIGH);
    led1On = true;
    led1StartTime = millis();
    send1Pending = true;
  }

  if (digitalRead(button2Pin) == LOW && !led2On) {
    Serial.println("버튼 2 눌림 감지");
    digitalWrite(led2Pin, HIGH);
    led2On = true;
    led2StartTime = millis();
    send2Pending = true;
  }

  // LED 자동 OFF
  if (led1On && millis() - led1StartTime >= 5000) {
    digitalWrite(led1Pin, LOW);
    led1On = false;
  }

  if (led2On && millis() - led2StartTime >= 5000) {
    digitalWrite(led2Pin, LOW);
    led2On = false;
  }

  // 주기적으로 버튼 상태를 체크하고 서버로 전송
  if (millis() - lastButtonCheck >= buttonCheckInterval) {
    if (send1Pending || send2Pending) {
      sendValuesToServer();
      send1Pending = false;
      send2Pending = false;
    }
    lastButtonCheck = millis();
  }
}

// 서버에 POST 요청 (버튼 상태를 배열로 전송)
void sendValuesToServer() {
  String host = String(serverUrl);
  int port = serverPort;

  // JSON 배열 생성
  String jsonBody = "{\"hint\":[";
  bool first = true;
  if (send1Pending) {
    jsonBody += "1";
    first = false;
  }
  if (send2Pending) {
    if (!first) jsonBody += ",";
    jsonBody += "2";
  }
  jsonBody += "]}";

  int contentLength = jsonBody.length();

  String startCmd = "AT+CIPSTART=\"TCP\",\"" + host + "\"," + String(port);
  if (!SendCommand(startCmd, "CONNECT", 5000)) {
    Serial.println("TCP 연결 실패");
    return;
  }

  String request = "POST /api/hint HTTP/1.1\r\n";
  request += "Host: " + host + "\r\n";
  request += "Content-Type: application/json\r\n";
  request += "Content-Length: " + String(contentLength) + "\r\n";
  request += "Connection: close\r\n\r\n";
  request += jsonBody;

  String sendCmd = "AT+CIPSEND=" + String(request.length());
  if (!SendCommand(sendCmd, ">", 2000)) {
    Serial.println("CIPSEND 실패");
    return;
  }

  esp.print(request);

  unsigned long startTime = millis();
  while (millis() - startTime < 1000) {
    if (esp.available()) esp.read(); // 응답 무시
  }
  Serial.println("서버로 전송 완료: " + jsonBody);
}

// AT 명령 관련
bool sendATWait(String command, String waitFor, unsigned long timeout) {
  esp.println(command);
  unsigned long start = millis();
  String response = "";
  while (millis() - start < timeout) {
    while (esp.available()) {
      char c = esp.read();
      response += c;
      if (response.indexOf(waitFor) != -1) return true;
    }
  }
  Serial.println("sendATWait 실패: " + command);
  return false;
}

void sendAT(String command) {
  esp.println(command);
  delay(1000);
  while (esp.available()) {
    esp.read();
  }
}

boolean SendCommand(String command, String expectedResponse, int timeout = 5000) {
  esp.println(command);
  long int time = millis();
  while ((millis() - time) < timeout) {
    if (esp.find((char*)expectedResponse.c_str())) {
      return true;
    }
  }
  Serial.println("SendCommand 실패: " + command);
  return false;
}
