/**
 * 3D 퍼즐 게임 서버
 * 
 * 이 서버는 실시간 3D 퍼즐 게임을 지원하는 백엔드 애플리케이션입니다.
 * 주요 기능:
 * - 아두이노 하드웨어와의 통신 및 좌표 기반 정답 검증
 * - 파이썬 프로그램과의 연동을 통한 게임 조건 설정
 * - WebSocket을 통한 실시간 클라이언트 통신
 * - 게임 설정, 점수, 랭킹 데이터의 영구 저장
 * - CORS 설정을 통한 크로스 오리진 요청 지원
 */

// ========================================
// 모듈 의존성 imports
// ========================================
const express = require('express');           // 웹 서버 프레임워크
const path = require('path');                 // 파일 경로 처리 유틸리티
const http = require('http');                 // HTTP 서버 생성
const WebSocket = require('ws');              // WebSocket 실시간 통신
const fs = require('fs');                     // 파일 시스템 조작

// ========================================
// 서버 및 애플리케이션 초기화
// ========================================
const app = express();                        // Express 애플리케이션 인스턴스
const server = http.createServer(app);        // HTTP 서버 인스턴스
const port = 7080;                           // 서버 포트 번호

// ========================================
// CORS (Cross-Origin Resource Sharing) 설정
// ========================================
/**
 * 모든 도메인에서의 API 접근을 허용하는 CORS 미들웨어
 * 개발 환경에서 프론트엔드와 백엔드가 다른 포트에서 실행될 때 필요
 */
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');                    // 모든 도메인 허용
    res.header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS'); // 허용 HTTP 메서드
    res.header('Access-Control-Allow-Headers', 'Content-Type');        // 허용 헤더
    next();
});

// ========================================
// 미들웨어 설정
// ========================================
app.use(express.json());                                              // JSON 파싱 미들웨어
app.use(express.static(path.join(__dirname, 'public')));             // 정적 파일 서빙 설정

// ========================================
// 데이터 저장 및 상태 관리
// ========================================
const DATA_FILE = 'data.json';  // 게임 데이터 영구 저장 파일

/**
 * 게임의 모든 상태 데이터를 관리하는 중앙 데이터 객체
 * 서버 재시작 시에도 데이터가 유지되도록 파일 시스템에 저장됨
 */
let data = {
    buttonSelections: {        // 버튼 선택 상태 관리
        selections: [],        // 선택 이력
        currentSelection: null // 현재 선택된 항목
    },
    pythonData: {},           // 파이썬 프로그램과 연동되는 데이터
    playedPatterns: [],       // 플레이한 패턴들의 통계 정보
    hintState: null,          // 힌트 시스템의 현재 상태
    rankings: []              // 게임 완료 시간 기반 랭킹 시스템
};

/**
 * 파이썬 프로그램에서 전송받은 OX 정답 조건 배열
 * 각 인덱스는 퍼즐 조각 번호를 나타내며, 값은 다음과 같음:
 * - 1: 맞춰야 하는 조각 (정답)
 * - 0: 맞추면 안 되는 조각 (오답)
 */
let pythonConditions = [];

/**
 * 3D 공간에서 각 퍼즐 조각의 정답 위치를 정의하는 좌표 범위 (패턴 1)
 * 각 조각(diagram)마다 x, y, z 좌표의 최소/최대 범위를 설정
 * 아두이노에서 전송받은 좌표가 이 범위 안에 있으면 정답으로 판정
 */
const answerZones = {
    0: { x: [-37, -35], y: [-423, -413], z: [101, 102] },     // 큰 삼각형1의 정답 영역
    1: { x: [-31, -30], y: [-335, -334], z: [-167, -165] },   // 큰 삼각형2의 정답 영역
    2: { x: [-8, -7], y: [-392, -390], z: [260, 263] },       // 작은 삼각형1의 정답 영역
    3: { x: [14, 15], y: [-250, -249], z: [-234, -233] },     // 작은 삼각형2의 정답 영역
    4: { x: [-213, -212], y: [-215, -213], z: [-170, -168] }, // 중간 삼각형의 정답 영역
    5: { x: [-189, -184], y: [-206, -205], z: [-79, -76] },   // 사각형의 정답 영역
    6: { x: [80, 81], y: [-292, -291], z: [110, 111] }        // 평행사변형의 정답 영역
};

