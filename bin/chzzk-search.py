#!/usr/bin/env python3
# 치지직 채널명 검색 → 목록에서 선택 → 선택한 channelId를 stdout으로 출력
# (메뉴/프롬프트는 stderr, 입력은 /dev/tty → `id=$(chzzk-search.py 검색어)` 형태로 사용 가능)
import sys, json
import requests

UA = "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/141.0"
API = "https://api.chzzk.naver.com/service/v1/search/channels"

def err(*a):
    print(*a, file=sys.stderr, flush=True)

def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        err("usage: chzzk-search.py <검색어>")
        sys.exit(2)
    keyword = " ".join(sys.argv[1:]).strip()

    try:
        r = requests.get(API, params={"keyword": keyword, "size": 12},
                         headers={"User-Agent": UA}, timeout=10)
        data = (r.json().get("content") or {}).get("data") or []
    except Exception as e:
        err(f"검색 실패: {e}")
        sys.exit(1)

    chans = [it.get("channel", {}) for it in data]
    chans = [c for c in chans if c.get("channelId")]
    if not chans:
        err(f"'{keyword}' 검색 결과가 없습니다.")
        sys.exit(1)

    # 라이브 중인 채널을 위로 정렬
    chans.sort(key=lambda c: (not c.get("openLive"), -(c.get("followerCount") or 0)))

    err(f"\n\033[1m'{keyword}' 검색 결과\033[0m")
    for i, c in enumerate(chans, 1):
        live = c.get("openLive")
        badge = "\033[91m● LIVE\033[0m" if live else "\033[90m· 오프라인\033[0m"
        fol = c.get("followerCount") or 0
        name = c.get("channelName", "")
        err(f"  {i:2d}. {badge}  \033[96m{name}\033[0m  (팔로워 {fol:,})")

    # 선택 입력: /dev/tty 우선, 없으면 stdin 폴백
    try:
        tty = open("/dev/tty")
    except Exception:
        tty = sys.stdin
    while True:
        err("\n번호 선택 [기본 1, q 취소]: ")
        line = tty.readline()
        if not line:
            sys.exit(1)
        s = line.strip().lower()
        if s in ("q", "quit", "exit"):
            err("취소되었습니다.")
            sys.exit(1)
        if s == "":
            s = "1"
        if s.isdigit() and 1 <= int(s) <= len(chans):
            chosen = chans[int(s) - 1]
            if not chosen.get("openLive"):
                err(f"\033[93m※ '{chosen.get('channelName')}' 는 지금 방송 중이 아닙니다. 재생이 안 될 수 있어요.\033[0m")
            print(chosen["channelId"])  # ← stdout: 선택된 channelId
            return
        err("잘못된 입력입니다.")

if __name__ == "__main__":
    main()
