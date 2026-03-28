"""draft.md 파트별 분량 검증 — outline.md 목표 대비 실제 글자수 비교.

사용법:
    .venv/bin/python scripts/src/validate_draft.py <outline_path> <draft_path> [--threshold 0.9]

종료 코드:
    0 — 모든 검증 대상 섹션이 threshold 이상
    1 — FAIL 섹션 1개 이상
    2 — 파싱 에러 (목표/섹션 추출 불가)
"""

import argparse
import re
import sys
from pathlib import Path

# ── outline.md 파트 목표 추출 ──────────────────────────────────
_OUTLINE_PART_RE = re.compile(
    r"^###\s+(.+?)\s*\(~?[\d.]+분(?:\s*\d+초)?,\s*~?([\d,]+)자\)", re.MULTILINE
)

# ── draft.md 섹션 파싱 (finalize.py 동일 로직) ────────────────
_SECTION_HEADER_RE = re.compile(r"^#{2}\s+(.*)$")
_ANY_HEADER_RE = re.compile(r"^#{1,6}\s+")
_HR_RE = re.compile(r"^-{3,}$")
_BLOCKQUOTE_RE = re.compile(r"^>.*$")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", flags=re.DOTALL)


def parse_outline_targets(text: str) -> list[dict]:
    """outline.md에서 파트별 목표 글자수를 추출한다."""
    targets = []
    for m in _OUTLINE_PART_RE.finditer(text):
        targets.append({
            "title": m.group(1).strip(),
            "chars": int(m.group(2).replace(",", "")),
        })
    return targets


def parse_draft_sections(text: str) -> list[dict]:
    """draft.md에서 ## 헤더 기준으로 섹션별 글자수를 측정한다."""
    text = _HTML_COMMENT_RE.sub("", text)

    sections: list[dict] = []
    current_label: str | None = None
    current_chars = 0
    prev_had_text = False

    def _flush():
        nonlocal current_label, current_chars, prev_had_text
        if current_label is not None:
            sections.append({"title": current_label, "chars": current_chars})
        current_label = None
        current_chars = 0
        prev_had_text = False

    for line in text.splitlines():
        stripped = line.strip()

        if _HR_RE.match(stripped):
            continue
        if _BLOCKQUOTE_RE.match(stripped):
            continue

        m = _SECTION_HEADER_RE.match(stripped)
        if m:
            _flush()
            current_label = m.group(1).strip()
            continue

        if _ANY_HEADER_RE.match(stripped):
            continue

        if stripped:
            if prev_had_text:
                current_chars += 1  # 줄 간 공백 구분자
            current_chars += len(stripped)
            prev_had_text = True

    _flush()
    return sections


def validate(outline_path: Path, draft_path: Path, threshold: float) -> int:
    """검증 실행. 종료 코드 반환."""
    outline_text = outline_path.read_text(encoding="utf-8")
    draft_text = draft_path.read_text(encoding="utf-8")

    targets = parse_outline_targets(outline_text)
    if not targets:
        print(f"ERROR: outline.md에서 파트별 목표를 추출하지 못했습니다: {outline_path}", file=sys.stderr)
        return 2

    sections = parse_draft_sections(draft_text)
    if not sections:
        print(f"ERROR: draft.md에서 섹션을 감지하지 못했습니다: {draft_path}", file=sys.stderr)
        return 2

    # 첫 번째 섹션 = Hook & Intro (목표 없음, SKIP)
    hook = sections[0]
    body_sections = sections[1:]

    if len(body_sections) != len(targets):
        print(
            f"WARNING: outline 목표 {len(targets)}개 vs draft 섹션(Hook 제외) {len(body_sections)}개 — 매칭 가능한 만큼만 비교",
            file=sys.stderr,
        )

    # ── 결과 테이블 ──────────────────────────────────────────
    rows: list[dict] = []

    # Hook 행
    rows.append({
        "title": hook["title"],
        "target": None,
        "actual": hook["chars"],
        "ratio": None,
        "result": "SKIP",
    })

    # 본문 + 클로징 행
    match_count = min(len(body_sections), len(targets))
    for i in range(match_count):
        t = targets[i]
        s = body_sections[i]
        ratio = s["chars"] / t["chars"] if t["chars"] > 0 else 1.0
        result = "PASS" if ratio >= threshold else "FAIL"
        rows.append({
            "title": s["title"],
            "target": t["chars"],
            "actual": s["chars"],
            "ratio": ratio,
            "result": result,
        })

    # 매칭 안 된 나머지 draft 섹션 (목표 없음)
    for s in body_sections[match_count:]:
        rows.append({
            "title": s["title"],
            "target": None,
            "actual": s["chars"],
            "ratio": None,
            "result": "SKIP",
        })

    # ── 출력 ─────────────────────────────────────────────────
    col_w = max(len(r["title"]) for r in rows)
    col_w = max(col_w, 10)  # 최소 너비
    header = f"{'섹션':<{col_w}} | {'목표':>6} | {'실제':>6} | {'비율':>5} | 결과"
    sep = "─" * len(header)

    print(header)
    print(sep)
    for r in rows:
        target_str = f"{r['target']:>,}" if r["target"] is not None else "-"
        actual_str = f"{r['actual']:>,}"
        ratio_str = f"{r['ratio']:.0%}" if r["ratio"] is not None else "-"
        print(f"{r['title']:<{col_w}} | {target_str:>6} | {actual_str:>6} | {ratio_str:>5} | {r['result']}")
    print(sep)

    # 전체 합산
    total_target = sum(t["chars"] for t in targets)
    total_actual = sum(s["chars"] for s in sections)
    total_ratio = total_actual / total_target if total_target > 0 else 0
    print(f"전체: {total_actual:,} / {total_target:,} ({total_ratio:.0%})")

    fail_parts = [r["title"] for r in rows if r["result"] == "FAIL"]
    if fail_parts:
        print(f"FAIL 섹션: {', '.join(fail_parts)}")
        return 1

    return 0


def main():
    parser = argparse.ArgumentParser(description="draft.md 파트별 분량 검증")
    parser.add_argument("outline", type=Path, help="outline.md 경로")
    parser.add_argument("draft", type=Path, help="draft.md 경로")
    parser.add_argument("--threshold", type=float, default=0.9, help="통과 기준 비율 (기본 0.9)")
    args = parser.parse_args()

    if not args.outline.exists():
        print(f"ERROR: outline.md를 찾을 수 없습니다: {args.outline}", file=sys.stderr)
        sys.exit(2)
    if not args.draft.exists():
        print(f"ERROR: draft.md를 찾을 수 없습니다: {args.draft}", file=sys.stderr)
        sys.exit(2)

    sys.exit(validate(args.outline, args.draft, args.threshold))


if __name__ == "__main__":
    main()
