# 대본 제작 — 상세 절차

`{P}` = `channels/{채널}/projects/{프로젝트}`
`{VENV_PYTHON}` = macOS/Linux: `.venv/bin/python` | Windows: `.venv\Scripts\python`

---

## COLLECT

**YouTube 레퍼런스 수집.**

1. 사용자에게 YouTube URL 수집 (또는 이미 있으면 확인)
2. 실행:
```bash
{VENV_PYTHON} scripts/collect.py --project {프로젝트} --channel "{채널}" URL1 URL2 ...
```
3. 결과: `_refs/{NNN}/` 에 meta.md, transcript.txt, thumbnail.webp

### collect.py 실패 시 — 수동 수집 폴백

collect.py가 실패하면 (429 에러, 네트워크 문제 등) 사용자에게 대본을 직접 붙여넣도록 안내한다.

**흐름 — 한 번에 하나씩, 제목과 대본을 분리해서 받는다:**

```
1. 안내: "YouTube에서 직접 가져오지 못했습니다. 대본을 직접 붙여넣어 주세요."
2. 요청: "첫 번째 레퍼런스 영상의 제목을 알려주세요."
3. 사용자가 제목 입력
4. 요청: "이제 그 영상의 대본을 붙여넣어 주세요."
5. 사용자가 대본 붙여넣기
6. _refs/001/ 생성 (transcript.txt + meta.md)
7. 질문: "두 번째 레퍼런스 영상도 있나요?"
8. 있으면 → "제목을 알려주세요." → "대본을 붙여넣어 주세요." → _refs/002/ 생성
9. 반복 (최대 4~5개)
10. 없으면 → ANALYZE 진행
```

**파일 생성 규칙:**
- `_refs/{NNN}/transcript.txt` — 사용자가 붙여넣은 대본 텍스트 그대로 저장
- `_refs/{NNN}/meta.md` — 최소 정보로 생성:
  ```markdown
  # {영상 제목}

  ## 기본 정보
  - **URL**: {있으면 URL, 없으면 "(직접 입력)"}
  - **수집 방식**: 수동 입력
  ```
- `thumbnail.webp` — 없음 (수동 수집이므로 썸네일 없이 진행)

---

## ANALYZE

**레퍼런스 영상 분석. 에이전트: video-analyst**

1. `_refs/*/analysis.md`가 없는 영상 목록 확인
2. **전체 동시 병렬 실행** (run_in_background: true, **TaskOutput 사용 금지** → Glob으로 확인)
3. 각 에이전트에게 전달:
   - 채널 프로필 (`channels/{채널}/config/profile.md`)
   - 분석 프롬프트 (`prompts/reference-analyze.md`)
   - 영상 데이터 (meta.md + transcript.txt + thumbnail.webp)
4. 출력: 각 `_refs/{NNN}/analysis.md`
5. 완료 후 요약 보고

---

## DATA_PREP

**패턴 추출 + 데이터 검증/리서치. 2 에이전트 완전 병렬.**

### pattern-extractor 에이전트

1. 최소 2개 analysis.md 필요 (부족하면 알림)
2. 에이전트 1개 호출 (run_in_background: true)
3. 전달: 채널 프로필 + `prompts/reference-patterns.md` + 모든 analysis.md + meta.md
4. 출력: `{P}/_script/patterns.md`

### data-researcher 에이전트

1. 에이전트 1개 호출 (run_in_background: true, WebSearch 사용)
2. 전달: 채널 프로필 + `prompts/data-research.md` + 모든 transcript.txt + 모든 analysis.md
3. 출력: `{P}/_script/factcheck.md` + `{P}/_script/verified-data.md` (추가 리서치 포함)

### 완료 확인

- `_script/patterns.md` 존재 확인
- `_script/verified-data.md`에 "## 추가 리서치" 존재 확인

---

## STRATEGY

**크리에이티브 전략 통합 설계 + 썸네일 프롬프트. strategist 에이전트 1회.**

입력: `_script/patterns.md` + `_script/verified-data.md` + 채널 프로필

### 사전 준비

```bash
python -c "import os; os.makedirs('{P}/output/thumbnails', exist_ok=True)"
```

### strategist 에이전트 호출