/**
 * 3D 공간에서 각 퍼즐 조각의 정답 위치를 정의하는 좌표 범위 (패턴 2)
 * 패턴 1과 다른 위치에 조각들이 배치되는 경우의 좌표 범위
 */
const answerZones2 = {
    0: { x: [-166, -165], y: [184, 185], z: [125, 129] },     // 큰 삼각형1의 정답 영역
    1: { x: [119, 120], y: [188, 189], z: [39, 40] },         // 큰 삼각형2의 정답 영역
    2: { x: [-8, -7], y: [20, 21], z: [29, 30] },             // 작은 삼각형1의 정답 영역
    3: { x: [-153, -152], y: [230, 235], z: [-9, -8] },       // 작은 삼각형2의 정답 영역
    4: { x: [-173, -171], y: [213, 215], z: [16, 19] },       // 중간 삼각형의 정답 영역
    5: { x: [43, 44], y: [143, 153], z: [16, 19] },           // 사각형의 정답 영역
    6: { x: [71, 72], y: [-280, -279], z: [-196, -195] }      // 평행사변형의 정답 영역
};
 

/**
 * 이미 맞춘 퍼즐 조각들을 추적하는 Set 자료구조
 * Set을 사용하여 중복을 방지하고 O(1) 시간복잡도로 검색 가능
 */
const correctMatches = new Set();

/**
 * 현재 힌트를 제공할 수 있는 퍼즐 조각 번호들의 배열
 * 맞춰야 하는 조각 중에서 아직 맞추지 못한 조각들만 포함
 */
let eligibleHints = [];

// ========================================
// 데이터 영속성 관리 함수들
// ========================================

/**
 * JSON 파일에서 게임 데이터를 로드하는 함수
 * 서버 시작 시 호출되어 이전 게임 상태를 복원함
 * 
 * @throws {Error} 파일 읽기 또는 JSON 파싱 실패 시
 */
function loadData() {
    try {
        // 데이터 파일이 존재하는지 확인
        if (fs.existsSync(DATA_FILE)) {
            const fileData = fs.readFileSync(DATA_FILE, 'utf8');
            data = JSON.parse(fileData);
            
            // 배열 데이터 무결성 검증 및 초기화
            if (!Array.isArray(data.playedPatterns)) {
                data.playedPatterns = [];
            }
            
            // 서버 재시작 시 타임어택 상태는 항상 초기화
            // 진행 중인 타임어택이 있더라도 서버 재시작으로 인해 무효화됨
            data.timeAttackState = null;

            console.log('데이터 로드 완료');
        }
    } catch (error) {
        console.error('데이터 로드 오류:', error);
        // 로드 실패 시에도 서버는 기본 데이터 구조로 계속 실행됨
    }
}

/**
 * 현재 게임 데이터를 JSON 파일에 저장하는 함수
 * 게임 상태 변경 시마다 호출되어 데이터 손실을 방지함
 * 
 * @throws {Error} 파일 쓰기 실패 시
 */
function saveData() {
    try {
        // JSON 형태로 포맷팅하여 가독성 향상 (들여쓰기 2칸)
        fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
        console.log('데이터 저장 완료');
    } catch (error) {
        console.error('데이터 저장 오류:', error);
        // 저장 실패해도 서버 실행은 계속됨 (메모리 상태는 유지)
    }
}

// 서버 시작 전에 이전 데이터 로드
loadData();

// ========================================
// WebSocket 실시간 통신 설정
// ========================================

/**
 * WebSocket 서버 인스턴스 생성
 * HTTP 서버와 동일한 포트를 사용하여 실시간 양방향 통신 제공
 */
