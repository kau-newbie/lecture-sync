# lecture-sync

강의자료 폴더에 새 파일이 들어오면 다음 일을 하는 Claude Code 플러그인입니다.

1. 새 강의자료마다 아티팩트 두 개를 만듭니다.
   - 보충본: 슬라이드(장)마다 원문, 번역, 배경, 상세 설명, 예시와 풀이
   - 퀴즈: 잘 배웠는지 확인하는 문제와 해설. 답을 고르면 바로 채점합니다.
2. 그 과목의 지식 그래프를 갱신해 아티팩트로 발행합니다.
3. 보충본, 퀴즈, 그래프 링크와 바뀐 내용을 Gmail로 보냅니다.

그래프와 처리 기록은 과목 폴더마다 따로 저장됩니다. 과목끼리 섞이지 않습니다.

## 준비물

- Claude Code (Windows, WSL, Linux, macOS)
- Python 3.9 이상. 추가 패키지는 설치하지 않아도 됩니다. PDF를 읽는 pypdf는 플러그인 안에 들어 있습니다.
  - Windows는 https://www.python.org 에서 설치합니다. `python`, `py` 중 어느 명령이든 동작하면 됩니다.
- Gmail 앱 비밀번호. Google 계정에서 2단계 인증을 켠 뒤 "앱 비밀번호" 메뉴에서 만듭니다.

## 설치

셸에서 실행합니다.

```bash
claude plugin marketplace add kau-newbie/lecture-sync
claude plugin install lecture-sync@kau-newbie
```

## 비밀번호 등록

**WSL, Linux, macOS:** `~/.bashrc`(zsh는 `~/.zshrc`)에 한 줄을 추가하고 터미널을 다시 엽니다.

```bash
export GMAIL_APP_PASSWORD="앱 비밀번호 16자리"
```

**Windows:** PowerShell 또는 명령 프롬프트에서 실행하고, 터미널과 Claude Code를 다시 엽니다.

```powershell
setx GMAIL_APP_PASSWORD "앱 비밀번호 16자리"
```

비밀번호는 이 환경 변수로만 읽습니다. 파일에 저장하거나 화면에 출력하지 않습니다.

보내는 계정과 받는 주소가 다르면 `GMAIL_USER`에 보내는 계정을 추가로 등록합니다.

## 과목 폴더 설정

과목 폴더 맨 위에 `.lecture-sync.json` 파일을 만듭니다.

```json
{
  "course": "과목 이름",
  "notify_to": "받을 Gmail 주소",
  "extensions": [".pptx", ".ppt", ".pdf"]
}
```

| 항목 | 설명 |
|---|---|
| `course` | 과목 이름 |
| `notify_to` | 알림 메일을 받을 주소 |
| `extensions` | 강의자료로 볼 확장자. 생략하면 `.pptx`, `.ppt`, `.pdf` |

## 권장 폴더 구조

과목마다 폴더 하나를 두고, 그 안에 주차 폴더를 둡니다. 아래는 실제 과목 폴더를 바탕으로 한 예시입니다.

```
2026-2학기/                                   학기 폴더. 설정 파일을 두지 않습니다.
├── 모바일센서nw/                              과목 폴더
│   ├── .lecture-sync.json                     과목 설정 (직접 작성)
│   ├── .lecture-sync/                         플러그인이 만들고 관리하는 폴더
│   │   ├── manifest.json                      처리한 강의자료 기록
│   │   ├── graph.json                         이 과목의 지식 그래프 데이터와 아티팩트 링크
│   │   ├── graph.html                         graph.json으로 만든 그래프 페이지
│   │   └── notes/w3-rtsensor3/                강의자료마다 보충본과 퀴즈 데이터, 아티팩트 링크
│   ├── CLAUDE.md                              (선택) 과목 안내. 주차별 흐름 목록이 있으면 스킬이 새 주차를 추가합니다.
│   ├── 1주차/
│   │   └── RtLec1_2026.pptx
│   ├── 2주차/
│   │   ├── RTSensor1_2.pptx
│   │   └── Rtsensor2ext.pptx
│   ├── 3주차/
│   │   └── Rtsensor3_RM.pptx                  원본 강의자료
│   ├── 4주차/
│   │   └── Rtsensor4.pptx
│   └── 5주차/                                 아직 자료가 없는 주차는 빈 폴더로 둡니다.
└── 다른과목/                                  과목마다 그래프와 기록이 따로 생깁니다.
    ├── .lecture-sync.json
    ├── .lecture-sync/
    └── 1주차/
```

지켜야 할 점은 다음과 같습니다.

