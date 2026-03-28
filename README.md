# autoworkers

**유튜브 영상 대본 자동 제작 파이프라인.**

"대본 만들어줘" 한마디로 레퍼런스 수집 → 분석 → 전략 → 대본 작성 → 리뷰까지 자동으로 진행됩니다.

Claude Code가 PD 역할을 하며, 6개의 전문 에이전트를 오케스트레이션하여 유튜브 대본을 제작합니다.

---

## 어떻게 작동하나요?

```
사용자: "대본 만들어줘"
  ↓
Claude PD가 상태를 감지하고 자동으로 파이프라인을 실행:

1. COLLECT    — 레퍼런스 영상 수집 (yt-dlp)
2. ANALYZE    — 영상별 구조/기법 분석 (video-analyst 에이전트 ×N 병렬)
3. DATA_PREP  — 패턴 추출 + 팩트체크 (pattern-extractor + data-researcher 병렬)
4. STRATEGY   — 컨셉/훅/썸네일 전략 수립 (strategist 에이전트)
5. OUTLINE    — 대본 아웃라인 작성
6. DRAFT      — 대본 초고 작성 (script-writer 에이전트)
7. REVIEW     — 리뷰 + 수정 + 최종본 생성 (script-reviewer 에이전트)
  ↓
최종 산출물: _script/script.txt (TTS용 대본)
```

중간에 멈춰도 **"이어서 해줘"** 하면 마지막 상태에서 자동 재개됩니다.

---

## 시작하기

### 1. 사전 준비

- **Python 3.10+**
- **Claude Code** (CLI 또는 IDE 확장)

### 2. 설치

```bash
# 저장소 클론
git clone <repository-url>
cd autoworkers

# Python 가상환경 생성 + 의존성 설치
python -m venv .venv

# macOS/Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Windows (cmd)
.venv\Scripts\activate.bat

pip install -r requirements.txt
```

### 3. 채널 만들기

채널이 없으면 대본을 만들 수 없습니다. 먼저 채널을 만들어야 합니다.

```
Claude에게: "채널 만들어줘"
```

Claude가 장르, 톤, 서사 스타일 등을 대화형으로 물어보고, 채널 설정 파일을 자동 생성합니다.

### 4. 대본 만들기

```
Claude에게: "대본 만들어줘"
```

레퍼런스 영상 URL을 주면 수집부터 최종 대본까지 자동으로 진행됩니다.

---

## 프로젝트 구조

```
autoworkers/
├── .claude/
│   ├── skills/                        # Claude 스킬 정의
│   │   ├── script-pd/SKILL.md         # 대본 제작 PD (상태머신 오케스트레이터)
│   │   └── channel-setup/SKILL.md     # 채널 생성 스킬
│   └── agents/                        # 역할별 에이전트 정의
│       ├── video-analyst.md           #   레퍼런스 영상 분석
│       ├── pattern-extractor.md       #   패턴 추출
│       ├── data-researcher.md         #   팩트체크 + 리서치
│       ├── strategist.md              #   크리에이티브 전략
│       ├── script-writer.md           #   대본 작성
│       └── script-reviewer.md         #   대본 리뷰
│
├── channels/                          # 채널별 설정 + 프로젝트
│   └── {channel-name}/               #   (예: economy, psychology)
│       ├── config/
│       │   ├── settings.json          #     채널 식별 (id, name)
│       │   ├── profile.md             #     채널 성격 (장르, 톤, 서사, 관점 등)
│       │   └── workflow.json          #     auto/ask 모드 설정
│       └── projects/
│           └── {project-name}/        #     (예: samsung-crisis)
│               ├── _refs/             #       레퍼런스 수집 결과
│               ├── _script/           #       대본 단계별 산출물
│               └── output/            #       최종 산출물
│
├── prompts/                           # 에이전트용 프롬프트 (11개)
│   ├── pd-script.md                   #   대본 제작 상세 절차
│   ├── pd-agents.md                   #   에이전트 호출 사양
│   ├── pd-templates.md                #   산출물 포맷 템플릿
│   ├── creative-strategy.md           #   크리에이티브 전략 프롬프트
│   ├── ctr-reference.md               #   제목/썸네일 CTR 이론
│   ├── thumbnail-design.md            #   썸네일 프롬프트 규칙
│   ├── reference-analyze.md           #   영상 분석 프레임워크
│   ├── reference-patterns.md          #   패턴 추출 규칙
│   ├── data-research.md               #   데이터 검증 워크플로우
│   ├── script-review-checklist.md     #   대본 리뷰 체크리스트
│   ├── draft-verify.md                #   팩트체크 규칙
│   └── tts-rules.md                   #   TTS 전처리 규칙
│
├── scripts/                           # Python 코드
│   ├── collect.py                     #   yt-dlp 레퍼런스 수집
│   ├── finalize.py                    #   draft → script.txt 변환
│   └── src/
│       ├── project_resolver.py        #   프로젝트 경로 해석
│       ├── merge_draft.py             #   파트별 초고 병합
│       └── validate_draft.py          #   아웃라인 vs 초고 검증
│
├── CLAUDE.md                          # Claude 지시사항 (이 파일을 자동으로 읽음)
├── requirements.txt                   # Python 의존성 (yt-dlp)
└── README.md                          # 이 파일
```