const wss = new WebSocket.Server({ server });

/**
 * 새로운 WebSocket 클라이언트 연결 처리
 * 클라이언트 연결 시 현재 게임 상태를 즉시 전송
 */
wss.on('connection', (ws) => {
    // 연결된 클라이언트에게 현재 게임 상태 전송
    ws.send(JSON.stringify({ type: 'state', data }));
    
    // WebSocket 연결 오류 처리
    ws.on('error', (error) => console.error('WS 에러:', error));
});

/**
 * 모든 연결된 WebSocket 클라이언트에게 데이터를 브로드캐스트하는 함수
 * 게임 상태 변경 시 모든 클라이언트가 실시간으로 업데이트를 받음
 * 
 * @param {string} type - 메시지 타입 (식별자)
 * @param {any} payload - 전송할 데이터 페이로드
 */
function broadcastData(type, payload) {
    wss.clients.forEach((client) => {
        // 연결이 활성 상태인 클라이언트에게만 전송
        if (client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify({ type, data: payload }));
        }
    });
}

// ========================================
// 게임 로직 유틸리티 함수들
// ========================================

/**
 * 주어진 3D 좌표가 특정 퍼즐 조각의 정답 영역 안에 있는지 검사하는 함수
 * 
 * @param {number} diagram - 퍼즐 조각 번호 (0-6)
 * @param {number} x - X 좌표
 * @param {number} y - Y 좌표  
 * @param {number} z - Z 좌표
 * @param {number} pattern - 패턴 번호 (1 또는 2, 기본값: 1)
 * @returns {boolean} 정답 영역 안에 있으면 true, 아니면 false
 */
function checkIfCorrect(diagram, x, y, z, pattern = 1) {
    const zone1 = answerZones[diagram];
    const zone2 = answerZones2[diagram];
    
    if (!zone1 && !zone2) return false;
    
    // 두 영역 중 하나라도 만족하면 정답
    const inZone1 = zone1 && (
        x >= zone1.x[0] && x <= zone1.x[1] &&
        y >= zone1.y[0] && y <= zone1.y[1] &&
        z >= zone1.z[0] && z <= zone1.z[1]
    );
    
    const inZone2 = zone2 && (
        x >= zone2.x[0] && x <= zone2.x[1] &&
        y >= zone2.y[0] && y <= zone2.y[1] &&
        z >= zone2.z[0] && z <= zone2.z[1]
    );
    
    return inZone1 || inZone2;
}

/**
 * 아두이노 전용 좌표 정답 확인 함수
 * 현재 선택된 패턴에 따라 적절한 좌표 영역을 사용하여 정답을 확인
 * 
 * @param {number} diagram - 퍼즐 조각 번호
 * @param {number} x - X 좌표
 * @param {number} y - Y 좌표
 * @param {number} z - Z 좌표
 * @returns {boolean} 정답 여부
 */
function checkArduinoOnly(diagram, x, y, z) {
const pattern1Result = checkIfCorrect(diagram, x, y, z, 1);
    if (pattern1Result) {
        console.log(`정답: diagram=${diagram}`);
        return true;
    }
    
    // 대칭 확인
    const pattern2Result = checkIfCorrect(diagram, x, y, z, 2);
    if (pattern2Result) {
        console.log(`대칭으로 정답: diagram=${diagram}`);
        return true;
    }
    
    console.log(`두 패턴 모두에서 오답: diagram=${diagram}`);
    return false;
}

// ========================================
// API 엔드포인트 정의
// ========================================

/**
 * 아두이노 하드웨어로부터 3D 좌표 데이터를 받아 정답 여부를 판정하는 API
 * POST /api/arduino
 * 
 * 요청 본문:
 * - diagram: 퍼즐 조각 번호 (number)
 * - x, y, z: 3D 좌표값 (number)
 * 
 * 응답:
 * - isCorrect: 정답 여부 (boolean)
 * - diagram: 조각 번호 확인용
 * - arrivalTime: 데이터 수신 시간
 */
