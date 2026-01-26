# Links Manager

프로시저 링크 관리 웹 애플리케이션입니다. 하드웨어 트리 구조와 프로시저 데이터베이스를 기반으로 링크를 관리합니다.

## 주요 기능

- **하드웨어 트리 구조**: 키워드 기반 트리 구조로 프로시저를 분류 및 탐색
- **프로시저 관리**: 프로시저 코드, 제목, 링크, 태그를 관리
- **버전 관리**: 여러 버전의 트리 및 프로시저 데이터베이스 지원
- **검색 기능**: 프로시저 제목으로 검색
- **네트워크 그래프**: 하드웨어 트리 구조를 시각화한 네트워크 그래프

## 기술 스택

- **Backend**: FastAPI
- **Storage**: CSV 파일 및 텍스트 파일 기반
- **Frontend**: Jinja2 Templates
- **Visualization**: vis.js (네트워크 그래프)
- **Python**: 3.11+

## 설치 방법

### 1. 저장소 클론

```bash
git clone https://github.com/KipCod/autoap_Link.git
cd autoap_Link
```

### 2. Conda 가상환경 생성 및 활성화

```bash
conda create -n autoap_link python=3.11 -y
conda activate autoap_link
```

### 3. 의존성 패키지 설치

```bash
pip install -r requirements.txt
```

## 실행 방법

### 방법 1: uvicorn으로 직접 실행 (권장)

```bash
uvicorn app.main:app --reload
```

### 방법 2: Python 모듈로 실행

```bash
python -m app.main
```

### 방법 3: 직접 실행

```bash
python app/main.py
```

애플리케이션이 실행되면 브라우저에서 `http://127.0.0.1:8000`으로 접속하세요.

## 데이터 구조

애플리케이션은 다음 파일들을 사용합니다:

- **tree.txt**: 하드웨어 키워드 트리 구조 (indent 기반, 4칸 = 1 레벨)
- **other_keywords.txt**: 추가 키워드 트리 구조
- **tagged_database.csv**: 프로시저 데이터베이스 (코드, 제목, 링크, 태그)

데이터 세트 구성은 `app/datasets.json` 파일에서 관리합니다.

## 데이터 세트 구성

데이터 세트는 `app/datasets.json` 파일에서 관리합니다. 각 세트는 여러 버전을 가질 수 있습니다.

### 세트 추가/수정 방법

1. `app/datasets.json` 파일을 엽니다
2. 필요한 만큼 객체를 추가하거나 기존 값을 수정합니다
3. `id`: URL 파라미터로 사용 (영문 소문자/숫자 조합 권장)
4. `label`: 화면 상단 탭에 표시될 이름
5. `versions`: 버전 배열
   - `tree_txt`: 하드웨어 트리 파일 경로
   - `other_keywords_txt`: 추가 키워드 파일 경로
   - `tagged_database_csv`: 프로시저 데이터베이스 CSV 파일 경로

예시:

```json
{
  "app_title": "CoSy Links Manager",
  "datasets": [
    {
      "id": "set_a",
      "label": "세트 A",
      "versions": [
        {
          "id": "ver1",
          "label": "ver1",
          "tree_txt": "set_a_ver1_tree.txt",
          "other_keywords_txt": "set_a_ver1_other_keywords.txt",
          "tagged_database_csv": "set_a_ver1_tagged_database.csv"
        }
      ]
    }
  ]
}
```

## 주요 기능 설명

### 1. 하드웨어 트리 탐색

- 홈 화면에서 하드웨어 섹션의 트리 구조를 탐색할 수 있습니다
- 각 노드를 클릭하여 펼치거나 접을 수 있습니다
- 네트워크 그래프에서 노드를 클릭하면 해당 트리 노드로 이동합니다

### 2. 프로시저 관리

1. "+ Link" 버튼을 클릭하여 프로시저 관리 페이지로 이동
2. 새 프로시저 추가: 코드, 제목, URL, 태그를 입력하여 추가
3. 태그 변경: 기존 프로시저의 태그를 변경하여 트리 구조에 매핑

### 3. 검색

- 검색 섹션에서 프로시저 제목으로 검색할 수 있습니다
- 검색 결과는 실시간으로 필터링됩니다

## 프로젝트 구조

```
autoap_Link/
├── app/
│   ├── __init__.py              # 패키지 초기화
│   ├── main.py                  # FastAPI 애플리케이션 메인
│   ├── models.py                # 데이터 모델
│   ├── database.py              # CSV 파일 읽기/쓰기 로직
│   ├── dataset_config.py        # 데이터 세트 설정 로더
│   ├── link_tree.py             # 트리 파싱 및 네트워크 그래프 생성
│   ├── datasets.json            # 데이터 세트 정의 파일
│   ├── static/
│   │   └── styles.css           # 스타일시트
│   └── templates/
│       ├── layout.html          # 기본 레이아웃
│       ├── home.html            # 홈 페이지 (트리 구조, 검색)
│       └── manage_links.html    # 프로시저 관리 페이지
├── requirements.txt             # Python 의존성 패키지
└── README.md                    # 이 파일
```

## API 엔드포인트

### 링크 관리
- `GET /`: 홈 페이지 (트리 구조, 검색)
- `GET /links/manage`: 프로시저 관리 페이지
- `POST /links/update-procedure`: 프로시저 태그 업데이트
- `POST /links/add-procedure`: 새 프로시저 추가
- `GET /export/links`: 링크 CSV 내보내기

## 주의사항

- `app/datasets.json` 파일을 수정한 후에는 서버를 재시작해야 변경사항이 반영됩니다
- 트리 파일은 indent 기반으로 파싱됩니다 (4칸 공백 = 1 레벨)
- 프로시저 태그는 트리 구조의 키워드와 일치해야 해당 노드에 표시됩니다

## 라이선스

이 프로젝트는 내부 사용을 위한 것입니다.
