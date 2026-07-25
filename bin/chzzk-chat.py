#!/usr/bin/env python3
# 치지직 라이브 채팅을 터미널에 출력. 기본은 익명 읽기 전용이지만
# chzzk-login.py로 로그인 쿠키를 저장해두면 터미널에서 입력한 메시지를 전송한다.
#
# 로그인 인증 흐름과 웹소켓 전송(SEND) 프레임 구조는 오픈소스 gunyu1019/chzzkpy(MIT)의
# chzzkpy/unofficial/chat/{chat_client,gateway,http}.py 를 참고해 리버스엔지니어링함.
# https://github.com/gunyu1019/chzzkpy
import sys, os, json, re, time, shutil, asyncio, signal
import requests
import websockets

UA = "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/141.0"
GAME_API = "https://comm-api.game.naver.com/nng_main"
CHZZK_API = "https://api.chzzk.naver.com"
COOKIE_PATH = os.path.expanduser("~/.config/chzzk/cookies.json")

# ChatCmd
PING, PONG = 0, 10000
CONNECT, CONNECTED = 100, 10100
REQ_RECENT, RECENT = 5101, 15101
CHAT, DONATION = 93101, 93102
SEND_CHAT = 3101

EMOJI_RE = re.compile(r"\{:[^:}]+:\}")
INPUT_PROMPT = "채팅 입력: "

_pinned = False  # 로그인 상태에서만 하단 고정 입력줄 사용

def _term_size():
    cols, rows = shutil.get_terminal_size(fallback=(80, 24))
    return cols, rows

def _pinned_setup():
    """화면 마지막 줄을 스크롤 영역 밖으로 빼서 입력줄로 고정한다."""
    global _pinned
    _, rows = _term_size()
    sys.stdout.write(f"\033[1;{rows - 1}r")  # 스크롤 영역 = 1~(rows-1)번째 줄
    _pinned = True
    _pinned_redraw_prompt()

def _pinned_teardown():
    global _pinned
    if not _pinned:
        return
    _, rows = _term_size()
    sys.stdout.write("\033[r")  # 스크롤 영역 해제(전체 화면으로 복귀)
    sys.stdout.write(f"\033[{rows};1H\n")
    sys.stdout.flush()
    _pinned = False

def _pinned_redraw_prompt():
    if not _pinned:
        return
    _, rows = _term_size()
    sys.stdout.write(f"\033[{rows};1H\033[2K{INPUT_PROMPT}")
    sys.stdout.flush()

def log(msg):
    if not _pinned:
        print(msg, flush=True)
        return
    _, rows = _term_size()
    # 커서를 저장하고 스크롤 영역 마지막 줄로 이동해 출력한 뒤, 입력줄로 복귀
    sys.stdout.write("\0337")
    sys.stdout.write(f"\033[{rows - 1};1H\033[2K{msg}\n")
    sys.stdout.write("\0338")
    sys.stdout.flush()

def load_login():
    """저장된 NID_AUT/NID_SES 쿠키를 읽어 Cookie 헤더 문자열로 반환. 없으면 None."""
    if not os.path.exists(COOKIE_PATH):
        return None
    try:
        with open(COOKIE_PATH) as f:
            c = json.load(f)
        return f"NID_AUT={c['NID_AUT']}; NID_SES={c['NID_SES']}"
    except Exception:
        return None

def get_chat_channel_id(channel_id):
    r = requests.get(f"{CHZZK_API}/service/v2/channels/{channel_id}/live-detail",
                     headers={"User-Agent": UA}, timeout=10)
    c = r.json().get("content") or {}
    if c.get("status") != "OPEN":
        log("※ 방송이 진행 중이 아닙니다 (status=%s)" % c.get("status"))
    title = c.get("liveTitle", "")
    ccid = c.get("chatChannelId")
    if not ccid:
        raise SystemExit("chatChannelId를 찾을 수 없습니다 (채팅 비활성/방송 종료).")
    return ccid, title

def get_user_id_hash(cookie):
    """로그인 쿠키로 내 userIdHash 조회 (전송 모드에 필요)."""
    r = requests.get(f"{GAME_API}/v1/user/getUserStatus",
                     headers={"User-Agent": UA, "Cookie": cookie}, timeout=10)
    c = r.json().get("content") or {}
    if not c.get("loggedIn", True):
        return None
    return c.get("userIdHash")

def get_access_token(chat_channel_id, cookie=None):
    headers = {"User-Agent": UA}
    if cookie:
        headers["Cookie"] = cookie
    r = requests.get(f"{GAME_API}/v1/chats/access-token",
                     params={"channelId": chat_channel_id, "chatType": "STREAMING"},
                     headers=headers, timeout=10)
    c = r.json()["content"]
    return c["accessToken"], c["extraToken"]

