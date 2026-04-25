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

## GitHub 자동 동기화 정책

**저장소**: `https://github.com/eoanr12-del/daemooklim` (main 브랜치, 2026-04-25 연결)
**목적**: 다른 기기에서도 작업 이어가기 + 자동 백업

### 자동으로 "푸시할까요?" 묻는 시점
- `finalize.py` 실행 직후 (대본 한 편 완성)
- `.claude/`, `prompts/`, `scripts/` 안의 파일 수정 후
- `channels/*/config/` 변경 후 (채널 세팅 변경)
- `.gitignore`, `CLAUDE.md`, `requirements.txt` 수정 후
- 새 채널 또는 새 프로젝트의 산출물이 모두 완성된 시점 (1회만)

### 묻지 않는 시점
- 대본 진행 중 산출물(_refs, outline.md, draft.md 등) — finalize 시 한 번에 묶어서 묻는다
- 사용자 단순 질문/대화, TodoWrite, 임시 파일 작업

### 트리거 단어 (사용자 표현 모두 인식)
"푸시", "푸시해", "업로드", "올려", "깃", "백업", "동기화" 등 → 모두 GitHub push로 해석.

### 푸시 묻기 전 반드시 보여줄 것
1. **변경사항 요약** (신규/수정/삭제 — 많으면 카테고리별 카운트, 적으면 파일 목록)
2. **민감 파일 가드 검사**:
   ```bash
   git status --porcelain | grep -iE "bank_|_temp_|secret|key|\.env"
   ```
   결과 없으면 `✓ 통과`, 있으면 멈추고 사용자에게 경고 (.gitignore 누락 가능성).

### Commit message 자동 생성 규칙
| 변경 종류 | 메시지 형식 |
|----------|-----------|
| 대본 완성 | `Add script: <project-name> (<channel>)` |
| 코드/프롬프트/스킬 수정 | `Update <path>: <한줄 변경 이유>` |
| 정책·메모리·가이드 변경 | `Refine <topic>: <한줄 요점>` |
| 채널 세팅 변경 | `Update <channel> config: <한줄 이유>` |
| 신규 프로젝트 묶음 | `Add project: <project-name>` |
| 그 외 모호한 것 | `Refine <영역>: <한줄 요약>` |

### 실행 (사용자 동의 후)
```bash
git add -A
git commit -m "<자동 생성 메시지>"
git push origin main
```

### 가드레일
- main 브랜치에 직접 push (force-push 절대 금지)
- 민감 파일이 staged에 잡히면 멈추고 사용자에게 경고 (.gitignore 보강 후 재시도)
- push 실패(네트워크/인증)는 원인 보고
- Co-Authored-By 트레일러는 의미 있는 협업 commit에만 추가 (자잘한 자동 push에는 생략)