1. strategist 에이전트 호출:
   - 전달: `prompts/creative-strategy.md` 내용 + `prompts/ctr-reference.md` 내용
          + `prompts/thumbnail-design.md` 내용
          + 채널 프로필 + `config/pd-guide.md` (있으면)
          + `config/thumbnail-strategy.json` (있으면)
          + `config/assets/mascot/` 경로 (있으면)
          + `_script/patterns.md` 경로 + `_script/verified-data.md` 경로
          + `{P}/_refs/` 경로
          + 모드 (auto / ask)
   - auto 출력: `{P}/_script/concept.md` + `{P}/_script/hook-intro.md` + `{P}/output/thumbnails/prompts.json`
   - ask 출력: `{P}/_script/_strategy_candidates.md`

### auto 모드

1. concept.md + hook-intro.md + prompts.json 존재 확인
2. 결과 요약 보고
3. 백그라운드 썸네일 이미지 생성 (fire-and-forget, prompts.json 존재 시):
```bash
{VENV_PYTHON} scripts/src/thumbnail/generate_thumbnails.py \
  --project {프로젝트} --channel "{채널}"
```
   - `run_in_background: true`로 실행, 완료 대기 없이 즉시 다음 단계 진행
4. OUTLINE 진행

### ask 모드

1. `_strategy_candidates.md` 읽기
2. 3 패키지 사용자에게 제시 (컨셉+제목+Hook 간결 비교)
3. 사용자 선택/수정/혼합:
   - "B로 해줘" → B 그대로 채택
   - "A 앵글에 B 제목으로" → 혼합
   - "A 좋은데 Hook 좀 바꿔줘" → 수정
4. 확정 → `_script/concept.md` + `_script/hook-intro.md` 저장
5. 썸네일 프롬프트 생성: `{S}/concept.md`의 썸네일 이미지 컨셉 + `prompts/thumbnail-design.md` 규칙 + `_refs/` 썸네일 분석으로 `{P}/output/thumbnails/prompts.json` 생성 (PD 직접 또는 strategist Phase 5 호출)
6. 백그라운드 썸네일 이미지 생성 (fire-and-forget, prompts.json 존재 시):
```bash
{VENV_PYTHON} scripts/src/thumbnail/generate_thumbnails.py \
  --project {프로젝트} --channel "{채널}"
```
   - `run_in_background: true`로 실행, 완료 대기 없이 즉시 다음 단계 진행
7. OUTLINE 진행

---

## OUTLINE

**통합 기획서 작성. PD 직접 수행.**

입력: `_script/concept.md` + `_script/hook-intro.md` + `_script/patterns.md` + `_script/verified-data.md` + 채널 프로필

### ask 모드
1. 통합 기획서 초안 제시 (포맷은 `prompts/pd-templates.md` 참조)
2. 사용자 검토/피드백 → 수정 → 확정
3. `_script/outline.md` 저장

### auto 모드
1. 오케스트레이터가 outline.md 직접 생성 (셀프체크 9항목 내장):
   1. 제목→구조 정합성
   2. 감정 전략 정합성
   3. 완시율 설계
   4. 핵심약속 이행
   5. 스테이크 상승
   6. 재참여 포인트 (2~3분 간격)
   7. 데이터 활용 검증 (verified-data.md에 존재하는 데이터만)
   8. 분량 현실성 (1분≈400자)
   9. 대본 작성 가능성
2. `_script/outline.md` 저장 → 바로 DRAFT 진행

### 제목→구조 제약 규칙

확정 제목이 본문 구조를 제약한다. 반드시 확인:

| 제목 패턴 | 구조 제약 |
|-----------|----------|
| "N가지 이유/방법/실수" | 정확히 N개 섹션 |
| "~의 몰락/추락/붕괴" | 시간순 서사 |
| "A vs B" 비교 | 비교 프레임워크 |
| "진짜 이유/숨겨진 비밀" | 미스터리 구조 (표면→단서→진실) |
| "~하는 법" | 프로세스 구조 |

concept.md의 서사 유형과 확정 제목이 호환되는지도 확인한다. 비호환 시 서사 유형을 제목에 맞춰 조정.

### 타겟 러닝타임 결정 가이드

프로젝트 초기화 시 사용자에게 받은 `target_minutes`를 기준으로 한다:
1. **target_minutes** 확인 (사용자가 프로젝트 시작 시 지정한 목표 분량)
2. 확정 제목이 암시하는 섹션 수 반영 (예: "3가지 이유" → 3섹션 × 각 2~3분 + Hook/클로징)
3. 콘텐츠 볼륨 고려 (verified-data.md 데이터량, 사례 수)
4. 위 요소를 종합하여 target_minutes ±20% 범위 내에서 최종 러닝타임 결정
5. 최종 러닝타임을 outline.md `## 1. 기획 뼈대`의 `타겟 러닝타임`에 기록

