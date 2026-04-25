"""
YouTube 영상 파인더 — 키워드로 조회수 높은 영상을 찾는다.

사용법:
    python scripts/find_videos.py --query "경제 위기" --period month --count 10
    python scripts/find_videos.py --channel economy-break --query "금리"
    python scripts/find_videos.py                          # 대화형 모드

카테고리(--channel):
    economy-break   경제/시사
    history-bite    역사
    joseon-tales    야담/조선
    mind-temp       심리
    science-wiki    과학/기술
    story-that-day  사연/실화

기간(--period):
    week / month / 3month / 6month / year / all(기본)
"""

import argparse
import json
import os
import subprocess
import sys
from urllib.parse import quote

# Windows cp949 stdout 인코딩 문제 방지
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# venv 내 yt-dlp 경로 자동 탐지
_VENV_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".venv")
if sys.platform == "win32":
    _YTDLP = os.path.join(_VENV_DIR, "Scripts", "yt-dlp.exe")
else:
    _YTDLP = os.path.join(_VENV_DIR, "bin", "yt-dlp")
if not os.path.isfile(_YTDLP):
    _YTDLP = "yt-dlp"

# 채널 → 카테고리 키워드 매핑
CHANNEL_CATEGORIES = {
    "economy-break":  {"name": "경제 브레이크",    "category": "경제/시사",    "keywords": ["경제", "시사", "재테크", "금융", "주식"]},
    "history-bite":   {"name": "역사이야기한입",    "category": "역사",        "keywords": ["역사", "한국사", "세계사"]},
    "joseon-tales":   {"name": "조선야담기록소",    "category": "야담/조선",    "keywords": ["조선", "야담", "조선시대", "사극"]},
    "mind-temp":      {"name": "마음온도",         "category": "심리",        "keywords": ["심리", "심리학", "멘탈", "정신건강"]},
    "science-wiki":   {"name": "잡학위키",         "category": "과학/기술",    "keywords": ["과학", "기술", "우주", "물리", "생물"]},
    "story-that-day": {"name": "그날의사연",        "category": "사연/실화",    "keywords": ["사연", "실화", "레전드", "감동"]},
}

# 기간 → YouTube search sp 파라미터 (sort=view_count, type=video)
# protobuf: sort=3(view_count), filter: upload_date + type=video
PERIOD_LABELS = {
    "all":     "전체",
    "week":    "이번 주",
    "month":   "이번 달",
    "3month":  "이번 달 (YouTube 최소 단위)",
    "6month":  "올해",
    "year":    "올해",
}

SP_PARAMS = {
    "all":     "CAMSAhAB",             # 전체 기간, 조회수순, 동영상만
    "week":    "CAMSBAgDEAE%3D",       # 이번 주
    "month":   "CAMSBAgEEAE%3D",       # 이번 달
    "3month":  "CAMSBAgEEAE%3D",       # YouTube 최소: 이번 달
    "6month":  "CAMSBAgFEAE%3D",       # YouTube 최소: 올해
    "year":    "CAMSBAgFEAE%3D",       # 올해
}


def format_count(n):
    """숫자를 읽기 쉬운 형태로."""
    if n is None:
        return "N/A"
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}억"
    if n >= 10_000:
        return f"{n / 10_000:.1f}만"
    if n >= 1_000:
        return f"{n / 1_000:.1f}천"
    return str(n)


