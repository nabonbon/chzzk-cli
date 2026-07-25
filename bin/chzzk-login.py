#!/usr/bin/env python3
# 치지직 채팅 "전송" 기능용 네이버 로그인 쿠키 저장/삭제/상태 확인
#
# 사용법:
#   chzzk -set                               # 대화형으로 NID_AUT → NID_SES 순서 입력 (권장)
#   chzzk-login.py --set                     # 위와 동일 (직접 호출)
#   chzzk-login.py <NID_AUT값> <NID_SES값>   # 인자로 바로 저장 (셸 히스토리에 남을 수 있음)
#   chzzk-login.py --status                  # 저장 여부 확인 (값은 마스킹)
#   chzzk-login.py --clear                   # 삭제
#
# 쿠키 얻는 법: 브라우저로 chzzk.naver.com 로그인 후
#   F12(개발자도구) → Application/저장공간 → Cookies → https://chzzk.naver.com
#   에서 NID_AUT, NID_SES 값을 복사.
#
# 주의: 이 값은 네이버 계정 로그인 세션 자체다. 유출되면 그 계정으로
# 글쓰기/채팅이 가능해지므로 절대 다른 곳에 붙여넣거나 공유하지 말 것.
import getpass
import json
import os
import sys

CONFIG_DIR = os.path.expanduser("~/.config/chzzk")
COOKIE_PATH = os.path.join(CONFIG_DIR, "cookies.json")


def mask(v):
    return v[:4] + "…" + v[-4:] if len(v) > 8 else "****"


def save(nid_aut, nid_ses):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    fd = os.open(COOKIE_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"NID_AUT": nid_aut, "NID_SES": nid_ses}, f)
    os.chmod(COOKIE_PATH, 0o600)
    print(f"저장됨: {COOKIE_PATH} (permission 600)")
    print(f"  NID_AUT={mask(nid_aut)}  NID_SES={mask(nid_ses)}")


def status():
    if not os.path.exists(COOKIE_PATH):
        print("로그인 안 됨 (쿠키 파일 없음)")
        return
    with open(COOKIE_PATH) as f:
        c = json.load(f)
    print(f"로그인 상태: {COOKIE_PATH}")
    print(f"  NID_AUT={mask(c.get('NID_AUT', ''))}  NID_SES={mask(c.get('NID_SES', ''))}")


def interactive_set():
    print("치지직 채팅 전송용 로그인 쿠키 등록")
    print("브라우저로 chzzk.naver.com 로그인 후 F12 → Application/저장공간 → Cookies 에서 값 복사")
    print("(입력한 값은 화면에 표시되지 않습니다)\n")
    nid_aut = getpass.getpass("NID_AUT 값 입력: ").strip()
    if not nid_aut:
        print("NID_AUT 값이 비어있어 취소합니다.", file=sys.stderr)
        sys.exit(1)
    nid_ses = getpass.getpass("NID_SES 값 입력: ").strip()
    if not nid_ses:
        print("NID_SES 값이 비어있어 취소합니다.", file=sys.stderr)
        sys.exit(1)
    save(nid_aut, nid_ses)


def clear():
    if os.path.exists(COOKIE_PATH):
        os.remove(COOKIE_PATH)
        print("삭제됨")
    else:
        print("이미 로그인 안 된 상태입니다")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    if args[0] == "--set":
        interactive_set()
    elif args[0] == "--status":
        status()
    elif args[0] == "--clear":
        clear()
    elif len(args) == 2:
        save(args[0], args[1])
    else:
        print("usage: chzzk-login.py --set | <NID_AUT> <NID_SES> | --status | --clear", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
