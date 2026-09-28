#!/usr/bin/env bash
# 실제로 동작하는 Python 3을 찾아 인자를 그대로 넘겨 실행한다.
# Windows의 python.org 설치본에는 python3가 없고, python3를 부르면 Microsoft Store
# 안내용 실행 파일이 실행되어 실패한다. 그래서 이름만 보지 않고 직접 실행해 확인한다.
# 사용: bash py.sh 스크립트.py [인자...]
for c in python3 python "py -3"; do
  if $c -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >/dev/null 2>&1; then
    export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
    exec $c "$@"
  fi
done
echo "lecture-sync: Python 3.9 이상을 찾지 못했습니다. https://www.python.org 에서 설치하세요." >&2
exit 127