### 본문 구조 가이드
- 모든 파트가 핵심약속 이행에 기여
- 핵심 포인트 3~5개를 가치 상승 순서로 배열
- 파트 전환 직전에 오픈루프 배치
- 1~2분 간격으로 소규모 리텐션 장치(질문, 반전, 감정 전환) 배치
- patterns.md의 검증된 리텐션 장치(오픈루프, 전환문구, 감정유발)를 리텐션 설계 섹션에 발췌 기록
- 각 파트에 예상 시간/글자수 (1분 ≈ 400자)

### 리텐션 설계 가이드
- **재참여 포인트**: 파트 전환점마다 + 긴 파트 중간에 배치하여 2~3분 간격 유지. 타겟 러닝타임 전체에 걸쳐 빈 구간 없이 분포
- **스테이크 상승**: 파트가 진행될수록 "왜 이게 중요한가"의 규모가 커져야 함
- **감정 목표**: 각 파트별 시청자의 감정 상태를 명시 (예: 충격→분석→공감→경각심)

**저장 후: 사용자 확인 없이 바로 DRAFT 단계로 자동 진행한다.**

---

## DRAFT

**대본 초안 작성. 에이전트: script-writer (파트당 1개, 병렬)**

입력: `_script/outline.md` + `_script/concept.md` + `_script/verified-data.md` + 채널 프로필 + `prompts/script-review-checklist.md`

### 파트별 병렬 에이전트

1. outline.md `## 3. 본문 구조`에서 `### ` 파트 헤더 추출 → 파트 목록 확인
2. **Hook & Intro는 에이전트 범위에서 제외** — merge_draft.py가 자동 삽입
3. 파트당 에이전트 1개 병렬 호출:
   - 각 에이전트 → `_script/_draft_part{N}.md` 저장 (N = 파트 순서, 클로징 포함)
4. 각 에이전트에게 전달: outline.md(담당 파트 섹션) + concept.md + verified-data.md + 채널 프로필 + script-review-checklist.md + 담당 파트명 + 출력 경로
5. 완료 확인: `ls {S}/_draft_part*.md`로 파일 수 == 파트 수

### draft.md 병합

```bash
{VENV_PYTHON} scripts/src/merge_draft.py \
  --hook-intro {S}/hook-intro.md \
  --parts-dir {S} \
  --output {S}/draft.md
```

### 분량 검증 게이트 (REVIEW 전 필수)

```bash
{VENV_PYTHON} scripts/src/validate_draft.py {S}/outline.md {S}/draft.md --threshold 0.9
```

- **exit 0** (전 파트 90% 이상) → REVIEW 진행
- **exit 1** (FAIL 파트 있음) → 보충 2-pass:
  1. FAIL 파트 번호(N) 확인
  2. outline.md에서 빠진 내용(비유/사례/데이터) 식별
  3. script-writer 재호출 → `_draft_part{N}.md` 덮어쓰기
  4. merge_draft.py 재실행 → draft.md 재생성
  5. validate_draft.py 재실행 (1회)

---

## REVIEW_FINALIZE

**검수 + 확정. 에이전트: script-reviewer(verdict 권한 + 신규 주장 WebSearch 검증)**

1. **script-reviewer 에이전트 호출:**
   - 전달: `_script/draft.md` + `_script/outline.md` + `_script/concept.md` + `_script/verified-data.md` + `prompts/script-review-checklist.md` + `prompts/draft-verify.md`
   - 출력: `{P}/_script/review.md` (체크리스트 + 심각도 분류 + 신규 주장 검증 결과 + verdict)
   - reviewer가 신규 주장을 식별하면 즉시 WebSearch로 검증하여 review.md에 포함

2. **verdict 확인:**
   - review.md의 `verdict:` 확인
   - `verdict: 통과` → finalize.py 실행
   - `verdict: 수정` → 리비전 1회

3. **리비전 (최대 1회):**
   - review.md 치명적 항목 (신규 주장 ❌/⚠️ 포함) 정리
   - script-writer 재호출 → draft.md 덮어쓰기
   - finalize.py 실행 (재검수 없이 확정)

4. 확정 후 finalize:
```bash
{VENV_PYTHON} scripts/finalize.py --project {프로젝트} --channel "{채널}"
```
5. 결과: `{P}/_script/script.txt` (순수 텍스트, 한 줄 형태)

6. **TTS 검수:**
   - `{P}/_script/script.txt` 읽기
   - `prompts/tts-rules.md` 규칙에 따라 형식만 정리 (내용 변경 금지)
   - 정리된 텍스트를 `{P}/_script/script.txt`에 덮어쓰기