app.post('/api/arduino', (req, res) => {
    const { diagram, x, y, z } = req.body;

    // 데이터 수신 시간 기록 (로그용)
    const now = new Date();
    const arrivalTime = now.toISOString().replace('T', ' ').substring(0, 19);
    console.log(`[${arrivalTime}] 아두이노 데이터 수신: diagram=${diagram}, x=${x}, y=${y}, z=${z}`);

    // 입력 데이터 유효성 검증
    if (typeof diagram !== 'number' || ![x, y, z].every(Number.isFinite)) {
        return res.status(400).json({ error: '유효하지 않은 데이터' });
    }

    // 이미 맞춘 조각들 (값이 1인 인덱스들)
    const alreadyCorrect = pythonConditions
        .map((cond, i) => cond === 1 ? i : null)
        .filter(i => i !== null);
    
    // 아직 맞춰야 하는 조각들 (값이 0인 인덱스들)
    const needToMatch = pythonConditions
        .map((cond, i) => cond === 0 ? i : null)
        .filter(i => i !== null);
    
    let isCorrect = false;
    
    // 아직 맞춰야 하는 조각인지 확인
    if (needToMatch.includes(diagram)) {
        // 맞춰야 하는 조각이고 좌표도 정답 범위 안에 있는 경우
        isCorrect = checkArduinoOnly(diagram, x, y, z);
        
        if (isCorrect) {
            correctMatches.add(diagram);
            console.log(`✅ 정답: diagram=${diagram}`);
        } else {
            console.log(`❌ 오답: diagram=${diagram}`);
        }
    }
    
    // 힌트 가능한 조각 목록 업데이트
    eligibleHints = needToMatch.filter(i => !correctMatches.has(i));

    // 게임 완료 조건 체크 (모든 정답 조각을 맞췄는지 확인)
    console.log('correctTargets:', correctTargets);
    console.log('correctMatches:', Array.from(correctMatches));
    console.log('두 패턴 모두 확인하는 모드 사용 중');
    
    const allCorrect = correctTargets.every(i => correctMatches.has(i));
    console.log('allCorrect:', allCorrect);

    // 모든 정답을 맞춘 경우 클리어 신호 브로드캐스트
    if (allCorrect) {
        console.log('🎉 모든 정답이 맞춰졌습니다!');
        broadcastData('clear', true);
    }

    // 모든 클라이언트에게 아두이노 결과 브로드캐스트
    broadcastData('arduino', { 
        isCorrect,           // 이번 시도의 정답 여부
        incorrectTargets,    // 맞추면 안 되는 조각들 (오답 처리용)
    });

    // 아두이노에게 응답 전송
    res.json({ isCorrect, diagram, arrivalTime });
});

/**
 * 파이썬 프로그램으로부터 게임 조건 (OX 배열)을 받는 API
 * POST /api/python
 * 
 * 요청 본문:
 * - conditions: 각 조각의 정답/오답 조건 배열 [0|1, 0|1, ...]
 * 
 * 응답:
 * - message: 성공 메시지
 */
app.post('/api/python', (req, res) => {
    const { conditions } = req.body;
    
    // 입력 데이터 유효성 검증
    if (!Array.isArray(conditions)) {
        return res.status(400).json({ error: 'conditions는 배열이어야 합니다' });
    }
    
    // 새로운 게임 조건 설정
    pythonConditions = conditions;
    correctMatches.clear(); // 기존 정답 기록 초기화
    
    // 힌트 가능한 조각들 업데이트
    eligibleHints = conditions
        .map((cond, i) => cond === 0 ? i : null)
        .filter(i => i !== null);

    // 모든 조건이 0인지 확인 (특별한 게임 모드 체크용)
    const allOne = conditions.every(c => c === 0);

    // 모든 클라이언트에게 새로운 조건 브로드캐스트
    broadcastData('python', { conditions, allOne });
    
    res.json({ message: 'OX 조건 업데이트 완료' });
});

