# lecture-sync

강의자료 폴더에 새 파일이 들어오면 다음 일을 하는 Claude Code 플러그인입니다.

1. 새 강의자료를 슬라이드(장)별 정리 문서(`.docx`)로 만듭니다.
2. 그 과목의 지식 그래프를 갱신해 아티팩트로 발행합니다.
3. 그래프 링크와 바뀐 내용을 Gmail로 보냅니다.

그래프와 처리 기록은 과목 폴더마다 따로 저장됩니다. 과목끼리 섞이지 않습니다.

## 준비물

- Claude Code
- Python 3 (추가 패키지 필요 없음)
- Gmail 앱 비밀번호. Google 계정에서 2단계 인증을 켠 뒤 "앱 비밀번호" 메뉴에서 만듭니다.

## 설치

셸에서 실행합니다.

```bash
claude plugin marketplace add kau-newbie/lecture-sync
claude plugin install lecture-sync@lecture-sync
```

## 비밀번호 등록

`~/.bashrc`(zsh는 `~/.zshrc`)에 한 줄을 추가하고 터미널을 다시 엽니다.

```bash
export GMAIL_APP_PASSWORD="앱 비밀번호 16자리"
```

비밀번호는 이 환경 변수로만 읽습니다. 파일에 저장하거나 화면에 출력하지 않습니다.

보내는 계정과 받는 주소가 다르면 `GMAIL_USER`에 보내는 계정을 추가로 등록합니다.

## 과목 폴더 설정

과목 폴더 맨 위에 `.lecture-sync.json` 파일을 만듭니다.

```json
{
  "course": "과목 이름",
  "notify_to": "받을 Gmail 주소",
  "extensions": [".pptx", ".ppt", ".pdf"],
  "summary_reference": "3주차/기존_정리문서.docx"
}
```

| 항목 | 설명 |
|---|---|
| `course` | 과목 이름 |
| `notify_to` | 알림 메일을 받을 주소 |
| `extensions` | 강의자료로 볼 확장자. 생략하면 `.pptx`, `.ppt`, `.pdf` |
| `summary_reference` | 정리 문서의 형식 기준으로 삼을 기존 문서. 없으면 생략 |

## 사용 방법

1. 과목 폴더에서 Claude Code를 엽니다.
2. 처음 열면 기존 자료를 모두 정리할지, 처리한 것으로 기록만 할지 묻습니다.
3. 이후에는 새 파일이 있을 때 첫 메시지를 보내면 정리가 시작됩니다.
4. 직접 실행하려면 `/lecture-sync:sync`를 입력합니다.

## 알아 둘 점

- 새 파일은 Claude Code 세션을 시작할 때 확인합니다. 세션 도중에 넣은 파일은 다음 세션에 확인하거나 `/lecture-sync:sync`로 처리합니다.
- 내용이 같은 파일은 새 자료로 보지 않습니다. 예를 들어 `파일 (1).pptx` 같은 다운로드 복사본은 건너뜁니다.
- 구형 `.ppt`는 읽을 수 없습니다. PowerPoint에서 `.pptx`로 저장하면 새 자료로 처리됩니다.
- 슬라이드의 그림과 수식 개체는 글자로 추출되지 않습니다. 정리 문서와 그래프에 "확인하지 못한 부분"으로 표시합니다.
- 아티팩트 기능이 없는 환경에서는 그래프를 과목 폴더의 `.lecture-sync/graph.html` 파일로 저장합니다.
- `.lecture-sync.json`이 없는 폴더에서는 아무 동작도 하지 않습니다.

## 파일 구성

```
.claude-plugin/marketplace.json     마켓플레이스 목록
plugins/lecture-sync/
  .claude-plugin/plugin.json        플러그인 정보
  hooks/hooks.json                  세션 시작 시 변경 확인
  skills/sync/SKILL.md              정리 절차
  scripts/detect.py                 변경 감지와 처리 기록
  scripts/extract_slides.py         슬라이드별 글자 추출
  scripts/build_graph.py            그래프 HTML 생성과 겹침 검사
  scripts/graph_template.html       그래프 페이지 틀
  scripts/notify.py                 Gmail 발송
  config.example.json               과목 설정 예시
```
