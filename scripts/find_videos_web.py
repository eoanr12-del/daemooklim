"""
YouTube 영상 파인더 — 웹 UI (v3)

사용법:
    python scripts/find_videos_web.py
    → 브라우저에서 http://localhost:8585 접속
"""

import json
import os
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import quote, parse_qs, urlparse

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_VENV_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".venv")
if sys.platform == "win32":
    _YTDLP = os.path.join(_VENV_DIR, "Scripts", "yt-dlp.exe")
else:
    _YTDLP = os.path.join(_VENV_DIR, "bin", "yt-dlp")
if not os.path.isfile(_YTDLP):
    _YTDLP = "yt-dlp"

PORT = 8585

# ── SP 파라미터 ──
SP_MAP = {
    ("views", "all"):    "CAMSAhAB",
    ("views", "hour"):   "CAMSBAgBEAE%3D",
    ("views", "today"):  "CAMSBAgCEAE%3D",
    ("views", "week"):   "CAMSBAgDEAE%3D",
    ("views", "month"):  "CAMSBAgEEAE%3D",
    ("views", "year"):   "CAMSBAgFEAE%3D",
    ("latest", "all"):   "CAISAhAB",
    ("latest", "hour"):  "CAISBAgBEAE%3D",
    ("latest", "today"): "CAISBAgCEAE%3D",
    ("latest", "week"):  "CAISBAgDEAE%3D",
    ("latest", "month"): "CAISBAgEEAE%3D",
    ("latest", "year"):  "CAISBAgFEAE%3D",
    ("trending", "all"):   "EgIQAQ%3D%3D",
    ("trending", "hour"):  "EgQIARAB",
    ("trending", "today"): "EgQIAhAB",
    ("trending", "week"):  "EgQIAxAB",
    ("trending", "month"): "EgQIBBAB",
    ("trending", "year"):  "EgQIBRAB",
}

BROADCASTER_KW = [
    "KBS", "MBC", "SBS", "JTBC", "YTN", "tvN", "채널A", "TV조선", "MBN",
    "EBS", "KTV", "연합뉴스", "한국경제TV", "뉴스", "NHK", "TBS",
    "ABC", "NBC", "CBS", "CNN", "BBC", "FOX",
]
CORP_KW = [
    "삼성", "Samsung", "현대", "Hyundai", "LG", "SK", "롯데", "Lotte",
    "CJ", "포스코", "POSCO", "한화", "Hanwha", "GS", "두산",
    "카카오", "Kakao", "네이버", "NAVER", "쿠팡", "Apple", "Google",
]


# ── 상세 메타 조회 ──
def get_details(video_ids):
    """개별 영상의 upload_date, view_count 상세 조회."""
    if not video_ids:
        return {}
    urls = [f"https://www.youtube.com/watch?v={v}" for v in video_ids[:40]]
    cmd = [_YTDLP, "--no-download",
           "--print", "%(id)s|%(upload_date)s|%(view_count)s"] + urls
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        out = {}
        for line in r.stdout.strip().split("\n"):
            p = line.strip().split("|")
            if len(p) >= 3:
                vid = p[0]
                ud = p[1] if p[1] not in ("NA", "None", "") else ""
                vc = int(p[2]) if p[2].isdigit() else None
                out[vid] = {"upload_date": ud, "view_count": vc}
        return out
    except Exception:
        return {}


def compute_metrics(vc, upload_date):
    """속도(views/hour)와 상승지수를 계산한다."""
    if not upload_date or not vc:
        return 0, 0, "unknown"
    try:
        ud = datetime.strptime(upload_date, "%Y%m%d")
        age_h = max((datetime.now() - ud).total_seconds() / 3600, 1)
        vph = vc / age_h  # views per hour
        # 상승지수: log-scale score (0~100)
        import math
        score = min(100, int(math.log10(max(vph, 1)) * 25))
        # 상태
        if age_h <= 24:
            status = "new"
        elif vph >= 1000:
            status = "rising"
        elif vph >= 100:
            status = "steady"
        else:
            status = "falling"
        return round(vph, 1), score, status
    except Exception:
        return 0, 0, "unknown"


