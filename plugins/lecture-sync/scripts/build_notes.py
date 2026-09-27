#!/usr/bin/env python3
"""강의자료 하나의 보충본과 퀴즈 HTML을 만든다.

사용: build_notes.py NOTES_DIR --kind notes|quiz --out OUT.html
      build_notes.py NOTES_DIR --check

NOTES_DIR는 <과목 폴더>/.lecture-sync/notes/<id>/ 이다. 안에 다음 파일을 둔다.

meta.json
{
  "source": "3주차/원본.pptx",
  "week": "3주차",
  "topic": "주제",
  "title": "보충본 제목(2~4단어)",
  "quiz_title": "퀴즈 제목(2~4단어)",
  "lead": "이 강의가 다루는 내용 요약 문단",
  "prereq": ["먼저 알아야 할 내용", ...],
  "formulas": [{"name": "이름", "expr": "식", "note": "뜻"}, ...],
  "unverified": ["21장: 수식이 개체라 텍스트로 추출되지 않음", ...],
  "notes_url": "", "quiz_url": "", "graph_url": ""
}

slides-*.json (여러 파일로 나눠 써도 된다. 장 번호 순서로 합친다)
[{"n": 1, "title": "제목", "original": "슬라이드 원문",
  "translation": "번역", "background": "배경 설명", "detail": "상세 설명",
  "example": "예시·문제 풀이(선택)", "unverified": "확인하지 못한 부분(선택)",
  "brief": false}, ...]
brief가 true인 장(표지, 목차 등)은 background, detail을 비워도 된다.

quiz.json
{"questions": [
  {"type": "mc", "q": "질문", "choices": ["보기", ...], "answer": 0, "explain": "해설", "slides": [5, 6]},
  {"type": "tf", "q": "질문", "answer": true, "explain": "해설", "slides": [7]},
  {"type": "short", "q": "질문", "answer": "모범 답안", "explain": "해설", "slides": [8]},
  {"type": "calc", "q": "질문", "answer": "답", "explain": "풀이", "slides": [9]}
]}
mc의 answer는 0부터 센 보기 번호다.

본문 텍스트 표기(original 제외):
- 빈 줄로 문단을 나눈다.
- "- "로 시작하는 줄은 글머리표, "1. "처럼 시작하는 줄은 번호 목록이다.
- "|"로 시작하는 줄이 이어지면 표가 된다. 첫 줄이 머리글이다.
- "$ "로 시작하는 줄은 수식 한 줄로 보여 준다.
- **굵게**, `코드`, x_{i}(아래 첨자), 2^{1/n}(위 첨자)를 쓸 수 있다.
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KINDS = {"notes": "notes_template.html", "quiz": "quiz_template.html"}
QTYPES = {"mc": "객관식", "tf": "O/X", "short": "서술", "calc": "계산"}


def esc(s):
    return html.escape(str(s), quote=True)


def inline(s):
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"_\{([^{}]+)\}", r"<sub>\1</sub>", s)
    s = re.sub(r"\^\{([^{}]+)\}", r"<sup>\1</sup>", s)
    return s


def table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    cells = [r for r in cells if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
    head, body = cells[0], cells[1:]
    out = ['<div class="tw"><table><thead><tr>']
    out += [f"<th>{inline(c)}</th>" for c in head]
    out.append("</tr></thead><tbody>")
    for r in body:
        out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def rich(text):
    """본문 텍스트 표기를 HTML로 바꾼다."""
    if not text:
        return ""
    out = []
    for block in re.split(r"\n\s*\n", str(text).strip()):
        lines = [l for l in block.split("\n") if l.strip()]
        i = 0
        para = []

        def flush():
            if para:
                out.append("<p>" + "<br>".join(inline(p) for p in para) + "</p>")
                para.clear()

        while i < len(lines):
            l = lines[i].strip()
            if l.startswith("|"):
                flush()
                j = i
                while j < len(lines) and lines[j].strip().startswith("|"):
                    j += 1
                out.append(table(lines[i:j]))
                i = j
            elif l.startswith("- ") or re.match(r"\d+\. ", l):
                flush()
                ordered = not l.startswith("- ")
                pat = r"\d+\. " if ordered else r"- "
                items = []
                while i < len(lines) and re.match(pat, lines[i].strip()):
                    items.append(re.sub("^" + pat, "", lines[i].strip()))
                    i += 1
                tag = "ol" if ordered else "ul"
                out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
            elif l.startswith("$ "):
                flush()
                out.append(f'<div class="math">{inline(l[2:])}</div>')
                i += 1
            else:
                para.append(l)
                i += 1
        flush()
    return "\n".join(out)


def load(d):
    d = Path(d)
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    slides = []
    for f in sorted(d.glob("slides-*.json")):
        slides += json.loads(f.read_text(encoding="utf-8"))
    slides.sort(key=lambda s: s["n"])
    qf = d / "quiz.json"
    quiz = json.loads(qf.read_text(encoding="utf-8")) if qf.exists() else {"questions": []}
    return meta, slides, quiz


def check(meta, slides, quiz):
    errs = []
    for k in ("source", "week", "topic", "title"):
        if not meta.get(k):
            errs.append(f"meta.json: {k}가 비어 있습니다")
    nums = [s["n"] for s in slides]
    dup = sorted({n for n in nums if nums.count(n) > 1})
    if dup:
        errs.append(f"장 번호가 중복됩니다: {dup}")
    if nums:
        miss = sorted(set(range(1, max(nums) + 1)) - set(nums))
        if miss:
            errs.append(f"빠진 장: {miss}")
    for s in slides:
        need = ("title", "original", "translation") if s.get("brief") else ("title", "original", "translation", "background", "detail")
        for k in need:
            if not s.get(k):
                errs.append(f"{s['n']}장: {k}가 비어 있습니다")
    for i, q in enumerate(quiz.get("questions", []), 1):
        t = q.get("type")
        if t not in QTYPES:
            errs.append(f"퀴즈 {i}번: type이 {t}입니다")
            continue
        for k in ("q", "explain"):
            if not q.get(k):
                errs.append(f"퀴즈 {i}번: {k}가 비어 있습니다")
        if t == "mc":
            ch = q.get("choices") or []
            if len(ch) < 2 or not isinstance(q.get("answer"), int) or not 0 <= q["answer"] < len(ch):
                errs.append(f"퀴즈 {i}번: 보기 또는 answer가 잘못되었습니다")
        elif t == "tf":
            if not isinstance(q.get("answer"), bool):
                errs.append(f"퀴즈 {i}번: answer는 true 또는 false여야 합니다")
        elif not q.get("answer"):
            errs.append(f"퀴즈 {i}번: answer가 비어 있습니다")
        bad = [n for n in q.get("slides", []) if n not in nums]
        if bad:
            errs.append(f"퀴즈 {i}번: 없는 장을 가리킵니다 {bad}")
    return errs


def links(meta, kind):
    out = []
    if kind == "quiz" and meta.get("notes_url"):
        out.append(f'<a href="{esc(meta["notes_url"])}" target="_blank" rel="noopener">보충본</a>')
    if kind == "notes" and meta.get("quiz_url"):
        out.append(f'<a href="{esc(meta["quiz_url"])}" target="_blank" rel="noopener">퀴즈</a>')
    if meta.get("graph_url"):
        out.append(f'<a href="{esc(meta["graph_url"])}" target="_blank" rel="noopener">지식 그래프</a>')
    return " · ".join(out)


def li(items):
    return "\n".join(f"<li>{inline(x)}</li>" for x in items)


def section(label, body, cls):
    return f'<div class="part {cls}"><h4>{label}</h4>{body}</div>' if body else ""


def notes_page(meta, slides):
    toc = "\n".join(f'<li><a href="#s{s["n"]}"><span class="no">{s["n"]}</span>{inline(s["title"])}</a></li>' for s in slides)
    arts = []
    for s in slides:
        orig = f'<div class="part orig"><h4>원문</h4><pre>{esc(s["original"])}</pre></div>'
        tr = section("번역", rich(s.get("translation")), "tr")
        parts = [f'<div class="pair">{orig}{tr}</div>']
        parts.append(section("배경", rich(s.get("background")), "bg"))
        parts.append(section("상세 설명", rich(s.get("detail")), "dt"))
        parts.append(section("예시와 풀이", rich(s.get("example")), "ex"))
        if s.get("unverified"):
            parts.append(f'<p class="warn">확인하지 못한 부분: {inline(s["unverified"])}</p>')
        cls = "slide brief" if s.get("brief") else "slide"
        arts.append(f'<article class="{cls}" id="s{s["n"]}"><h3><span class="no">{s["n"]}장</span>{inline(s["title"])}</h3>{"".join(parts)}</article>')
    formulas = ""
    if meta.get("formulas"):
        rows = "".join(f'<tr><th scope="row">{inline(f["name"])}</th><td class="m">{inline(f["expr"])}</td><td>{inline(f.get("note", ""))}</td></tr>' for f in meta["formulas"])
        formulas = f'<section class="box"><h2>핵심 공식</h2><div class="tw"><table><thead><tr><th>이름</th><th>식</th><th>뜻</th></tr></thead><tbody>{rows}</tbody></table></div></section>'
    prereq = f'<section class="box"><h2>먼저 알아야 할 내용</h2><ul>{li(meta["prereq"])}</ul></section>' if meta.get("prereq") else ""
    unv = f'<section class="box warnbox"><h2>확인하지 못한 부분</h2><ul>{li(meta["unverified"])}</ul></section>' if meta.get("unverified") else ""
    return {
        "TITLE": esc(meta["title"]),
        "SOURCE": esc(meta["source"]),
        "WEEK": esc(meta["week"]),
        "TOPIC": esc(meta["topic"]),
        "LEAD": inline(meta.get("lead", "")),
        "LINKS": links(meta, "notes"),
        "NSLIDES": str(len(slides)),
        "PREREQ": prereq,
        "FORMULAS": formulas,
        "UNVERIFIED": unv,
        "TOC": toc,
        "SLIDES": "\n".join(arts),
    }


def quiz_page(meta, slides, quiz):
    base = meta.get("notes_url", "")
    qs = []
    for i, q in enumerate(quiz["questions"], 1):
        t = q["type"]
        refs = ""
        if q.get("slides"):
            if base:
                refs = ", ".join(f'<a href="{esc(base)}#s{n}" target="_blank" rel="noopener">{n}장</a>' for n in q["slides"])
            else:
                refs = ", ".join(f"{n}장" for n in q["slides"])
            refs = f'<p class="ref">보충본 {refs}</p>'
        if t == "mc":
            body = '<div class="choices">' + "".join(
                f'<button type="button" class="ch" data-i="{k}"><span class="k">{k + 1}</span><span>{inline(c)}</span></button>'
                for k, c in enumerate(q["choices"])) + "</div>"
            ans = str(q["answer"])
            shown = f'정답: {q["answer"] + 1}번'
        elif t == "tf":
            body = '<div class="choices tf"><button type="button" class="ch" data-i="1"><span class="k">O</span><span>맞다</span></button><button type="button" class="ch" data-i="0"><span class="k">X</span><span>틀리다</span></button></div>'
            ans = "1" if q["answer"] else "0"
            shown = "정답: " + ("O" if q["answer"] else "X")
        else:
            body = ('<textarea rows="3" aria-label="내 답"></textarea>'
                    '<div class="row"><button type="button" class="reveal">정답 보기</button></div>')
            ans = ""
            shown = "정답: " + inline(q["answer"])
        sol = (f'<div class="sol" hidden><p class="ans">{shown}</p>{rich(q["explain"])}{refs}'
               + ('<div class="row self"><span>내 답이 맞았나요?</span><button type="button" data-self="1">맞음</button><button type="button" data-self="0">틀림</button></div>' if t in ("short", "calc") else "")
               + "</div>")
        qs.append(f'<li class="q" data-type="{t}" data-ans="{ans}" id="q{i}"><div class="qh"><span class="tag">{QTYPES[t]}</span></div>'
                  f'<div class="qt">{rich(q["q"])}</div>{body}{sol}</li>')
    return {
        "TITLE": esc(meta.get("quiz_title") or meta["title"] + " 퀴즈"),
        "SOURCE": esc(meta["source"]),
        "WEEK": esc(meta["week"]),
        "TOPIC": esc(meta["topic"]),
        "LINKS": links(meta, "quiz"),
        "NQ": str(len(qs)),
        "QUESTIONS": "\n".join(qs),
        "KEY": esc(meta["source"]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--kind", choices=KINDS)
    ap.add_argument("--out")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    meta, slides, quiz = load(a.dir)
    errs = check(meta, slides, quiz)
    if a.check:
        print("\n".join(errs) if errs else f"문제 없음: {len(slides)}장, 퀴즈 {len(quiz.get('questions', []))}문제")
        sys.exit(1 if errs else 0)
    if not a.kind or not a.out:
        ap.error("--kind와 --out이 필요합니다")
    if errs:
        print("\n".join(errs), file=sys.stderr)
        sys.exit(1)
    vals = notes_page(meta, slides) if a.kind == "notes" else quiz_page(meta, slides, quiz)
    page = (HERE / KINDS[a.kind]).read_text(encoding="utf-8")
    for k, v in vals.items():
        page = page.replace("{{" + k + "}}", v)
    Path(a.out).write_text(page, encoding="utf-8")
    print(f"만듦: {a.out}")


if __name__ == "__main__":
    main()
