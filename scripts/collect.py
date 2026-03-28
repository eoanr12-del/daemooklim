"""
YouTube 레퍼런스 영상 수집 스크립트

사용법:
    python3 scripts/collect.py --project 프로젝트명 [--channel 채널명] URL1 URL2 ...

Output:
    channels/{채널}/projects/{프로젝트명}/_refs/{번호}/
    ├── meta.md          ← 메타데이터 + 댓글 TOP 10
    ├── transcript.txt   ← 대본 (텍스트만)
    └── thumbnail.webp   ← 썸네일 이미지
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from project_resolver import resolve_project_dir

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def next_ref_id(ref_dir):
    """_refs/ 폴더에서 다음 번호를 자동으로 찾는다."""
    os.makedirs(ref_dir, exist_ok=True)
    existing = [d for d in os.listdir(ref_dir) if d.isdigit()]
    if not existing:
        return "001"
    return f"{max(int(d) for d in existing) + 1:03d}"


def run_ytdlp(url, output_dir):
    """yt-dlp로 영상 메타데이터 + 썸네일 + 자막을 가져온다."""
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-thumbnail",
        "--write-auto-sub",
        "--sub-lang", "ko",
        "--sub-format", "json3",
        "--print-json",
        "-o", os.path.join(output_dir, "%(id)s.%(ext)s"),
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"yt-dlp 에러: {result.stderr}")
        sys.exit(1)
    return json.loads(result.stdout)


def fetch_comments(url):
    """yt-dlp로 댓글 TOP 10만 별도로 가져온다."""
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-comments",
        "--no-write-info-json",
        "--extractor-args", "youtube:comment_sort=top;max_comments=10",
        "--print-json",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        return []
    data = json.loads(result.stdout)
    comments = data.get("comments", [])
    return comments[:10]


def parse_transcript(output_dir):
    """json3 자막 파일을 텍스트로 변환한다."""
    # 우선순위: ko > en > 나머지
    sub_file = None
    fallback = None
    for f in os.listdir(output_dir):
        if f.endswith(".ko.json3"):
            sub_file = os.path.join(output_dir, f)
            break
        elif f.endswith(".en.json3"):
            fallback = os.path.join(output_dir, f)
    sub_file = sub_file or fallback

    if not sub_file:
        return "(자막 없음)"

    with open(sub_file, "r", encoding="utf-8") as f:
        subs = json.load(f)

    segments = []
    for event in subs.get("events", []):
        segs = event.get("segs", [])
        text = "".join(s.get("utf8", "") for s in segs).strip()
        if text and text != "\n":
            segments.append(text)

    return " ".join(segments)


def build_meta_md(info, comments):
    """메타데이터를 마크다운으로 만든다."""
    ud = info.get("upload_date", "")
    upload_date = f"{ud[:4]}-{ud[4:6]}-{ud[6:8]}" if len(ud) == 8 else ud

    subs = info.get("channel_follower_count") or 0
    subs_str = f"{subs / 10000:.0f}만" if subs >= 10000 else f"{subs:,}"

    comment_rows = ""
    for i, c in enumerate(comments, 1):
        likes = c.get("like_count", 0)
        text = c.get("text", "").replace("\n", " ").replace("|", "\\|")
        comment_rows += f"| {i} | {likes:,} | {text} |\n"

    comment_count = info.get("comment_count", "N/A")
    if isinstance(comment_count, int):
        comment_count = f"{comment_count:,}"

    md = f"""# {info.get('title', '')}

## 기본 정보
- **URL**: https://www.youtube.com/watch?v={info.get('id', '')}
- **채널명**: {info.get('channel', '')}
- **구독자수**: {subs_str}
- **조회수**: {info.get('view_count', 0):,}
- **업로드일**: {upload_date}
- **영상 길이**: {info.get('duration_string', '')}
- **댓글 수**: {comment_count}
- **좋아요 수**: {info.get('like_count', 0):,}

## 썸네일
![thumbnail](thumbnail.webp)

---

## 댓글 (추천순 TOP 10)

| 순위 | 좋아요 | 댓글 |
|------|--------|------|
{comment_rows}"""

    return md


def cleanup(output_dir):
    """썸네일 이름 정리 + 임시 파일 삭제."""
    for f_name in os.listdir(output_dir):
        if f_name.endswith(".webp") and f_name != "thumbnail.webp":
            shutil.copy(
                os.path.join(output_dir, f_name),
                os.path.join(output_dir, "thumbnail.webp"),
            )
            os.remove(os.path.join(output_dir, f_name))
            break

    for f_name in os.listdir(output_dir):
        if f_name.endswith(".json3") or f_name.endswith(".info.json"):
            os.remove(os.path.join(output_dir, f_name))


def collect(url, ref_dir, ref_id):
    """메인 수집 함수."""
    output_dir = os.path.join(ref_dir, ref_id)
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n[1/5] 영상 정보 수집 중...")
    info = run_ytdlp(url, output_dir)
    title = info.get("title", "(제목 없음)")
    print(f"       → {title}")

    print(f"[2/5] 댓글 수집 중...")
    comments = fetch_comments(url)
    print(f"       → {len(comments)}개 수집")

    print(f"[3/5] meta.md 생성 중...")
    meta_md = build_meta_md(info, comments)
    with open(os.path.join(output_dir, "meta.md"), "w", encoding="utf-8") as f:
        f.write(meta_md)

    print(f"[4/5] transcript.txt 생성 중...")
    transcript = parse_transcript(output_dir)
    with open(os.path.join(output_dir, "transcript.txt"), "w", encoding="utf-8") as f:
        f.write(transcript)

    print(f"[5/5] 정리 중...")
    cleanup(output_dir)

    rel_path = os.path.relpath(output_dir, ROOT_DIR)
    print(f"\n✓ 완료! → {rel_path}/")
    for f_name in sorted(os.listdir(output_dir)):
        size = os.path.getsize(os.path.join(output_dir, f_name))
        print(f"  {f_name} ({size:,} bytes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube 레퍼런스 영상 수집")
    parser.add_argument("--project", required=True, help="프로젝트 폴더명 (예: 01-현대제철-귀족노조)")
    parser.add_argument("--channel", default=None, help="채널명 (미지정시 자동 탐색)")
    parser.add_argument("urls", nargs="*", help="YouTube URL 목록")
    args = parser.parse_args()

    project_dir = str(resolve_project_dir(args.project, args.channel))
    ref_dir = os.path.join(project_dir, "_refs")

    if args.urls:
        urls = args.urls
    else:
        urls = []
        while True:
            url = input("YouTube URL (엔터 → 종료): ").strip()
            if not url:
                break
            urls.append(url)

    if not urls:
        print("URL을 입력해주세요.")
        sys.exit(1)

    print(f"\n프로젝트: {args.project}")
    print(f"총 {len(urls)}개 영상 수집 시작\n{'='*40}")

    for i, url in enumerate(urls, 1):
        ref_id = next_ref_id(ref_dir)
        print(f"\n[{i}/{len(urls)}] _refs/{ref_id}/")
        collect(url, ref_dir, ref_id)

    print(f"\n{'='*40}")
    rel_path = os.path.relpath(ref_dir, ROOT_DIR)
    print(f"전체 완료! {rel_path}/ 를 확인하세요.")