# ── 메인 검색 ──
def search_youtube(query, sort="views", period="week", country="KR",
                   fmt="long", count=20, min_views=0,
                   upload_within=0, compare_hours=24, status_filter="all",
                   ex_broad=False, ex_corp=False, ex_big=False, dedup=True):

    sp = SP_MAP.get((sort, period), "CAMSAhAB")
    url = f"https://www.youtube.com/results?search_query={quote(query)}&sp={sp}&gl={country}"
    fetch_n = min(count * 3, 80)

    cmd = [_YTDLP, "--flat-playlist", "--dump-single-json",
           "--no-download", "--playlist-end", str(fetch_n), url]

    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        return {"error": r.stderr[:300]}

    entries = json.loads(r.stdout).get("entries", [])

    # 1차 필터
    filt = []
    seen = set()
    for e in entries:
        if e.get("live_status") == "is_live":
            continue
        dur = e.get("duration") or 0
        vc = e.get("view_count") or 0
        ch = (e.get("channel") or "")

        if fmt == "long" and dur < 60:
            continue
        if fmt == "shorts" and (dur >= 60 or dur == 0):
            continue
        if vc < min_views:
            continue
        if ex_broad and any(k.lower() in ch.lower() for k in BROADCASTER_KW):
            continue
        if ex_corp and any(k.lower() in ch.lower() for k in CORP_KW):
            continue
        if ex_big and e.get("channel_is_verified"):
            continue
        if dedup:
            cid = e.get("channel_id") or ch
            if cid in seen:
                continue
            seen.add(cid)
        filt.append(e)

    if sort == "views":
        filt.sort(key=lambda x: x.get("view_count") or 0, reverse=True)

    filt = filt[:count * 2]

    # 2차: 상세 조회 (속도/상승지수 계산용)
    ids = [e["id"] for e in filt if e.get("id")]
    details = get_details(ids)

    now = datetime.now()
    final = []
    STATUS_KO = {"new": "신규", "rising": "상승", "falling": "하락",
                 "steady": "유지", "unknown": ""}

    for e in filt:
        vid = e.get("id", "")
        d = details.get(vid, {})
        ud = d.get("upload_date", "")
        vc = d.get("view_count") or e.get("view_count") or 0

        # 업로드 N시간 이내 필터
        if upload_within > 0:
            if not ud:
                continue
            try:
                age_h = (now - datetime.strptime(ud, "%Y%m%d")).total_seconds() / 3600
                if age_h > upload_within:
                    continue
            except ValueError:
                continue

        vph, score, status = compute_metrics(vc, ud)

        # 상태 필터
        if status_filter != "all" and status != status_filter:
            continue

        final.append({
            "id": vid,
            "title": e.get("title", ""),
            "channel": e.get("channel", ""),
            "view_count": vc,
            "duration": e.get("duration"),
            "thumbnails": e.get("thumbnails", []),
            "verified": e.get("channel_is_verified") or False,
            "upload_date": ud,
            "vph": vph,
            "score": score,
            "status": STATUS_KO.get(status, ""),
        })

    if sort == "views":
        final.sort(key=lambda x: x.get("view_count") or 0, reverse=True)

    return {"entries": final[:count],
            "total_fetched": len(entries),
            "after_filter": len(final)}


# ════════════════════════════════════════
# HTML
# ════════════════════════════════════════

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>YouTube Finder</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',-apple-system,'Malgun Gothic',sans-serif;background:#0a0a0a;color:#e0e0e0;min-height:100vh}

