#!/usr/bin/env bash
# chzzk-cli 설치 스크립트: ~/.local/bin 에 도구를 설치하고, PATH/설정을 준비한다.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
MPV_CONF_DIR="$HOME/.config/mpv"

echo "== 1. 의존성 확인 =="
missing=()
command -v mpv >/dev/null || missing+=("mpv")
command -v yt-dlp >/dev/null || missing+=("yt-dlp")
command -v python3 >/dev/null || missing+=("python3")
command -v xfce4-terminal >/dev/null || echo "  ※ xfce4-terminal 없음: xterm으로 대체되거나(있으면) 채팅이 현재 창에 출력됨"

py_missing=()
python3 -c "import requests" 2>/dev/null || py_missing+=("python3-requests")
python3 -c "import websockets" 2>/dev/null || py_missing+=("python3-websockets")

if [ "${#missing[@]}" -gt 0 ] || [ "${#py_missing[@]}" -gt 0 ]; then
  pkgs=("${missing[@]}" "${py_missing[@]}")
  echo "  누락된 패키지: ${pkgs[*]}"
  read -r -p "  지금 'sudo apt install -y ${pkgs[*]}' 실행할까요? [Y/n] " ans
  if [ -z "${ans:-}" ] || [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
    sudo apt update && sudo apt install -y "${pkgs[@]}"
  else
    echo "  건너뜀. 나중에 직접 설치: sudo apt install -y ${pkgs[*]}"
  fi
else
  echo "  필수 의존성 모두 설치되어 있음"
fi

echo "== 2. 스크립트 설치 =="
mkdir -p "$BIN_DIR"
install -m 755 "$REPO_DIR"/bin/chzzk-watch "$BIN_DIR"/chzzk-watch
install -m 755 "$REPO_DIR"/bin/chzzk-chat.py "$BIN_DIR"/chzzk-chat.py
install -m 755 "$REPO_DIR"/bin/chzzk-search.py "$BIN_DIR"/chzzk-search.py
install -m 755 "$REPO_DIR"/bin/chzzk-login.py "$BIN_DIR"/chzzk-login.py
ln -sf "$BIN_DIR"/chzzk-watch "$BIN_DIR"/chzzk
echo "  설치됨: $BIN_DIR/{chzzk-watch,chzzk-chat.py,chzzk-search.py,chzzk-login.py,chzzk→chzzk-watch}"

echo "== 3. PATH 설정 =="
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  if ! grep -qsF "$BIN_DIR" "$HOME/.bashrc" 2>/dev/null; then
    echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$HOME/.bashrc"
    echo "  ~/.bashrc 에 PATH 추가함 (새 터미널부터 적용, 또는 'source ~/.bashrc')"
  fi
else
  echo "  이미 PATH에 있음"
fi

echo "== 4. mpv 설정 =="
mkdir -p "$MPV_CONF_DIR"
if [ -f "$MPV_CONF_DIR/mpv.conf" ]; then
  echo "  기존 $MPV_CONF_DIR/mpv.conf 있음 → 덮어쓰지 않음"
  echo "  하드웨어 디코딩/버퍼 설정은 $REPO_DIR/config/mpv.conf.example 참고해서 직접 병합하세요"
else
  cp "$REPO_DIR/config/mpv.conf.example" "$MPV_CONF_DIR/mpv.conf"
  echo "  $MPV_CONF_DIR/mpv.conf 생성함"
fi

echo
echo "설치 완료. 새 터미널을 열거나 'source ~/.bashrc' 후 다음을 실행해보세요:"
echo "  chzzk <채널명 또는 URL>"
