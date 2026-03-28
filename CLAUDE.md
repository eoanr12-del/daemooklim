# autoworkers

유튜브 영상 대본 자동 제작 파이프라인. 레퍼런스 수집 → 분석 → 전략 → 대본 작성 → 리뷰까지.

## 사용법

### 채널 만들기
채널 생성 요청 시 **반드시 `.claude/skills/channel-setup/SKILL.md`를 먼저 읽고** 그대로 따를 것.
```
"채널 만들어줘"        → channel-setup 스킬 로드 → 대화형 채널 생성
```

### 대본 만들기
대본 제작 관련 요청 시 **반드시 `.claude/skills/script-pd/SKILL.md`를 먼저 읽고** 그대로 따를 것.
```
"대본 만들어줘"        → SKILL.md 로드 → 상태 감지 → 자동 진행
"이어서 해줘"          → 마지막 상태에서 재개
"대본 다시 써줘"       → 해당 단계만 재실행
```

## 프로젝트 구조

```
autoworkers/
├── .claude/
│   ├── skills/script-pd/SKILL.md     # PD 두뇌 (상태머신)
│   ├── skills/channel-setup/SKILL.md # 채널 생성 스킬
│   └── agents/                        # 역할별 에이전트 정의
├── channels/{channel-name}/            # 채널별 설정 + 프로젝트
│   ├── config/                        # 채널 설정 파일
│   │   ├── settings.json              # 채널 식별 (id, name)
│   │   └── profile.md                 # 채널 성격 전체 (장르, 톤, 서사, 관점 등)
│   └── projects/                      # 영상별 작업 폴더
│       └── {project-name}/
│           ├── _refs/                  # 레퍼런스 수집 결과
│           ├── _script/               # 대본 단계 산출물
│           └── output/                # 최종 산출물 (youtube.md, thumbnails/)
├── prompts/                           # 에이전트용 프롬프트
├── scripts/                           # Python 코드
│   ├── collect.py                     # yt-dlp 수집
│   ├── finalize.py                    # draft → script.txt
│   └── src/                           # 유틸리티
└── requirements.txt                   # Python 의존성
```

## 크로스 플랫폼 규칙 (필수)

이 프로젝트는 macOS와 Windows 사용자가 함께 사용한다. **모든 명령어 실행 시 OS를 자동 감지하여 적절한 명령어를 사용할 것.**

### Python 실행
- macOS/Linux: `.venv/bin/python scripts/...`
- Windows: `.venv\Scripts\python scripts/...`

```bash
# macOS/Linux
.venv/bin/python scripts/collect.py --project {project} --channel "{channel}" URL1 URL2

# Windows (cmd/PowerShell)
.venv\Scripts\python scripts/collect.py --project {project} --channel "{channel}" URL1 URL2
```

### pip 실행
- macOS/Linux: `.venv/bin/pip install -U yt-dlp`
- Windows: `.venv\Scripts\pip install -U yt-dlp`

### 파일/디렉토리 조작 — 셸 명령 대신 Python 사용
OS별 셸 명령(`mv`, `rm -r`, `mkdir -p` 등)은 크로스 플랫폼 호환이 안 되므로, **Python으로 대체**한다:

```bash
# mkdir -p 대신
python -c "import os; os.makedirs('path/to/dir', exist_ok=True)"

# mv 대신
python -c "import shutil; shutil.move('src', 'dst')"

# rm -r 대신
python -c "import shutil; shutil.rmtree('path/to/dir')"
```

> **프롬프트/스킬의 셸 명령은 예시일 뿐이다.** 실행 시 반드시 현재 OS에 맞는 명령어를 사용할 것.

## 산출물

최종 산출물은 `_script/script.txt`. 이 파일을 영상 제작 사이트에 업로드하면 TTS → 영상 제작이 자동 진행됨.
부가 산출물: `output/youtube.md` (제목/설명/태그), `output/thumbnails/prompts.json` (썸네일 프롬프트).
