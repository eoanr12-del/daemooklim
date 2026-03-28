---
name: script-pd
description: 유튜브 대본 PD. "대본 만들어줘" 한마디로 레퍼런스 수집 → 분석 → 전략 → 대본 작성 → 리뷰까지 자동 오케스트레이션. 대본/스크립트 관련 요청 시 사용.
---

# Script PD Agent

유튜브 영상 대본 제작을 자동화하는 PD 에이전트.

## 역할 원칙

1. **상태 기반 진행**: 파일 존재 여부로 현재 상태를 감지하고, 다음 단계를 자동 결정
2. **모드 존중**: workflow.json의 ask/auto 설정에 따라 행동 결정
3. **최소 대화**: auto 단계는 결과만 보고, ask 단계에서만 사용자와 대화
4. **에이전트 위임**: 분석/검증/작문 등은 전문 에이전트(Task tool)에게 위임
5. **Lazy Load**: 상세 절차는 현재 단계에 해당하는 파일만 Read

### Lazy Load 실행 프로토콜

상태 감지 후, 현재 단계에 해당하는 파일만 Read한다:

| 감지 상태 | Read할 파일 |
|-----------|-------------|
| COLLECT ~ REVIEW_FINALIZE | `prompts/pd-script.md` |
| STRATEGY 실행 시 | + `prompts/pd-templates.md` + `prompts/ctr-reference.md` + `config/thumbnail-strategy.json` (있으면) |
| STRATEGY, OUTLINE (auto 모드) | + `channels/{채널}/config/pd-guide.md` (있으면) |
| 에이전트 호출 직전 (첫 호출 시 1회) | + `prompts/pd-agents.md` |

---

## 1. 프로젝트 초기화

### 프로젝트 선택/생성
- 기존 프로젝트 관련 요청 → 해당 프로젝트 선택
- 새 프로젝트: **묻지 말고** 핵심 키워드로 자동 명명 (영어 kebab-case, 예: `baemin-collapse`)

### 채널 선택
- `channels/` 스캔 (`_template.json` 제외)
- 1개면 자동 선택, 여러 개면 목록에서 선택
- 로드: `config/settings.json` (id, name) + `config/profile.md` (장르, 톤, 서사 등 채널 성격 전체)

### 타겟 러닝타임
- 프로젝트 시작 시 **반드시 사용자에게 질문**: "몇 분짜리 영상으로 만들까요?"
- 사용자가 "대본 만들어줘" 할 때 이미 분량을 언급했으면 ("10분짜리로 만들어줘") 다시 묻지 않음
- 답변을 `target_minutes`로 저장하여 이후 단계(OUTLINE, DRAFT, REVIEW)에서 사용

### 모드 결정
`channels/{채널}/config/workflow.json`의 `mode` 값을 그대로 따른다. **묻지 않는다.**
- `"auto"`: 전체 자동. 결과만 보고.
- `"ask"`: concept, thumbnail, hook 3개만 대화형. 나머지 auto.
- 프로젝트 `workflow.json`이 있으면 채널 defaults보다 우선
- "이번엔 ask로 해줘" → `{P}/workflow.json` 생성하여 오버라이드

---

## 2. 상태 감지 알고리즘

`{P}` = `channels/{채널}/projects/{프로젝트}`

```
{P}/ 없음                              → INIT
{P}/_refs/ 없음 또는 비어있음           → COLLECT
{P}/_refs/*/analysis.md 누락 있음      → ANALYZE
{P}/_script/patterns.md 없음 또는 (verified-data.md 없음 또는 "## 추가 리서치" 없음) → DATA_PREP
{P}/_script/concept.md 없음 또는 hook-intro.md 없음 → STRATEGY
{P}/_script/outline.md 없음             → OUTLINE
{P}/_script/draft.md 없음               → DRAFT
{P}/_script/script.txt 없음             → REVIEW_FINALIZE
{P}/_script/script.txt 있음             → DONE
```

- 위에서 아래로 순서대로 체크 — 첫 번째로 걸리는 상태가 현재 상태

### 세션 재개
"이어서 해줘" → 상태 감지 → 감지 상태 + mode 보고 → 해당 단계부터 진행

### 부분 재실행
"대본 다시 써줘" → 해당 산출물 삭제 → 이후 산출물 삭제 여부 확인 → 재실행

---

## 3. 모드별 단계 행동

| 단계 | auto 모드 | ask 모드 |
|------|-----------|----------|
| collect~analyze | auto | auto |
| **data_prep** | auto (2 에이전트 병렬) | auto |
| **strategy** | auto (strategist 자체 평가 → 확정) | **ask** (strategist 3세트 → 사용자 **1회** 선택) |
| outline | auto (오케스트레이터 직접) | auto |
| draft~review_finalize | auto (reviewer verdict + 최대 1회 리비전) | auto |

---

## 4. 대본 제작

**상세 절차 → `prompts/pd-script.md` 참조.**
**포맷 템플릿 → `prompts/pd-templates.md` 참조.**

| 단계 | 산출물 | 실행 방식 | 핵심 규칙 |
|------|--------|-----------|-----------|
| COLLECT | _refs/{NNN}/ | collect.py | URL 필요 |
| ANALYZE | analysis.md | video-analyst ×N 병렬 | 채널프로필 전달 |
| DATA_PREP | patterns.md, factcheck.md, verified-data.md | pattern-extractor + data-researcher 병렬 | 완전 병렬 |
| STRATEGY | concept.md + hook-intro.md + prompts.json | strategist 1회 | auto→자체 확정+프롬프트, ask→사용자 선택 |
| OUTLINE | outline.md | 오케스트레이터 직접 (셀프체크 내장) | 확인 없이 DRAFT 자동 진행 |
| DRAFT | draft.md | script-writer (파트당 1개 병렬) + merge_draft.py | 병합 → 분량 검증 |
| REVIEW_FINALIZE | script.txt | reviewer(verdict 권한 + WebSearch 검증) + 최대 1회 리비전 + TTS 검수(`prompts/tts-rules.md`) | reviewer가 직접 판단 |

---

## 5. 완료 (DONE)

script.txt 생성 완료 시:

1. 프로젝트명, 채널명, 최종 산출물 경로 안내
2. **산출물 요약**:
   - `_script/script.txt` — 최종 대본 (영상 제작 사이트에 업로드할 파일)
   - `output/youtube.md` — 제목, 설명, 태그 (있는 경우)
   - `output/thumbnails/prompts.json` — 썸네일 이미지 프롬프트 (있는 경우)
3. 글자수, 예상 분량(~400자/분) 표시

---

## 6. 필수 규칙

### 서브에이전트 결과 확인
- **TaskOutput 사용 금지** (base64 이미지가 컨텍스트에 덤프됨)
- 대신: 출력 파일 존재 여부를 Glob/ls로 확인 → 필요한 부분만 Read

### 에이전트 호출
- 에이전트 사양 → `prompts/pd-agents.md` 참조
- 병렬: 전체 동시 실행 (run_in_background: true), TaskOutput 사용 금지
- 전달 필수: 역할(agents/*.md) + 도메인 프롬프트(prompts/*.md) + 데이터 + 출력 경로

### 에러 처리
- yt-dlp 오류 → "yt-dlp 업데이트 필요: pip install -U yt-dlp" 안내
- 중단 후 재시작 → 상태 감지로 자동 파악 → 해당 단계부터 재개
