#!/usr/bin/env python3
"""과목의 예제집(예시 위주 정리) HTML을 만든다.

사용: build_examples.py EXAMPLES_DIR --out OUT.html
      build_examples.py EXAMPLES_DIR --check

EXAMPLES_DIR는 <과목 폴더>/.lecture-sync/examples/ 이다. 과목마다 예제집은 하나이고,
새 강의자료가 들어오면 예제 파일을 더해 같은 URL로 다시 발행한다. 안에 다음 파일을 둔다.

meta.json
{
  "title": "예제집 제목(2~4단어)",
  "course": "과목 이름",
  "scope": "다룬 범위. 예: 1~5주차",
  "lead": "도입 문단",
  "sources": ["2주차/dsd_note.pdf 1~101장", ...],        # 근거 자료
  "notice": "코드는 시뮬레이션하지 않았습니다 (선택)",
  "intro": "본문 표기. 예제 전에 알아야 할 흐름, 문법 요약, 공통 규칙 (선택)",
  "intro_figures": [{"file": "fig/intro-1.svg", "caption": "..."}],   # 선택
  "terms": [["용어", "뜻"], ...],                          # 공통 용어 (선택)
  "parts": ["조합 회로", "순차 회로", ...],                # 예제 묶음 순서 (선택)
  "transcript": "강의 영상 스크립트 출처 (선택)",
  "unverified": ["확인하지 못한 부분", ...],
  "url": "", "graph_url": ""
}

ex-01.json, ex-02.json, ... (파일 이름 순서가 예제 순서다. 한 파일에 예제 하나)
{
  "id": "e1",                         # 페이지 안 링크 이름. 영문, 숫자, -만
  "part": "조합 회로",                 # meta.parts 중 하나
  "title": "2:1 MUX, 세 가지 기술 방식",
  "tags": ["structural", "dataflow"],
  "src": "근거: dsd_note 19~21장, 70장",
  "preview": "7주차 내용 미리보기",     # 아직 배우지 않은 주차 내용을 쓸 때 (선택)
  "background": "본문 표기",           # 필수
  "terms": [["용어", "뜻"], ...],       # 선택
  "figures": [{"file": "fig/e1-1.svg", "caption": "그림 설명"}],   # 구조 그림, 상태도 (선택)
  "flow": "본문 표기. 데이터나 계산이 흘러가는 순서 (선택)",
  "solution": "본문 표기. 계산·풀이 과정 (선택)",
  "code": [{"title": "(1) structural", "file": "code/mux2to1.v", "lang": "verilog"}],   # 선택
  "explain": "본문 표기. 코드나 풀이의 설명",   # 필수
  "lecture": "본문 표기. 강의 영상에서 설명한 내용 (선택)",
  "pitfalls": "본문 표기. 자주 하는 실수 (선택)"
}

그림(fig/*.svg)은 인라인 SVG로 들어간다. 조건:
- <svg ... viewBox="..." role="img" aria-label="그림이 보여 주는 내용">으로 시작한다.
- <script>, <style>, <foreignObject>를 쓰지 않는다. 색은 아래 클래스로 준다.
  blk(상자), blk2(강조 상자), ff(레지스터), st(상태), st2(강조 상태), w(선), wb(버스), hot(강조 선),
  dash(점선), dot/fillc(채운 점, 화살촉), 글자: s(작게), m(고정폭), h(강조), a(파란 강조)
- id는 페이지 전체에서 겹치면 안 된다. 화살촉 marker id는 그림마다 다르게 짓는다(예: m-e1-1).

코드(code/*)는 그대로 넣고 이스케이프한다. lang은 highlight.js 언어 이름이다(verilog, python, c 등).
본문 표기는 build_notes.py와 같다: 빈 줄로 문단, "- " 글머리표, "1. " 번호 목록, "|" 표, "$ " 수식 줄,
**굵게**, `코드`, x_{i}, 2^{n}.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from build_notes import esc, inline, rich

HERE = Path(__file__).resolve().parent
TEMPLATE = "examples_template.html"
HLJS = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0"
# highlight.min.js 기본 묶음에 들어 있어 따로 불러오지 않아도 되는 언어
HLJS_COMMON = {"bash", "c", "cpp", "csharp", "css", "diff", "go", "java", "javascript", "json", "kotlin",
               "markdown", "python", "rust", "shell", "sql", "typescript", "xml", "yaml", "plaintext"}
SVG_BAD = re.compile(r"<\s*(script|style|foreignObject)\b", re.I)
ID_RE = re.compile(r'\sid="([^"]+)"')


def load(d):
    d = Path(d)
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    exs = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(d.glob("ex-*.json"))]
    return meta, exs


def read(d, rel):
    p = (Path(d) / rel)
    return p.read_text(encoding="utf-8") if p.is_file() else None


def check_svg(label, text, seen, errs):
    head = text.lstrip()[:600]
    if not head.startswith("<svg"):
        errs.append(f"{label}: <svg로 시작하지 않습니다")
    if 'role="img"' not in head or "aria-label=" not in head:
        errs.append(f'{label}: role="img"와 aria-label이 필요합니다')
    if "viewBox=" not in head:
        errs.append(f"{label}: viewBox가 필요합니다")
    if SVG_BAD.search(text):
        errs.append(f"{label}: script, style, foreignObject는 쓸 수 없습니다")
    for i in ID_RE.findall(text):
        if i in seen:
            errs.append(f"{label}: id '{i}'가 {seen[i]}와 겹칩니다")
        else:
            seen[i] = label


def check(d, meta, exs):
    errs, seen_ids, svg_ids = [], {}, {}
    for k in ("title", "course"):
        if not meta.get(k):
            errs.append(f"meta.json: {k}가 비어 있습니다")
    if not exs:
        errs.append("예제 파일(ex-*.json)이 없습니다")
    parts = meta.get("parts") or []
    for f in meta.get("intro_figures", []):
        t = read(d, f.get("file", ""))
        if t is None:
            errs.append(f"meta.json: 그림 파일이 없습니다 {f.get('file')}")
        else:
            check_svg(f["file"], t, svg_ids, errs)
    for n, e in enumerate(exs, 1):
        lab = f"{n}번째 예제({e.get('id', '?')})"
        for k in ("id", "title", "background", "explain"):
            if not e.get(k):
                errs.append(f"{lab}: {k}가 비어 있습니다")
        eid = e.get("id", "")
        if eid and not re.fullmatch(r"[A-Za-z0-9-]+", eid):
            errs.append(f"{lab}: id는 영문, 숫자, -만 씁니다")
        if eid in seen_ids:
            errs.append(f"{lab}: id가 {seen_ids[eid]}번째 예제와 겹칩니다")
        seen_ids[eid] = n
        if parts and e.get("part") not in parts:
            errs.append(f"{lab}: part '{e.get('part')}'가 meta.parts에 없습니다")
        for f in e.get("figures", []):
            t = read(d, f.get("file", ""))
            if t is None:
                errs.append(f"{lab}: 그림 파일이 없습니다 {f.get('file')}")
            else:
                check_svg(f["file"], t, svg_ids, errs)
            if not f.get("caption"):
                errs.append(f"{lab}: 그림 {f.get('file')}에 caption이 없습니다")
        for c in e.get("code", []):
            if read(d, c.get("file", "")) is None:
                errs.append(f"{lab}: 코드 파일이 없습니다 {c.get('file')}")
            if not c.get("lang"):
                errs.append(f"{lab}: 코드 {c.get('file')}에 lang이 없습니다")
    return errs


def terms_html(terms):
    if not terms:
        return ""
    rows = "".join(f"<dt>{inline(t)}</dt><dd>{inline(v)}</dd>" for t, v in terms)
    return f'<dl class="terms">{rows}</dl>'


def figures_html(d, figs):
    out = []
    for f in figs:
        svg = read(d, f["file"]).strip()
        out.append(f'<figure>{svg}<figcaption>{inline(f["caption"])}</figcaption></figure>')
    if not out:
        return ""
    cls = "grid2" if len(out) == 2 else "figs"
    return f'<div class="{cls}">{"".join(out)}</div>'


def code_html(d, blocks, langs):
    out = []
    for c in blocks:
        langs.add(c["lang"])
        title = f'<h4>{inline(c["title"])}</h4>' if c.get("title") else ""
        name = Path(c["file"]).name
        out.append(f'{title}<div class="codebox"><div class="fname"><span>{esc(name)}</span>'
                   f'<button type="button" class="copy">복사</button></div>'
                   f'<pre><code class="language-{esc(c["lang"])}">{esc(read(d, c["file"]).rstrip())}</code></pre></div>')
    return "".join(out)


def sec(title, body, cls=""):
    return f'<h3>{title}</h3><div class="body {cls}">{body}</div>' if body else ""


def example_html(d, n, e, langs):
    tags = "".join(f"<li>{inline(t)}</li>" for t in e.get("tags", []))
    prev = f' <span class="preview">{inline(e["preview"])}</span>' if e.get("preview") else ""
    head = (f'<div class="ex-head"><span class="ex-no">예제 {n}{" · " + inline(e["part"]) if e.get("part") else ""}{prev}</span>'
            f'<h2>{inline(e["title"])}</h2>' + (f'<ul class="tags">{tags}</ul>' if tags else "")
            + (f'<p class="src">{inline(e["src"])}</p>' if e.get("src") else "") + "</div>")
    body = [
        sec("배경", rich(e.get("background"))),
        sec("용어", terms_html(e.get("terms"))),
        sec("그림", figures_html(d, e.get("figures", []))),
        sec("흐름", rich(e.get("flow")), "flow"),
        sec("풀이", rich(e.get("solution"))),
        sec("코드", code_html(d, e.get("code", []), langs)),
        sec("설명", rich(e.get("explain"))),
        sec("강의 설명 (영상 스크립트)", rich(e.get("lecture")), "lec"),
    ]
    if e.get("pitfalls"):
        body.append(f'<div class="note"><h4>자주 하는 실수</h4>{rich(e["pitfalls"])}</div>')
    return f'<section class="ex" id="{esc(e["id"])}">{head}{"".join(body)}</section>'


def build(d, meta, exs):
    langs = set()
    parts = meta.get("parts") or []
    order = parts + sorted({e.get("part", "") for e in exs} - set(parts))
    toc, arts = [], []
    n = 0
    numbered = []
    for p in order:
        group = [e for e in exs if e.get("part", "") == p]
        if not group:
            continue
        if p:
            toc.append(f'<li class="part">{inline(p)}</li>')
            arts.append(f'<div class="part-title">{inline(p)}</div>')
        for e in group:
            n += 1
            numbered.append(e)
            toc.append(f'<li><a href="#{esc(e["id"])}"><span>{n}</span>{inline(e["title"])}</a></li>')
            arts.append(example_html(d, n, e, langs))
    intro = ""
    if meta.get("intro") or meta.get("terms") or meta.get("intro_figures"):
        intro = ('<section class="ex" id="intro"><div class="ex-head"><span class="ex-no">시작하기 전에</span>'
                 '<h2>먼저 알아 둘 내용</h2></div>'
                 + rich(meta.get("intro")) + figures_html(d, meta.get("intro_figures", []))
                 + sec("공통 용어", terms_html(meta.get("terms"))) + "</section>")
        toc.insert(0, '<li><a href="#intro"><span>0</span>먼저 알아 둘 내용</a></li>')
    info = []
    if meta.get("sources"):
        info.append("근거 자료: " + ", ".join(inline(s) for s in meta["sources"]))
    if meta.get("transcript"):
        info.append("강의 영상 스크립트: " + inline(meta["transcript"]))
    if meta.get("notice"):
        info.append(inline(meta["notice"]))
    links = []
    if meta.get("graph_url"):
        links.append(f'<a href="{esc(meta["graph_url"])}" target="_blank" rel="noopener">지식 그래프</a>')
    unv = ""
    if meta.get("unverified"):
        unv = ('<section class="ex warnbox"><h2>확인하지 못한 부분</h2><ul>'
               + "".join(f"<li>{inline(x)}</li>" for x in meta["unverified"]) + "</ul></section>")
    scripts = [f'<script src="{HLJS}/highlight.min.js"></script>']
    scripts += [f'<script src="{HLJS}/languages/{esc(l)}.min.js"></script>' for l in sorted(langs - HLJS_COMMON)]
    return {
        "TITLE": esc(meta["title"]),
        "EYEBROW": esc(meta["course"]) + (" · " + esc(meta["scope"]) if meta.get("scope") else ""),
        "LEAD": inline(meta.get("lead", "")),
        "INFO": "".join(f"<span>{x}</span>" for x in info),
        "LINKS": " · ".join(links),
        "NEX": str(n),
        "TOC": "\n".join(toc),
        "INTRO": intro,
        "EXAMPLES": "\n".join(arts) + unv,
        "HLJS": "\n".join(scripts),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--out")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    meta, exs = load(a.dir)
    errs = check(a.dir, meta, exs)
    if a.check:
        print("\n".join(errs) if errs else f"문제 없음: 예제 {len(exs)}개")
        sys.exit(1 if errs else 0)
    if not a.out:
        ap.error("--out이 필요합니다")
    if errs:
        print("\n".join(errs), file=sys.stderr)
        sys.exit(1)
    vals = build(a.dir, meta, exs)
    page = (HERE / TEMPLATE).read_text(encoding="utf-8")
    for k, v in vals.items():
        page = page.replace("{{" + k + "}}", v)
    Path(a.out).write_text(page, encoding="utf-8")
    print(f"만듦: {a.out}")


if __name__ == "__main__":
    main()