def parse_msg(m, donation=False):
    prof = m.get("profile")
    nick = "익명"
    if prof:
        try:
            nick = (json.loads(prof) if isinstance(prof, str) else prof).get("nickname", nick)
        except Exception:
            pass
    text = m.get("msg") or m.get("content") or ""
    text = EMOJI_RE.sub("[이모티콘]", text)
    if donation:
        amount = ""
        extras = m.get("extras")
        try:
            ex = json.loads(extras) if isinstance(extras, str) else (extras or {})
            amount = ex.get("payAmount", "")
        except Exception:
            pass
        return f"\033[93m💰 {nick} 후원 {amount}: {text}\033[0m"
    return f"\033[96m{nick}\033[0m: {text}"

async def stdin_sender(ws, ccid, sid_box, tid_box):
    """터미널에 입력한 줄을 채팅으로 전송 (로그인된 경우에만 호출됨)."""
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    while True:
        line = await reader.readline()
        if not line:
            break
        text = line.decode(errors="ignore").strip()
        _pinned_redraw_prompt()
        if not text:
            continue
        if sid_box[0] is None:
            log("  ※ 아직 연결 중입니다. 잠시 후 다시 시도하세요.")
            continue
        extras = json.dumps({
            "chatType": "STREAMING", "emojis": "", "osType": "PC",
            "streamingChannelId": ccid,
        })
        tid_box[0] += 1
        await ws.send(json.dumps({
            "ver": "2", "cmd": SEND_CHAT, "svcid": "game", "cid": ccid, "sid": sid_box[0],
            "bdy": {
                "msg": text, "msgTime": int(time.time() * 1000),
                "msgTypeCode": 1, "extras": extras,
            },
            "retry": False, "tid": tid_box[0],
        }))

async def run(channel_id):
    ccid, title = get_chat_channel_id(channel_id)
    cookie = load_login()
    uid = get_user_id_hash(cookie) if cookie else None
    token, _extra = get_access_token(ccid, cookie if uid else None)
    log(f"\033[1m● {title}\033[0m")
    if uid:
        log("  \033[92m● 로그인됨 — 메시지를 입력하면 전송됩니다.\033[0m")
    else:
        log("  익명 읽기 전용 (전송하려면 chzzk-login.py 참고)")
    log(f"  채팅 연결 중... (cid={ccid})\n")

    last_err = None
    for n in range(1, 11):  # kr-ss1 ~ kr-ss10 중 접속되는 서버 사용
        url = f"wss://kr-ss{n}.chat.naver.com/chat"
        try:
            async with websockets.connect(url, ping_interval=None,
                                          subprotocols=["chat"], max_size=None) as ws:
                await ws.send(json.dumps({
                    "ver": "2", "cmd": CONNECT, "svcid": "game", "cid": ccid,
                    "bdy": {"uid": uid, "devType": 2001, "accTkn": token,
                            "auth": "SEND" if uid else "READ"},
                    "tid": 1,
                }))
                sid_box = [None]
                tid_box = [1]
                async def keepalive():
                    while True:
                        await asyncio.sleep(20)
                        await ws.send(json.dumps({"ver": "2", "cmd": PING}))
                ka = asyncio.create_task(keepalive())
                sender = asyncio.create_task(stdin_sender(ws, ccid, sid_box, tid_box)) if uid else None
                try:
                    async for raw in ws:
                        f = json.loads(raw)
                        cmd = f.get("cmd")
                        bdy = f.get("bdy")
                        if cmd == CONNECTED:
                            sid_box[0] = (bdy or {}).get("sid")
                            tid_box[0] = 2
                            await ws.send(json.dumps({
                                "ver": "2", "cmd": REQ_RECENT, "svcid": "game",
                                "cid": ccid, "sid": sid_box[0],
                                "bdy": {"recentMessageCount": 30}, "tid": tid_box[0],
                            }))
                            log("  \033[92m✓ 연결됨 (kr-ss%d)\033[0m\n" % n)
                            if uid:
                                _pinned_setup()
                        elif cmd == PING:
                            await ws.send(json.dumps({"ver": "2", "cmd": PONG}))
                        elif cmd in (CHAT, RECENT, DONATION):
                            msgs = bdy.get("messageList", []) if isinstance(bdy, dict) else (bdy or [])
                            for m in msgs:
                                log(parse_msg(m, donation=(cmd == DONATION)))
                finally:
                    ka.cancel()
                    if sender:
                        sender.cancel()
            return
        except Exception as e:
            _pinned_teardown()
            last_err = e
            continue
    raise SystemExit(f"채팅 서버 접속 실패: {last_err}")

def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: chzzk-chat.py <채널ID>")
    cid = sys.argv[1]
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    try:
        asyncio.run(run(cid))
    except KeyboardInterrupt:
        pass
    finally:
        _pinned_teardown()

if __name__ == "__main__":
    main()
