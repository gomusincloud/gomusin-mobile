# 고무신모바일 관리시스템

실제 데이터 저장이 가능한 Flask 웹사이트입니다.

## 포함 기능
- 관리자 로그인
- 고객 등록 / 수정 / 삭제 / 검색
- SQLite 데이터베이스에 실제 저장
- 예약 등록 및 조회
- 시세표 등록 / 삭제
- 관리자/직원 권한 구조
- PC 및 모바일 반응형

## 로컬 실행
```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

브라우저에서 `http://127.0.0.1:5000` 접속

초기 계정:
- ID: admin
- PW: 1234

## 실제 인터넷 공개 전 반드시 할 것
1. 관리자 비밀번호 변경
2. SECRET_KEY 환경변수 변경
3. SQLite 대신 관리형 PostgreSQL 등 운영용 DB 사용 권장
4. HTTPS 및 접근권한/백업 설정
5. 고객 개인정보 수집·보관 관련 법적 요구사항 검토