- **설정 파일은 과목 폴더에만 둡니다.** 학기 폴더에 두면 그 아래 모든 과목의 자료가 한 과목으로 처리되어 그래프가 섞입니다.
- **Claude Code는 과목 폴더나 그 아래 주차 폴더에서 엽니다.** 설정 파일은 현재 폴더에서 위쪽 방향으로만 찾습니다. 학기 폴더에서 열면 아무 동작도 하지 않습니다.
- **주차 폴더에는 원본 강의자료만 두면 됩니다.** 보충본과 퀴즈는 아티팩트로 만들고, 데이터는 `.lecture-sync/notes/`에 저장합니다.
- **강의자료가 아닌 파일에 주의합니다.** 과제 PDF처럼 강의자료가 아닌 파일도 `extensions`에 맞으면 새 자료로 처리됩니다. 과목 폴더에 이런 파일이 있으면 `extensions`를 `[".pptx"]`처럼 좁히거나, 과목 폴더 밖에 둡니다.
- **파일 이름은 바꾸지 않아도 됩니다.** `파일 (1) (2).pptx` 같은 다운로드 중복 표시가 있어도 됩니다. 내용이 같은 복사본은 자동으로 건너뜁니다.
- **`.lecture-sync/` 폴더는 지우지 않습니다.** 지우면 처리 기록과 그래프, 보충본, 퀴즈 링크가 사라져, 다음 실행 때 처음 설정한 과목으로 처리됩니다.
- **`~$`로 시작하는 파일은 무시됩니다.** Word나 PowerPoint가 파일을 열어 둘 때 만드는 임시 파일입니다.

## 사용 방법

1. 과목 폴더에서 Claude Code를 엽니다.
2. 처음 열면 기존 자료를 모두 정리할지, 처리한 것으로 기록만 할지 묻습니다.
3. 이후에는 새 파일이 있을 때 첫 메시지를 보내면 정리가 시작됩니다.
4. 직접 실행하려면 `/lecture-sync:sync`를 입력합니다.

## 알아 둘 점

- 새 파일은 Claude Code 세션을 시작할 때 확인합니다. 세션 도중에 넣은 파일은 다음 세션에 확인하거나 `/lecture-sync:sync`로 처리합니다.
- 내용이 같은 파일은 새 자료로 보지 않습니다. 예를 들어 `파일 (1).pptx` 같은 다운로드 복사본은 건너뜁니다.
- 구형 `.ppt`는 읽을 수 없습니다. PowerPoint에서 `.pptx`로 저장하면 새 자료로 처리됩니다.
- 슬라이드의 그림과 수식 개체는 글자로 추출되지 않습니다. 보충본과 그래프에 "확인하지 못한 부분"으로 표시합니다.
- 퀴즈의 풀이 기록은 보는 사람의 브라우저에만 저장됩니다. 다른 기기에서는 처음부터 풀게 됩니다.
- 보충본은 번역과 설명을 모두 담기 때문에 강의자료 하나를 처리하는 데 시간이 걸립니다. 슬라이드 50장 정도면 수십 분이 걸릴 수 있습니다.
- 아티팩트 기능이 없는 환경에서는 그래프, 보충본, 퀴즈를 `.lecture-sync/` 안의 HTML 파일로 저장합니다.
- `.lecture-sync.json`이 없는 폴더에서는 아무 동작도 하지 않습니다.

## 파일 구성

```
.claude-plugin/marketplace.json     마켓플레이스 목록
plugins/lecture-sync/
  .claude-plugin/plugin.json        플러그인 정보
  hooks/hooks.json                  세션 시작 시 변경 확인
  skills/sync/SKILL.md              정리 절차
  scripts/detect.py                 변경 감지와 처리 기록
  scripts/py.sh                     운영체제에 맞는 Python을 찾아 스크립트 실행
  scripts/extract_slides.py         슬라이드별 글자 추출
  scripts/_vendor/                  PDF 읽기용 pypdf와 라이선스 (수정하지 않음)
  scripts/build_graph.py            그래프 HTML 생성과 겹침 검사
  scripts/graph_template.html       그래프 페이지 틀
  scripts/build_notes.py            보충본과 퀴즈 HTML 생성과 검사
  scripts/notes_template.html       보충본 페이지 틀
  scripts/quiz_template.html        퀴즈 페이지 틀
  scripts/notify.py                 Gmail 발송
  config.example.json               과목 설정 예시
```

## 예시

먼저, 아래와 같은 강의자료 지식 그래프를 생성합니다.

![지식그래프예시](./example/img/example2.png)

- 마우스를 올려두면, 이웃 노드들만 밝게 표시됩니다.

![정리노트예시](./example/img/example1.png)
 
- 다음과 같이 매 강의자료마다 정리됩니다. 강의자료(pdf, pptx)의 페이지별로 아래와 같이 구성됩니다.
	- 번역
	- 배경설명
	- 상세설명
 	- (필요할경우) 예시와 풀이

써보니까 강의자료가 ppt 56장일 때, 하나의 html 파일 만드는ㄷ, 클로드 pro 기준 4-5% 정도 쓰는 것 같았습니다.

## 라이선스

MIT 라이선스입니다. 자세한 내용은 `LICENSE` 파일에 있습니다.