.header{background:#111;border-bottom:1px solid #222;padding:14px 20px;display:flex;align-items:center;gap:10px}
.header h1{font-size:18px;font-weight:700;color:#fff}
.header .dot{color:#ff4444;font-size:22px}

.wrap{max-width:1100px;margin:0 auto;padding:16px 20px}

/* ── 검색 ── */
.search-row{display:flex;gap:8px;margin-bottom:12px}
.search-row input{flex:1;padding:11px 14px;border:1px solid #282828;border-radius:8px;background:#141414;color:#fff;font-size:14px;outline:none}
.search-row input:focus{border-color:#ff4444}
.btn-s{padding:11px 24px;border:none;border-radius:8px;background:#ff4444;color:#fff;font-size:14px;font-weight:700;cursor:pointer}
.btn-s:hover{background:#e03030}
.btn-s:disabled{background:#333;cursor:not-allowed}

/* ── 필터바 ── */
.fbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
.fg{display:flex;align-items:center;gap:4px}
.fg label{font-size:11px;color:#666}
.fg select,.fg input{padding:6px 8px;border:1px solid #282828;border-radius:6px;background:#141414;color:#ddd;font-size:12px;outline:none}
.fg input[type=number]{width:60px}

/* ── 형식 탭 ── */
.ftabs{display:inline-flex;gap:0;margin-bottom:12px}
.ftab{padding:6px 16px;border:1px solid #282828;background:#141414;color:#777;font-size:12px;cursor:pointer;font-weight:500}
.ftab:first-child{border-radius:6px 0 0 6px}
.ftab:last-child{border-radius:0 6px 6px 0}
.ftab.on{background:#ff4444;border-color:#ff4444;color:#fff}

/* ── 고급필터 ── */
.adv-btn{display:inline-flex;align-items:center;gap:4px;padding:6px 12px;border:1px solid #282828;border-radius:6px;background:#141414;color:#777;font-size:12px;cursor:pointer;margin-bottom:10px}
.adv-btn:hover{border-color:#444;color:#aaa}
.adv-btn .arr{font-size:9px;transition:transform .2s}
.adv-btn.open .arr{transform:rotate(180deg)}
.adv{display:none;background:#111;border:1px solid #1e1e1e;border-radius:10px;padding:16px;margin-bottom:14px}
.adv.show{display:block}
.adv-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px 20px}
@media(max-width:640px){.adv-grid{grid-template-columns:1fr}}
.adv-sec h4{font-size:12px;color:#666;margin-bottom:6px;font-weight:600}
.adv-r{display:flex;align-items:center;gap:6px;margin-bottom:6px}
.adv-r label{font-size:12px;color:#999;min-width:80px}
.adv-r select,.adv-r input{padding:6px 8px;border:1px solid #282828;border-radius:6px;background:#1a1a1a;color:#ddd;font-size:12px;outline:none;flex:1}
.tog{display:flex;align-items:center;justify-content:space-between;padding:4px 0}
.tog span{font-size:12px;color:#999}
.sw{position:relative;width:36px;height:20px;flex-shrink:0}
.sw input{opacity:0;width:0;height:0}
.sl{position:absolute;cursor:pointer;inset:0;background:#333;border-radius:20px;transition:.2s}
.sl:before{content:"";position:absolute;height:14px;width:14px;left:3px;bottom:3px;background:#888;border-radius:50%;transition:.2s}
.sw input:checked+.sl{background:#ff4444}
.sw input:checked+.sl:before{transform:translateX(16px);background:#fff}
.adv-reset{margin-top:10px;padding:6px 14px;border:1px solid #333;border-radius:6px;background:transparent;color:#666;font-size:11px;cursor:pointer}
.adv-reset:hover{border-color:#ff4444;color:#ff4444}
.adv-note{font-size:10px;color:#444;margin-top:3px}

/* ── 상태 ── */
.status{text-align:center;padding:30px;color:#444;font-size:13px}
.status.ld{color:#ff4444}
.sp{display:inline-block;width:16px;height:16px;border:2px solid #333;border-top-color:#ff4444;border-radius:50%;animation:spin .7s linear infinite;vertical-align:middle;margin-right:6px}
@keyframes spin{to{transform:rotate(360deg)}}

/* ── 결과 ── */
.rbar{display:flex;justify-content:space-between;align-items:center;margin:12px 0}
.rbar h2{font-size:13px;color:#666;font-weight:500}
.bgrp{display:flex;gap:4px}
.bo{padding:6px 12px;border:1px solid #ff4444;border-radius:6px;background:transparent;color:#ff4444;font-size:11px;cursor:pointer;font-weight:500}
.bo:hover{background:#ff4444;color:#fff}

/* ── 비디오 카드 ── */
.vc{display:flex;gap:12px;padding:12px;border-radius:8px;background:#141414;margin-bottom:6px;border:1px solid transparent;cursor:pointer;transition:all .12s}
.vc:hover{background:#1a1a1a;border-color:#252525}
.vchk{display:flex;align-items:center}
.vchk input{width:15px;height:15px;accent-color:#ff4444;cursor:pointer}
.vrk{font-size:16px;font-weight:800;color:#333;min-width:28px;display:flex;align-items:center;justify-content:center}
.vrk.t{color:#ff4444}
.vth{width:150px;min-width:150px;height:84px;border-radius:6px;object-fit:cover;background:#1e1e1e}
.vinf{flex:1;min-width:0;display:flex;flex-direction:column;justify-content:center;gap:4px}
.vtt{font-size:13px;font-weight:600;color:#eee;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;line-height:1.4}
.vm{font-size:11px;color:#666;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.vm .vw{color:#ff8888;font-weight:700}
.vm .ch{color:#888}

/* 메트릭스 영역 */
.vmetrics{display:flex;gap:8px;align-items:center;margin-top:2px}
.metric{display:flex;flex-direction:column;align-items:center;padding:4px 8px;border-radius:6px;background:#1a1a1a;min-width:56px}
.metric .val{font-size:12px;font-weight:700;color:#fff}
.metric .lbl{font-size:9px;color:#555;margin-top:1px}
.metric.speed .val{color:#4fc3f7}
.metric.score .val{color:#ffb74d}

/* 상태 뱃지 */
.badge{padding:2px 7px;border-radius:8px;font-size:10px;font-weight:600}
.b-new{background:#1565c0;color:#90caf9}
.b-rising{background:#b71c1c;color:#ef9a9a}
.b-falling{background:#263238;color:#78909c}
.b-steady{background:#1b5e20;color:#a5d6a7}

/* ── URL 박스 ── */
.ubox{margin-top:14px;padding:12px;background:#0c0c0c;border:1px solid #1e1e1e;border-radius:8px}
.ubox h3{font-size:12px;color:#666;margin-bottom:6px}
.ubox pre{font-size:11px;color:#4fc3f7;white-space:pre-wrap;word-break:break-all;line-height:1.5}

.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(20px);background:#ff4444;color:#fff;padding:8px 20px;border-radius:6px;font-size:12px;z-index:999;opacity:0;transition:all .25s}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
</style>
</head>
<body>

<div class="header">
  <span class="dot">&#9654;</span>
  <h1>YouTube Finder</h1>
</div>

<div class="wrap">

  <!-- 검색 -->
  <div class="search-row">
    <input type="text" id="q" placeholder="검색어 입력 또는 카테고리 클릭...">
    <button class="btn-s" id="sbtn" onclick="doSearch()">검색</button>
  </div>

  <!-- 필터 -->
  <div class="fbar">
    <div class="fg"><label>국가</label>
      <select id="country"><option value="KR" selected>한국</option><option value="US">미국</option><option value="JP">일본</option></select>
    </div>
    <div class="fg"><label>기간</label>
      <select id="period"><option value="all">전체</option><option value="hour">1시간</option><option value="today">오늘</option><option value="week" selected>이번 주</option><option value="month">이번 달</option><option value="year">올해</option></select>
    </div>
    <div class="fg"><label>정렬</label>
      <select id="sort"><option value="views" selected>조회수</option><option value="latest">최신</option><option value="trending">급상승</option></select>
    </div>
    <div class="fg"><label>결과</label><input type="number" id="cnt" value="15" min="1" max="50"></div>
  </div>

  <!-- 형식 -->
  <div class="ftabs" id="ftabs">
    <div class="ftab on" data-f="long">롱폼</div>
    <div class="ftab" data-f="shorts">쇼츠</div>
    <div class="ftab" data-f="all">전체</div>
  </div>

  <!-- 고급 -->
  <div class="adv-btn" id="abtn" onclick="togAdv()"><span class="arr">&#9660;</span> 고급 필터</div>
  <div class="adv" id="apnl">
    <div class="adv-grid">
      <div class="adv-sec">
        <h4>비교시간</h4>
        <div class="adv-r"><label>기준</label>
          <select id="cmpT">
            <option value="0">사용 안 함</option><option value="1">1시간</option><option value="3">3시간</option>
            <option value="6">6시간</option><option value="12">12시간</option><option value="24" selected>24시간</option>
            <option value="custom">직접 입력</option>
          </select>
        </div>
        <div class="adv-r" id="cmpCR" style="display:none"><label>시간(h)</label><input type="number" id="cmpCV" value="48" min="1"></div>
        <h4 style="margin-top:10px">상태</h4>
        <div class="adv-r"><label>필터</label>
          <select id="stF">
            <option value="all" selected>전체</option><option value="new">신규</option><option value="rising">상승</option>
            <option value="falling">하락</option><option value="steady">유지</option>
          </select>
        </div>
        <p class="adv-note">* 조회수÷시간 비율 기반 추정</p>
      </div>
      <div class="adv-sec">
        <h4>임계값</h4>
        <div class="adv-r"><label>최소 조회수</label><input type="number" id="minV" value="0" min="0" step="1000"></div>
        <div class="adv-r"><label>업로드 이내</label>
          <div style="display:flex;align-items:center;gap:4px;flex:1"><input type="number" id="upW" value="0" min="0" style="flex:1"><span style="font-size:11px;color:#666">시간</span></div>
        </div>
        <p class="adv-note">* 0 = 제한 없음</p>
        <h4 style="margin-top:10px">제외 조건</h4>
        <div class="tog"><span>대형채널 제외</span><label class="sw"><input type="checkbox" id="xB"><span class="sl"></span></label></div>
        <div class="tog"><span>대기업 제외</span><label class="sw"><input type="checkbox" id="xC"><span class="sl"></span></label></div>
        <div class="tog"><span>방송사 제외</span><label class="sw"><input type="checkbox" id="xR"><span class="sl"></span></label></div>
        <div class="tog"><span>중복 채널 제거</span><label class="sw"><input type="checkbox" id="dd" checked><span class="sl"></span></label></div>
      </div>
    </div>
    <button class="adv-reset" onclick="rstAdv()">고급 필터 초기화</button>
  </div>

  <!-- 상태 -->
  <div id="st" class="status">카테고리를 선택하거나 검색어를 입력하세요</div>

  <!-- 결과 -->
  <div id="res" style="display:none">
    <div class="rbar">
      <h2 id="rinfo"></h2>
      <div class="bgrp">
        <button class="bo" onclick="cpSel()">선택 URL 복사</button>
        <button class="bo" onclick="cpAll()">전체 URL 복사</button>
      </div>
    </div>
    <div id="vlist"></div>
    <div class="ubox" id="ubox" style="display:none">
      <h3>collect.py 명령어</h3>
      <pre id="upre"></pre>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
let results=[],curFmt='long';

// 형식탭
document.querySelectorAll('.ftab').forEach(t=>{
  t.onclick=()=>{document.querySelectorAll('.ftab').forEach(x=>x.classList.remove('on'));t.classList.add('on');curFmt=t.dataset.f}
});

document.getElementById('q').addEventListener('keydown',e=>{if(e.key==='Enter')doSearch()});
document.getElementById('cmpT').addEventListener('change',function(){
  document.getElementById('cmpCR').style.display=this.value==='custom'?'flex':'none';
});

function togAdv(){document.getElementById('apnl').classList.toggle('show');document.getElementById('abtn').classList.toggle('open')}
function rstAdv(){
  document.getElementById('cmpT').value='24';document.getElementById('cmpCR').style.display='none';
  document.getElementById('cmpCV').value=48;document.getElementById('stF').value='all';
  document.getElementById('minV').value=0;document.getElementById('upW').value=0;
  document.getElementById('xB').checked=false;document.getElementById('xC').checked=false;
  document.getElementById('xR').checked=false;document.getElementById('dd').checked=true;
}

async function doSearch(){
  const q=document.getElementById('q').value.trim();
  if(!q)return;
  const btn=document.getElementById('sbtn');
  btn.disabled=true;btn.textContent='검색 중...';
  document.getElementById('res').style.display='none';
  const s=document.getElementById('st');
  s.style.display='block';s.className='status ld';
  s.innerHTML='<span class="sp"></span> YouTube 검색 + 메트릭 분석 중... (최대 30초)';

  let ch=document.getElementById('cmpT').value;
  if(ch==='custom')ch=document.getElementById('cmpCV').value||48;

  const p=new URLSearchParams({
    query:q,sort:document.getElementById('sort').value,
    period:document.getElementById('period').value,
    country:document.getElementById('country').value,
    fmt:curFmt,count:document.getElementById('cnt').value||15,
    min_views:document.getElementById('minV').value||0,
    upload_within:document.getElementById('upW').value||0,
    compare_hours:ch,status_filter:document.getElementById('stF').value,
    ex_broad:document.getElementById('xR').checked?1:0,
    ex_corp:document.getElementById('xC').checked?1:0,
    ex_big:document.getElementById('xB').checked?1:0,
    dedup:document.getElementById('dd').checked?1:0,
  });

  try{
    const r=await fetch('/api/search?'+p);const d=await r.json();
    if(d.error){s.className='status';s.textContent='오류: '+d.error;return}
    results=d.entries||[];render(d);
  }catch(e){s.className='status';s.textContent='오류: '+e.message}
  finally{btn.disabled=false;btn.textContent='검색'}
}

function fc(n){if(n==null)return'N/A';if(n>=1e8)return(n/1e8).toFixed(1)+'억';if(n>=1e4)return(n/1e4).toFixed(1)+'만';if(n>=1e3)return(n/1e3).toFixed(1)+'천';return String(n)}
function fd(s){if(!s)return'?';s=Math.round(s);const h=Math.floor(s/3600),m=Math.floor(s%3600/60),sec=s%60;if(h)return h+':'+String(m).padStart(2,'0')+':'+String(sec).padStart(2,'0');return m+':'+String(sec).padStart(2,'0')}
function fdate(d){return d&&d.length===8?d.slice(0,4)+'-'+d.slice(4,6)+'-'+d.slice(6,8):''}
function esc(s){return s?s.replace(/</g,'&lt;').replace(/>/g,'&gt;'):''}
function bcls(s){if(s==='신규')return'b-new';if(s==='상승')return'b-rising';if(s==='하락')return'b-falling';if(s==='유지')return'b-steady';return''}

function render(data){
  if(!results.length){document.getElementById('st').className='status';document.getElementById('st').textContent='결과 없음';document.getElementById('res').style.display='none';return}
  document.getElementById('st').style.display='none';
  document.getElementById('res').style.display='block';
  document.getElementById('rinfo').textContent=`${results.length}개 결과 (${data.total_fetched}개 검색 → ${data.after_filter}개 통과)`;

  const el=document.getElementById('vlist');el.innerHTML='';
  results.forEach((e,i)=>{
    const url=`https://www.youtube.com/watch?v=${e.id}`;
    const th=e.thumbnails&&e.thumbnails.length?e.thumbnails[e.thumbnails.length-1].url:'';
    const c=document.createElement('div');c.className='vc';
    c.innerHTML=`
      <div class="vchk"><input type="checkbox" data-url="${url}" checked></div>
      <div class="vrk ${i<3?'t':''}">${i+1}</div>
      ${th?`<img class="vth" src="${th}" loading="lazy">`:'<div class="vth"></div>'}
      <div class="vinf">
        <div class="vtt">${esc(e.title)}</div>
        <div class="vm">
          <span class="vw">조회수 ${fc(e.view_count)}</span>
          <span>${fd(e.duration)}</span>
          <span class="ch">${esc(e.channel)}${e.verified?' ✓':''}</span>
          ${e.upload_date?`<span>${fdate(e.upload_date)}</span>`:''}
          ${e.status?`<span class="badge ${bcls(e.status)}">${esc(e.status)}</span>`:''}
        </div>
        <div class="vmetrics">
          <div class="metric speed"><div class="val">${fc(e.vph)}/h</div><div class="lbl">속도</div></div>
          <div class="metric score"><div class="val">${e.score}</div><div class="lbl">상승지수</div></div>
        </div>
      </div>`;
    c.addEventListener('click',ev=>{if(ev.target.type==='checkbox')return;window.open(url,'_blank')});
    el.appendChild(c);
  });
  updCmd();
  el.querySelectorAll('input[type=checkbox]').forEach(cb=>cb.addEventListener('change',updCmd));
}

function gsel(){return Array.from(document.querySelectorAll('#vlist input:checked')).map(c=>c.dataset.url)}
function gall(){return results.map(e=>`https://www.youtube.com/watch?v=${e.id}`)}
function updCmd(){
  const u=gsel(),b=document.getElementById('ubox');
  if(!u.length){b.style.display='none';return}
  b.style.display='block';
  document.getElementById('upre').textContent=`python scripts/collect.py --project "프로젝트명" ${u.join(' ')}`;
}
function cpSel(){const u=gsel();if(!u.length)return tt('선택 없음');navigator.clipboard.writeText(u.join(' ')).then(()=>tt(u.length+'개 URL 복사'))}
function cpAll(){const u=gall();navigator.clipboard.writeText(u.join(' ')).then(()=>tt(u.length+'개 URL 복사'))}
function tt(m){const t=document.getElementById('toast');t.textContent=m;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2000)}
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", ""):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))

        elif parsed.path == "/api/search":
            params = parse_qs(parsed.query)
            query = params.get("query", [""])[0]
            if not query:
                self.send_json({"error": "검색어가 없습니다."})
                return

            kw = {
                "sort": params.get("sort", ["views"])[0],
                "period": params.get("period", ["week"])[0],
                "country": params.get("country", ["KR"])[0],
                "fmt": params.get("fmt", ["long"])[0],
                "count": int(params.get("count", ["15"])[0]),
                "min_views": int(params.get("min_views", ["0"])[0]),
                "upload_within": int(params.get("upload_within", ["0"])[0]),
                "compare_hours": int(params.get("compare_hours", ["24"])[0]),
                "status_filter": params.get("status_filter", ["all"])[0],
                "ex_broad": params.get("ex_broad", ["0"])[0] == "1",
                "ex_corp": params.get("ex_corp", ["0"])[0] == "1",
                "ex_big": params.get("ex_big", ["0"])[0] == "1",
                "dedup": params.get("dedup", ["1"])[0] == "1",
            }
            print(f"[검색] \"{query}\" {kw['sort']}/{kw['period']}/{kw['country']}")
            result = search_youtube(query, **kw)
            self.send_json(result)
        else:
            self.send_response(404)
            self.end_headers()

    def send_json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def log_message(self, *a):
        pass


def main():
    server = HTTPServer(("localhost", PORT), Handler)
    print(f"\nYouTube Finder v3")
    print(f"http://localhost:{PORT}")
    print("종료: Ctrl+C\n")
    threading.Timer(0.5, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n종료.")
        server.server_close()


if __name__ == "__main__":
    main()
