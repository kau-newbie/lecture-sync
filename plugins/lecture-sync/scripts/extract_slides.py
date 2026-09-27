#!/usr/bin/env python3
"""강의 슬라이드 파일에서 슬라이드(장)별 텍스트를 뽑는다. 외부 패키지가 필요 없다.

사용: extract_slides.py 파일 [--json]
- .pptx: 슬라이드 번호 순서대로 문단 텍스트를 출력한다. 텍스트로 추출되지 않는 개체
  (그림, 수식, OLE 개체, 차트)의 개수도 슬라이드마다 표시한다.
- .pdf: pdftotext가 있으면 쪽 단위로 출력한다.
- .ppt(구형): 읽을 수 없다. 종료 코드 2로 끝난다. .pptx로 저장해야 한다.
"""
import html
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


def pptx_slides(path):
    slides = []
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
        names.sort(key=lambda n: int(re.search(r"(\d+)", n.split("/")[-1]).group(1)))
        for n in names:
            xml = z.read(n).decode("utf-8", "replace")
            paras = []
            for p in re.findall(r"<a:p[ >].*?</a:p>", xml, re.S):
                t = "".join(html.unescape(x) for x in re.findall(r"<a:t>([^<]*)</a:t>", p))
                t = t.strip()
                if t:
                    paras.append(t)
            objs = {
                "그림": len(re.findall(r"<p:pic[ >]", xml)),
                "수식": len(re.findall(r"<m:oMath[ >]", xml)),
                "OLE 개체": len(re.findall(r"<p:oleObj[ >]", xml)),
                "차트": len(re.findall(r"drawingml/2006/chart", xml)),
            }
            slides.append({"slide": int(re.search(r"(\d+)", n.split("/")[-1]).group(1)),
                           "text": paras, "objects": {k: v for k, v in objs.items() if v}})
    return slides


def pdf_pages(path):
    exe = shutil.which("pdftotext")
    if not exe:
        raise RuntimeError("pdftotext가 없어 PDF를 읽을 수 없습니다.")
    out = subprocess.run([exe, "-layout", str(path), "-"], capture_output=True, text=True, check=True).stdout
    pages = []
    for i, chunk in enumerate(out.split("\f"), 1):
        lines = [l.strip() for l in chunk.splitlines() if l.strip()]
        if lines:
            pages.append({"slide": i, "text": lines, "objects": {}})
    return pages


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = Path(sys.argv[1])
    suffix = path.suffix.lower()
    if suffix == ".ppt":
        print("구형 .ppt는 읽을 수 없습니다. PowerPoint에서 .pptx로 저장한 뒤 다시 실행하세요.", file=sys.stderr)
        sys.exit(2)
    try:
        if suffix == ".pptx":
            slides = pptx_slides(path)
        elif suffix == ".pdf":
            slides = pdf_pages(path)
        else:
            print(f"지원하지 않는 형식입니다: {suffix}", file=sys.stderr)
            sys.exit(2)
    except (zipfile.BadZipFile, RuntimeError, subprocess.CalledProcessError, OSError) as e:
        print(f"읽기 실패: {e}", file=sys.stderr)
        sys.exit(2)
    if "--json" in sys.argv:
        print(json.dumps(slides, ensure_ascii=False, indent=2))
        return
    for s in slides:
        print(f"## {s['slide']}장")
        for t in s["text"]:
            print(f"- {t}")
        if s["objects"]:
            print("  (텍스트로 추출되지 않음: " + ", ".join(f"{k} {v}개" for k, v in s["objects"].items()) + ")")
        print()


if __name__ == "__main__":
    main()