/**
 * 힌트 및 타임어택 요청을 처리하는 API
 * POST /api/hint
 * 
 * 요청 본문:
 * - hint: 힌트 요청 여부 (any value)
 * - timeAttack: 타임어택 상태 ('start' | 'end')
 * 
 * 응답:
 * - status: 처리 상태
 */
app.post('/api/hint', (req, res) => {
    const { hint, timeAttack } = req.body;
    console.log('힌트/타임어택 요청:', req.body);

    // 전체 조각 번호 배열 (0-6)
    // TODO: 이 값은 eligibleHints를 사용하는 것이 더 적절할 수 있음
    const correctTargets = [0, 1, 2, 3, 4, 5, 6];

    // 힌트 요청 처리
    if (hint !== undefined) {
        let hintIndex = null;
        
        // 힌트를 줄 수 있는 조각이 있는 경우 랜덤 선택
        if (correctTargets.length > 0) {
            hintIndex = correctTargets[Math.floor(Math.random() * correctTargets.length)];
        }
        
        // 클라이언트들에게 힌트 브로드캐스트
        broadcastData('hint', { hint, hintIndex });
        console.log(`📌 힌트 요청 → 전송된 번호: ${hintIndex}`);
    }

    // 타임어택 상태 변경 처리
    if (timeAttack === 'start' || timeAttack === 'end') {
        broadcastData('timeAttack', { timeAttack });
        console.log(`타임어택 상태 업데이트: ${timeAttack}`);
    }

    res.json({ status: 'ok' });
});

/**
 * 클라이언트가 요청하는 게임 설정값들을 반환하는 API
 * GET /api/settings
 * 
 * 응답:
 * - selectedMode: 선택된 게임 모드
 * - selectedTime: 선택된 시간 설정
 * - selectedDifficulty: 선택된 난이도
 * - selectedPattern: 선택된 패턴
 * - selectedTheme: 선택된 테마
 */
app.get('/api/settings', (req, res) => {
    const settings = {
        selectedMode: data.selectedMode,
        selectedTime: data.selectedTime,
        selectedDifficulty: data.selectedDifficulty,
        selectedPattern: data.selectedPattern,
        selectedTheme: data.selectedTheme
    };
    res.json(settings);
});

/**
 * 선택된 시간 설정만을 반환하는 API (타이머 기능용)
 * GET /api/selected-time
 * 
 * 응답:
 * - selectedTime: 현재 설정된 시간값
 */
app.get('/api/selected-time', (req, res) => {
    res.json({ selectedTime: data.selectedTime });
});

/**
 * 게임 설정을 저장하는 API
 * POST /api/settings
 * 
 * 요청 본문:
 * - mode: 게임 모드 (선택사항)
 * - time: 시간 설정 (선택사항)
 * - difficulty: 난이도 (선택사항)
 * - pattern: 패턴 (선택사항)
 * - theme: 테마 (선택사항)
 * 
 * 응답:
 * - message: 저장 완료 메시지
 */
app.post('/api/settings', (req, res) => {
    const { mode, time, difficulty, pattern, theme } = req.body;

    // 전달된 설정값들만 업데이트 (undefined 체크로 선택적 업데이트)
    if (mode !== undefined) data.selectedMode = mode;
    if (time !== undefined) data.selectedTime = time;
    if (difficulty !== undefined) data.selectedDifficulty = difficulty;
    if (pattern !== undefined) data.selectedPattern = pattern;
    if (theme !== undefined) data.selectedTheme = theme;

    console.log('현재 저장된 data:', data);
    saveData(); // 영구 저장
    res.json({ message: '설정 저장 완료' });
});

/**
 * 플레이한 패턴들의 통계를 조회하는 API
 * GET /api/playedPatterns
 * 
 * 응답:
 * - 패턴별 플레이 횟수 배열
 */
app.get('/api/playedPatterns', (req, res) => {
    res.json(data.playedPatterns);
});