---

## 산출물

| 파일 | 설명 |
|------|------|
| `_script/script.txt` | **최종 대본** — TTS 영상 제작 사이트에 업로드할 파일 |
| `output/youtube.md` | 영상 제목, 설명, 태그 |
| `output/thumbnails/prompts.json` | 썸네일 이미지 생성 프롬프트 |

---

## 주요 명령어

| 말하면 되는 것 | 하는 일 |
|----------------|---------|
| `"채널 만들어줘"` | 대화형으로 채널 설정 생성 |
| `"대본 만들어줘"` | 전체 파이프라인 실행 |
| `"이어서 해줘"` | 중단된 지점부터 재개 |
| `"대본 다시 써줘"` | 해당 단계만 재실행 |
| `"10분짜리로 만들어줘"` | 타겟 러닝타임 지정하여 실행 |

---

## 모드

채널의 `workflow.json`에서 설정합니다.

- **auto**: 전 과정 자동. 결과만 보고.
- **ask**: 컨셉/훅/썸네일 단계에서 사용자에게 선택지를 제시. 나머지는 auto.

---

## 트러블슈팅

### yt-dlp 에러 / 429 Too Many Requests

YouTube가 짧은 시간에 요청이 많으면 일시적으로 차단합니다. 영구 차단이 아닙니다.

- **해결**: 5~15분 기다렸다가 다시 시도
- **재개**: "이어서 해줘"하면 이미 수집된 영상은 건너뛰고 남은 것만 수집
- **예방**: 일반적인 사용(영상 3~5개 연속 수집)에서는 거의 발생하지 않음

### 레퍼런스 수집이 아예 안 될 때

yt-dlp가 어떤 이유로든 동작하지 않으면, 대본을 직접 붙여넣어서 진행할 수 있습니다.
Claude에게 "대본 만들어줘"를 하면, 수집 실패 시 자동으로 "대본을 직접 붙여넣어 주세요"라고 안내합니다.
유튜브 영상 페이지에서 자막/스크립트를 복사해서 붙여넣으면 됩니다.

### yt-dlp 버전 경고

`Your yt-dlp version is older than 90 days` 경고가 뜨면:
```bash
# macOS/Linux
.venv/bin/pip install -U yt-dlp
# Windows
.venv\Scripts\pip install -U yt-dlp
```

---

## 참고사항

- Python 실행은 항상 가상환경의 python 사용 (macOS: `.venv/bin/python`, Windows: `.venv\Scripts\python`)
- 레퍼런스 수집: 한국어 자막 우선, 없으면 영어 자막 사용 (외국어 영상도 레퍼런스 가능)
- 분량 기준: 약 400자/분
- `channels/*/projects/`는 `.gitignore`에 포함 — 각자의 프로젝트 데이터는 git에 올라가지 않음