def search_youtube(query, period="all", count=20):
    """yt-dlp로 YouTube 검색 결과를 가져온다."""
    sp = SP_PARAMS.get(period, SP_PARAMS["all"])
    search_url = f"https://www.youtube.com/results?search_query={quote(query)}&sp={sp}"

    fetch_count = min(count * 2, 60)

    cmd = [
        _YTDLP,
        "--flat-playlist",
        "--dump-single-json",
        "--no-download",
        "--playlist-end", str(fetch_count),
        search_url,
    ]

    label = PERIOD_LABELS.get(period, period)
    print(f"검색 중: \"{query}\" (기간: {label})...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        print(f"yt-dlp 에러: {result.stderr[:500]}")
        sys.exit(1)

    data = json.loads(result.stdout)
    entries = data.get("entries", [])

    if not entries:
        print("검색 결과가 없습니다.")
        return []

    # 조회수 순 정렬 (YouTube sp가 이미 기간 필터 처리)
    entries.sort(key=lambda e: e.get("view_count") or 0, reverse=True)

    return entries[:count]


def display_results(entries):
    """결과를 보기 좋게 출력한다."""
    if not entries:
        print("\n결과 없음.")
        return

    print(f"\n{'='*70}")
    print(f"{'순위':>4}  {'조회수':>8}  {'길이':>6}  제목")
    print(f"{'='*70}")

    for i, e in enumerate(entries, 1):
        views = format_count(e.get("view_count"))
        dur_sec = e.get("duration")
        if dur_sec:
            m, s = divmod(int(dur_sec), 60)
            h, m = divmod(m, 60)
            duration = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
        else:
            duration = e.get("duration_string", "?")
        title = e.get("title", "(제목 없음)")
        channel = e.get("channel", "")
        vid_id = e.get("id", "")
        url = f"https://www.youtube.com/watch?v={vid_id}"

        # 업로드일
        ud = e.get("upload_date", "")
        upload_str = f"{ud[:4]}-{ud[4:6]}-{ud[6:8]}" if len(ud) == 8 else ""

        # 제목 잘라내기 (터미널 폭)
        if len(title) > 40:
            title = title[:39] + "…"

        print(f"  {i:>2}.  {views:>8}  {duration:>6}  {title}")
        print(f"      {channel} | {upload_str} | {url}")
        print()

    print(f"{'='*70}")


def print_urls(entries):
    """collect.py에 바로 넣을 수 있는 URL 목록을 출력한다."""
    print("\n[URL 목록 — collect.py용]")
    urls = []
    for e in entries:
        vid_id = e.get("id", "")
        url = f"https://www.youtube.com/watch?v={vid_id}"
        urls.append(url)
        print(f"  {url}")
    print()
    print("복사용 (한 줄):")
    print("  " + " ".join(urls))


def show_channels():
    """등록된 채널 목록을 보여준다."""
    print("\n등록된 채널:")
    print(f"  {'ID':<16} {'이름':<16} {'카테고리'}")
    print(f"  {'-'*16} {'-'*16} {'-'*16}")
    for cid, info in CHANNEL_CATEGORIES.items():
        print(f"  {cid:<16} {info['name']:<16} {info['category']}")
    print()


def interactive_mode():
    """대화형 모드로 실행한다."""
    print("\n유튜브 파인더")
    print("=" * 40)

    # 채널 선택
    show_channels()
    channel_input = input("채널 선택 (ID 입력, 스킵=엔터): ").strip()
    channel_info = CHANNEL_CATEGORIES.get(channel_input)

    if channel_info:
        print(f"  → {channel_info['name']} ({channel_info['category']})")
        print(f"  관련 키워드: {', '.join(channel_info['keywords'])}")
    print()

    # 검색어 입력
    query = input("검색어: ").strip()
    if not query:
        print("검색어를 입력해주세요.")
        sys.exit(1)

    # 기간 선택
    print("\n기간: week / month / 3month / 6month / year / all")
    period = input("기간 (기본=all): ").strip() or "all"

    # 개수
    count_input = input("결과 수 (기본=15): ").strip()
    count = int(count_input) if count_input.isdigit() else 15

    # 검색 실행
    entries = search_youtube(query, period, count)
    display_results(entries)

    if entries:
        print_urls(entries)


def main():
    parser = argparse.ArgumentParser(
        description="YouTube 영상 파인더 — 조회수 높은 영상 검색",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python scripts/find_videos.py --query "경제 위기" --period month
  python scripts/find_videos.py --channel economy-break --query "금리 인상"
  python scripts/find_videos.py  # 대화형 모드
        """,
    )
    parser.add_argument("--query", "-q", help="검색 키워드")
    parser.add_argument("--channel", "-c", help="채널 ID (카테고리 참고용)")
    parser.add_argument("--period", "-p", default="all",
                        choices=["week", "month", "3month", "6month", "year", "all"],
                        help="기간 필터 (기본: all)")
    parser.add_argument("--count", "-n", type=int, default=15, help="결과 수 (기본: 15)")
    parser.add_argument("--list-channels", action="store_true", help="등록된 채널 목록 출력")
    args = parser.parse_args()

    if args.list_channels:
        show_channels()
        sys.exit(0)

    # 대화형 모드
    if not args.query:
        interactive_mode()
        return

    # CLI 모드
    channel_info = CHANNEL_CATEGORIES.get(args.channel) if args.channel else None
    if channel_info:
        print(f"채널: {channel_info['name']} ({channel_info['category']})")

    entries = search_youtube(args.query, args.period, args.count)
    display_results(entries)

    if entries:
        print_urls(entries)


if __name__ == "__main__":
    main()