/**
 * 플레이한 패턴을 기록하는 API (통계용)
 * POST /api/playedPatterns
 * 
 * 요청 본문:
 * - pattern: 플레이한 패턴 이름
 * 
 * 응답:
 * - message: 저장 완료 메시지
 */
app.post('/api/playedPatterns', (req, res) => {
    const { pattern } = req.body;
    
    if (!pattern) {
        return res.status(400).json({ message: '패턴 이름이 필요합니다.' });
    }

    // 기존에 같은 패턴이 있는지 확인
    const existing = data.playedPatterns.find(p => p.pattern === pattern);
    
    if (existing) {
        // 기존 패턴의 플레이 횟수 증가
        existing.session += 1;
    } else {
        // 새로운 패턴 추가
        data.playedPatterns.push({ pattern, session: 1 });
    }

    saveData(); // 통계 데이터 영구 저장
    res.json({ message: `${pattern} 패턴이 저장되었습니다.` });
});

/**
 * 플레이 기록을 초기화하는 API
 * DELETE /api/playedPatterns
 * 
 * 응답:
 * - message: 초기화 완료 메시지
 */
app.delete('/api/playedPatterns', (req, res) => {
    data.playedPatterns = [];
    saveData();
    res.json({ message: '플레이 기록이 초기화되었습니다.' });
});

/**
 * 랭킹 목록을 조회하는 API
 * GET /api/rankings
 * 
 * 응답:
 * - rankings: 시간 기반 랭킹 배열 (오름차순 정렬)
 */
app.get('/api/rankings', (req, res) => {
    res.json({ rankings: data.rankings || [] });
});

/**
 * 게임 완료 점수(시간)를 랭킹에 등록하는 API
 * POST /api/submit-score
 * 
 * 요청 본문:
 * - name: 플레이어 이름
 * - time: 게임 완료 시간 (숫자, 낮을수록 좋음)
 * 
 * 응답:
 * - message: 등록 완료 메시지
 * - rankings: 업데이트된 랭킹 목록
 */
app.post('/api/submit-score', (req, res) => {
    const { name, time } = req.body;
    
    // 입력 데이터 유효성 검증
    if (!name || typeof time !== 'number') {
        return res.status(400).json({ error: '잘못된 요청' });
    }

    // 랭킹 배열 초기화 (없는 경우)
    if (!data.rankings) data.rankings = [];

    // 같은 이름의 기존 기록 찾기
    const existingIndex = data.rankings.findIndex(entry => entry.name === name);

    if (existingIndex !== -1) {
        // 기존 기록이 있고, 현재 기록이 더 좋은 경우에만 업데이트
        if (time < data.rankings[existingIndex].time) {
            data.rankings[existingIndex].time = time;
        }
    } else {
        // 새로운 플레이어 기록 추가
        data.rankings.push({ name, time });
    }

    // 시간 기준 오름차순 정렬 (낮은 시간이 더 좋은 순위)
    data.rankings.sort((a, b) => a.time - b.time);

    saveData(); // 랭킹 데이터 영구 저장
    res.json({ message: '기록 저장 완료', rankings: data.rankings });
});

/**
 * 랭킹 데이터를 초기화하는 API
 * DELETE /api/rankings
 * 
 * 응답:
 * - message: 초기화 완료 메시지
 */
app.delete('/api/rankings', (req, res) => {
    data.rankings = [];
    saveData();
    res.json({ message: '랭킹 데이터가 초기화되었습니다.' });
});

// ========================================
// 서버 시작 및 오류 처리
// ========================================

/**
 * HTTP 서버 시작
 * 지정된 포트에서 서버를 시작하고 성공/실패 메시지를 출력
 */
server.listen(port, () => {
    console.log(`서버 실행 중: http://localhost:${port}`);
}).on('error', (err) => {
    console.error('서버 시작 오류:', err);
    // 포트 충돌 등의 오류 발생 시 프로세스 종료
    process.exit(1);
});
