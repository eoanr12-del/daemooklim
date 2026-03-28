"""hook-intro.md + _draft_part*.md → draft.md 병합."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_H2_RE = re.compile(r"^#{2,3}\s+(.+)$", re.MULTILINE)
_PART_NUM_RE = re.compile(r"_draft_part(\d+)\.md$")


def extract_hook_intro(path: Path) -> tuple[str, str]:
    """hook-intro.md에서 ## Hook / ## Intro 본문만 추출."""
    text = path.read_text(encoding="utf-8")
    headers = [(m.start(), m.end(), m.group(1).strip()) for m in _H2_RE.finditer(text)]

    hook_text = None
    intro_text = None

    for i, (start, end, title) in enumerate(headers):
        next_start = headers[i + 1][0] if i + 1 < len(headers) else len(text)
        body = text[end:next_start].strip()

        if re.match(r"Hook(\s*\(|$)", title):
            hook_text = body
        elif re.match(r"Intro(\s*\(|$)", title):
            intro_text = body

    if hook_text is None:
        raise ValueError(f"## Hook 헤더를 찾을 수 없습니다: {path}")
    if intro_text is None:
        raise ValueError(f"## Intro 헤더를 찾을 수 없습니다: {path}")

    return hook_text, intro_text


def collect_parts(parts_dir: Path) -> list[Path]:
    """_draft_part*.md를 숫자 순으로 정렬하여 반환."""
    parts = list(parts_dir.glob("_draft_part*.md"))
    if not parts:
        raise FileNotFoundError(f"_draft_part*.md 파일을 찾을 수 없습니다: {parts_dir}")

    def sort_key(p: Path) -> int:
        m = _PART_NUM_RE.search(p.name)
        return int(m.group(1)) if m else 999

    parts.sort(key=sort_key)
    return parts


def merge_draft(
    hook_intro_path: Path,
    parts_dir: Path,
    output_path: Path,
) -> int:
    """draft.md 병합. 0=성공, 1=오류."""
    try:
        hook_text, intro_text = extract_hook_intro(hook_intro_path)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    try:
        parts = collect_parts(parts_dir)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    sections = [f"## Hook & Intro\n\n{hook_text}\n\n{intro_text}"]

    for part_path in parts:
        content = part_path.read_text(encoding="utf-8").strip()
        sections.append(content)

    draft = "\n\n".join(sections) + "\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(draft, encoding="utf-8")

    print(f"draft.md 생성 완료: {output_path}")
    print(f"  Hook & Intro + {len(parts)}개 파트 병합")
    print(f"  총 {len(draft):,}자")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="hook-intro.md + _draft_part*.md → draft.md 병합",
    )
    parser.add_argument("--hook-intro", required=True, type=Path, help="hook-intro.md 경로")
    parser.add_argument("--parts-dir", required=True, type=Path, help="_draft_part*.md 디렉토리")
    parser.add_argument("--output", required=True, type=Path, help="출력 경로 (draft.md)")
    args = parser.parse_args()

    if not args.hook_intro.exists():
        print(f"ERROR: hook-intro.md를 찾을 수 없습니다: {args.hook_intro}", file=sys.stderr)
        sys.exit(1)
    if not args.parts_dir.is_dir():
        print(f"ERROR: parts 디렉토리를 찾을 수 없습니다: {args.parts_dir}", file=sys.stderr)
        sys.exit(1)

    sys.exit(merge_draft(args.hook_intro, args.parts_dir, args.output))


if __name__ == "__main__":
    main()
