#!/usr/bin/env python3
"""강의 슬라이드 파일에서 슬라이드(장)별 텍스트를 뽑는다. 외부 패키지를 설치할 필요가 없다.

사용: extract_slides.py 파일 [--json]
- .pptx: 슬라이드 번호 순서대로 문단 텍스트를 출력한다. 텍스트로 추출되지 않는 개체
  (그림, 수식, OLE 개체, 차트)의 개수도 슬라이드마다 표시한다.
- .pdf: 쪽 단위로 출력한다. 쪽마다 그림 개수도 표시한다. 절반이 넘는 쪽에 반복되는
  그림(로고, 배경)은 세지 않는다. 함께 넣어 둔 pypdf(_vendor/)로 읽으므로 운영체제와
  관계없이 같은 결과가 나온다. PDF의 수식은 글자나 그림으로 들어 있어 따로 세지 못한다.
- .ppt(구형): 읽을 수 없다. 종료 코드 2로 끝난다. .pptx로 저장해야 한다.
"""
import html
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "_vendor"))


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


def image_ids(resources, out=None, depth=0):
    """쪽의 리소스에 있는 그림의 객체 번호를 모은다. 폼 XObject 안의 그림도 모은다."""
    out = set() if out is None else out
    try:
        xobjs = resources.get_object().get("/XObject") if resources else None
        xobjs = xobjs.get_object() if xobjs else {}
        for k in xobjs:
            ref = xobjs.raw_get(k)
            key = getattr(ref, "idnum", None) or ("inline", id(ref))
            if key in out:
                continue
            o = ref.get_object()
            sub = o.get("/Subtype")
            if sub == "/Image":
                out.add(key)
            elif sub == "/Form" and depth < 5:
                image_ids(o.get("/Resources"), out, depth + 1)
    except Exception:  # 손상된 리소스는 개수에서 빼고 텍스트 추출은 계속한다.
        pass
    return out


def pdf_pages(path):
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError, DependencyError
    except ImportError as e:
        raise RuntimeError(f"함께 넣어 둔 pypdf를 불러오지 못했습니다: {e}")
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            reader.decrypt("")
        pages, ids = [], []
        for i, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            pages.append({"slide": i, "text": lines, "objects": {}})
            ids.append(image_ids(page.get("/Resources")))
        # 절반이 넘는 쪽에 반복되는 그림은 로고, 배경 같은 틀 그림으로 보고 세지 않는다.
        freq = Counter(k for s in ids for k in s)
        common = {k for k, c in freq.items() if len(pages) >= 4 and c > len(pages) / 2}
        for p, s in zip(pages, ids):
            n = len(s - common)
            if n:
                p["objects"]["그림"] = n
    except DependencyError:
        raise RuntimeError("암호화된 PDF라 읽을 수 없습니다. PDF 뷰어에서 '다른 이름으로 인쇄 > PDF로 저장'한 파일을 쓰세요.")
    except PdfReadError as e:
        raise RuntimeError(f"PDF를 읽지 못했습니다: {e}")
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
    except (zipfile.BadZipFile, RuntimeError, OSError) as e:
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
