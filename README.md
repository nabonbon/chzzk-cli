# chzzk-cli

저사양 리눅스 PC에서 [치지직(CHZZK)](https://chzzk.naver.com)을 브라우저 없이 터미널에서 시청하는 도구 모음.
`mpv` 하드웨어 디코딩으로 CPU 사용량을 크게 줄이고, 영상 재생·채팅 표시/전송·채널 검색·화질/지연 선택을
명령 하나(`chzzk`)로 처리한다.

## 왜 필요한가

오래된 내장 GPU(예: Intel Haswell 세대)는 H.264 외 코덱(HEVC/VP9/AV1)을 하드웨어로 디코딩하지 못한다.
브라우저로 그런 방송을 보면 소프트웨어 디코딩으로 CPU 사용률이 치솟는다. 치지직은 스트리머가 송출한
코덱을 그대로 통과(passthrough)시키므로, 방송마다 하드웨어 디코딩 가능 여부가 다르다.

`mpv`로 재생하면 지원되는 코덱(대부분 H.264)에 한해 GPU 하드웨어 디코딩이 확실히 걸리고,
브라우저보다 오버헤드도 적다. 이 저장소는 그 mpv 설정과, 브라우저 없이도 불편함 없게 채팅·검색까지
붙인 래퍼 스크립트를 담고 있다.

## 기능

- `mpv` + VAAPI 하드웨어 디코딩으로 재생 (지원 코덱: 사용 중인 GPU/드라이버에 따라 다름, 아래 진단 참고)
- 채널명으로 검색 → 라이브 우선 목록에서 선택
- 화질(`-q`) / 지연모드(`-l`) 선택, 값 생략 시 대화형 메뉴
- 채팅을 별도 터미널 창에 실시간 표시 (익명 읽기 전용, 이모티콘 치환)
- 로그인 쿠키를 등록하면 같은 창에서 채팅 **전송**도 가능 (하단 고정 입력줄)
- 추가 런타임 의존성 없음 (`python3` + `requests` + `websockets`만 사용)

## 요구 사항

- Linux (X11 데스크톱, `xfce4-terminal` 또는 `xterm` — 채팅 팝업 창용)
- `mpv`, `yt-dlp`, `python3`, `python3-requests`, `python3-websockets`
- VAAPI/VDPAU 하드웨어 디코딩이 되는 GPU (안 되면 그냥 소프트웨어 디코딩으로 동작은 함)

## 설치

```bash
git clone https://github.com/nabonbon/chzzk-cli.git
cd chzzk-cli
./install.sh
```

`install.sh`가 하는 일:
1. 의존성 확인 후, 없으면 설치 여부를 물어보고 `apt install` 실행
2. 스크립트를 `~/.local/bin`에 설치, `chzzk` 심볼릭 링크 생성
3. `~/.bashrc`에 `~/.local/bin` PATH 추가 (없을 때만)
4. `~/.config/mpv/mpv.conf`가 없으면 `config/mpv.conf.example`을 복사 (있으면 덮어쓰지 않음)

설치 후 새 터미널을 열거나 `source ~/.bashrc`.

## 사용법

```
chzzk [-q 1080|720|480] [-l 일반|저지연] <채널ID | URL | 채널명 검색어>
chzzk -set     # 채팅 전송용 로그인 쿠키 등록 (대화형)
chzzk -i       # 현재 로그인 등록 상태 확인
```

| 옵션 | 값 | 설명 |
|------|-----|------|
| `-q`, `--quality` | `1080` / `720` / `480` | 해상도 (생략=최고화질, 값 없이 `-q`=대화형 선택) |
| `-l`, `--latency` | `일반`(normal) / `저지연`(low) | 지연모드 (생략=일반, 값 없이 `-l`=대화형) |
| `-set` | – | 채팅 전송용 네이버 로그인 쿠키 등록 (NID_AUT → NID_SES 순서로 대화형 입력) |
| `-i`, `--info` | – | 현재 로그인 쿠키 등록 상태 확인 (값은 마스킹 표시) |

```bash
chzzk 풍월량                     # 검색 → 목록에서 선택, 최고화질·일반
chzzk -q 720 풍월량              # 720p·일반 (저사양 권장)
chzzk -q 720 -l 저지연 풍월량    # 720p·저지연
chzzk https://chzzk.naver.com/live/<채널ID>   # URL 직접
```

인자가 hex 채널 ID나 URL이면 바로 재생하고, 그 외 텍스트는 채널 검색 후 목록에서 선택한다.
재생과 동시에 채팅 팝업 창이 뜨고, mpv를 닫으면 같이 종료된다.

## 채팅 전송 (선택 기능)

기본은 익명 읽기 전용이다. 실제로 타이핑해서 보내려면:

```bash
chzzk -set   # NID_AUT 값 입력 → NID_SES 값 입력 (비밀번호처럼 화면에 표시 안 됨)
```

쿠키는 브라우저로 `chzzk.naver.com`에 로그인한 뒤 F12(개발자도구) → Application/저장공간 →
Cookies → `https://chzzk.naver.com`에서 `NID_AUT`, `NID_SES` 값을 복사하면 된다.
`~/.config/chzzk/cookies.json`에 `chmod 600`으로 저장되며, 등록 후에는 채팅 창 하단에
`채팅 입력:` 줄이 고정되어 그대로 타이핑 후 Enter로 전송된다.

> **주의**: `NID_AUT`/`NID_SES`는 네이버 로그인 세션 자체다(비밀번호와 동급). 절대 다른 사람과
> 공유하거나 다른 곳에 붙여넣지 말 것. 유출되면 그 계정으로 글쓰기/채팅이 가능해진다.
> 자동 갱신 방법은 없어서 만료되면 브라우저에서 다시 복사해야 한다. 자동화·도배 용도가 아니라
> 사람이 직접 치는 용도로만 사용할 것 — 짧은 시간에 반복 전송하면 계정이 일시 채팅 제한될 수 있다.

## 하드웨어 디코딩 확인

```bash
lspci -nn | grep -Ei 'vga|3d|display'                # GPU 확인
vainfo | grep -Ei 'VAProfile.*(H264|HEVC|VP9|AV1)'   # 지원 코덱 확인
```

재생 중 mpv에서 `i` 키 → 통계 오버레이의 `Hardware Decoder` 값으로 실제 적용 여부 확인 가능.
특정 방송의 코덱은 `yt-dlp -F "<라이브 URL>"`의 `VCODEC` 열로 확인 (`avc1`=H.264, `hev1`/`hvc1`=H.265, `av01`=AV1).

`config/mpv.conf.example`에는 하드웨어 디코딩(`hwdec=auto-safe`)과, 라이브 스트림에서 네트워크가
흔들려도 버티도록 한 버퍼 설정이 들어있다. **`profile=low-latency`는 의도적으로 사용하지 않는다** —
`audio-buffer=0` 등 극단적인 값이 들어있어 인터넷 스트림에서 오디오 언더런·싱크 밀림을 유발하기 때문에,
저지연 모드는 짧지만 0은 아닌 버퍼(`demuxer-readahead-secs=3`)로 직접 구성했다.

## 트러블슈팅

| 증상 | 원인 / 해결 |
|------|-------------|
| `chzzk: command not found` | `~/.local/bin`이 PATH에 없음 → 새 터미널 또는 `source ~/.bashrc` |
| 특정 방송에서 CPU 폭등 | 그 방송이 HEVC 등 미지원 코덱으로 송출 중 → `-q` 로 하위 화질 선택 |
| 멈출 때 CPU 100% | 디코딩/렌더 부하 → 화질 낮추기 |
| 멈추는데 CPU는 여유 | 네트워크 문제 → `-l 일반`으로 버퍼 확보 |
| 채팅 입력했는데 전송이 안 됨 | `chzzk -i`로 로그인 여부 확인 → 안 됐으면 `chzzk -set` |
| 로그인했는데 계속 읽기전용 | 쿠키 만료 → 브라우저에서 재로그인 후 `chzzk -set` 재등록 |

## 동작 원리 (요약)

- 영상: `yt-dlp`가 뽑아준 HLS 스트림 URL을 mpv가 재생 (`--ytdl-format`으로 화질/지연 프로파일 선택)
- 채팅 수신: 비공식 API로 `chatChannelId`·접속 토큰을 받아 `wss://kr-ss{1..10}.chat.naver.com/chat`에 연결
- 채팅 전송: 로그인 쿠키(Cookie 헤더)로 발급받은 토큰으로 `auth: "SEND"` 접속 후 cmd `3101` 프레임 전송 —
  서버가 이를 다시 `93101`로 전체 브로드캐스트하므로 자기 메시지도 같은 수신 루프에 표시됨

## 주의사항 (비공식 도구)

이 도구는 치지직의 **비공식/문서화되지 않은 API**를 사용한다. 네이버/치지직과 무관하며,
API가 바뀌면 언제든 동작하지 않을 수 있다. 어디까지나 개인 시청 편의용으로 만들었고,
자동화된 대량 요청·도배 목적으로 사용하지 않기를 권한다.

## 참고 자료 / Acknowledgments

채팅 **전송** 기능(로그인 쿠키 인증 흐름, access-token 발급, 웹소켓 CONNECT/SEND_CHAT 프레임 구조)은
직접 알아낸 게 아니라 아래 오픈소스 프로젝트의 소스 코드를 읽고 리버스엔지니어링해서 구현했다:

- [gunyu1019/chzzkpy](https://github.com/gunyu1019/chzzkpy) — MIT License.
  `NID_AUT`/`NID_SES` 쿠키 인증, `getUserStatus`로 `userIdHash` 조회, access-token 요청 시
  Cookie 헤더 첨부, 웹소켓 `auth: "SEND"` 접속과 채팅 전송 cmd(`3101`, 수신용 `93101`과 별개) 구조를
  이 라이브러리의 `chzzkpy/unofficial/chat/{chat_client,gateway,http}.py`에서 확인했다.

이 저장소는 chzzkpy의 코드를 그대로 가져다 쓰지 않고 프로토콜 이해 목적으로만 참고했지만,
그 코드가 없었다면 비공개 프로토콜을 이만큼 빠르게 파악하기 어려웠을 것이다.

## 라이선스

[MIT](LICENSE)
