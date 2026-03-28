# PD 에이전트 호출 사양

---

## 에이전트별 스펙

| 에이전트 | model | 실행 방식 | 참조 프롬프트 |
|----------|-------|-----------|-------------|
| video-analyst | sonnet | 전체 동시 병렬 | prompts/reference-analyze.md |
| pattern-extractor | opus | 1개 (data-researcher와 병렬) | prompts/reference-patterns.md |
| data-researcher | opus | 1개 (pattern-extractor와 병렬, WebSearch) | prompts/data-research.md |
| strategist | opus | 1개 (STRATEGY) | prompts/creative-strategy.md + prompts/ctr-reference.md + prompts/thumbnail-design.md + config/thumbnail-strategy.json (있으면) |
| script-writer | opus | 1~2개 순차 | outline.md + prompts/script-review-checklist.md |
| script-reviewer | opus | 1개 (verdict 권한, WebSearch) | prompts/script-review-checklist.md + prompts/draft-verify.md |

---

## 병렬 호출 패턴

독립적인 에이전트 N개를 동시에 실행:
1. 전체 대상 목록에 대해 Agent tool 동시 호출 (run_in_background: true)
2. 출력 파일 존재 여부를 Glob으로 확인
3. 모든 파일 생성 확인 후 다음 단계

**배치 분할 하지 않는다** — 에이전트들이 독립적이고 TaskOutput을 사용하지 않으므로 PD 컨텍스트 부하 없음.

---

## Task tool 호출 시 전달 내용

에이전트에게 항상 전달:
1. **역할** (agents/*.md에 정의된 역할 설명)
2. **도메인 프롬프트** (prompts/*.md 내용 또는 파일 경로)
3. **프로젝트 데이터** (파일 경로 — 에이전트가 직접 Read)
4. **출력 경로** (결과 파일 절대 경로)

가능하면 **파일 내용을 prompt에 임베드하지 말고 파일 경로를 전달**하여 PD 컨텍스트를 절약한다.

---

## 결과 확인 규칙 (필수)

- **TaskOutput 절대 사용 금지**: 에이전트 전체 transcript(base64 이미지 포함)가 PD 컨텍스트에 덤프되어 컨텍스트 폭발을 일으킴
- **대신**: 출력 파일 존재 여부를 Glob으로 확인 → 필요한 부분만 Read
- 에이전트가 파일을 잘 생성했는지만 확인하면 충분
- 에이전트 실패 시: 해당 에이전트만 재실행 (파일 미생성으로 감지)
