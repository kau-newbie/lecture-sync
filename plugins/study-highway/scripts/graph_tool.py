#!/usr/bin/env python3
"""graph.json을 통째로 읽거나 다시 쓰지 않고 보고 고친다. 토큰을 아끼려는 도구다.

사용:
  graph_tool.py summary GRAPH_JSON [--labels]   현재 그래프를 한눈에 본다. desc, refs, 연결 설명은 빼고 보여 준다.
  graph_tool.py show GRAPH_JSON ID [ID ...]     항목 몇 개와 그 항목에 닿는 연결을 전체 내용으로 본다.
  graph_tool.py patch GRAPH_JSON PATCH_JSON [--dry-run]   변경분만 적용한다.

summary 출력: 제목, viewBox, 그룹, 묶음(hulls), 항목(id | label | weeks | 그룹 | x,y,w | 표시), 연결(s>d 종류),
확인 필요 목록 개수, 최근 changelog 두 줄. --labels를 주면 연결 설명도 붙인다.
좌표는 새 항목을 빈 곳에 놓을 때 쓴다. 겹침은 build_graph.py --check가 검사한다.

patch 파일 형식 (모든 키는 선택):
{
  "nodes": [{"id": "새id", "label": "", "weeks": "", "group": 1, "x": 0, "y": 0, "w": 0, "desc": "", "ring": false},
            {"id": "기존id", "desc": "바꿀 내용만 쓴다", "refs_add": [{"label": "3주차 보충본 13~16장", "url": "URL#s13"}]}],
  "edges": [{"s": "id", "d": "id", "t": "u", "label": "", "sides": "rl", "pts": [[x, y]], "src": "근거"}],
  "remove_edges": [{"s": "id", "d": "id", "t": "u"}],
  "remove_nodes": ["id"],
  "set": {"lead": "", "caption": "", "title": "", "viewBox": [0, 0, 0, 0], "groups": [], "hulls": [], "artifact_url": ""},
  "checks_add": ["확인이 필요한 점"],
  "checks_set": ["목록 전체를 바꿀 때만"],
  "changelog_add": [{"date": "2026-09-27", "summary": "이번 수정 내용 한 줄"}]
}
- nodes: id가 이미 있으면 준 필드만 바꾼다(refs_add는 같은 url이 없을 때만 더한다). 없으면 새 항목이다.
  새 항목은 id, label, weeks, group, x, y, w가 필요하다.
- edges: s, d, t가 같은 연결이 이미 있으면 준 필드만 바꾸고, 없으면 더한다.
- remove_nodes는 그 항목에 닿는 연결도 함께 지운다.
적용 뒤 연결이 없는 항목을 가리키면 아무것도 쓰지 않고 멈춘다. 파일의 들여쓰기 서식(1, 2, 4칸)과 끝 줄바꿈은 그대로 둔다.
"""
import json
import sys
from pathlib import Path

NEW_NODE_KEYS = ("id", "label", "weeks", "group", "x", "y", "w")


def load(path):
    text = Path(path).read_text(encoding="utf-8")
    data = json.loads(text)
    # 원본과 같은 들여쓰기(1, 2, 4칸)를 찾아 그대로 되돌려 쓴다. 못 찾으면 1칸으로 쓰고 알린다.
    body = text.rstrip("\n")
    indent = next((i for i in (1, 2, 4) if json.dumps(data, ensure_ascii=False, indent=i) == body), None)
    return data, indent, text.endswith("\n")


def summary(data, labels=False):
    out = [f'title: {data.get("title", "")}  viewBox: {data.get("viewBox")}  artifact_url: {"있음" if data.get("artifact_url") else "없음"}']
    out.append("groups: " + ", ".join(f'{g["id"]}={g["label"]}{"*" if g.get("special") else ""}' for g in data.get("groups", [])))
    out.append("hulls (label: x,y,w,h):")
    for h in data.get("hulls", []):
        out.append(f'  {h.get("label", "")}: {h["x"]},{h["y"]},{h["w"]},{h["h"]}')
    out.append("nodes (id | label | weeks | group | x,y,w | ring/refs):")
    for n in data["nodes"]:
        mark = ("ring " if n.get("ring") else "") + (f'refs{len(n["refs"])}' if n.get("refs") else "")
        out.append(f'  {n["id"]} | {n.get("label", "")} | {n.get("weeks", "")} | {n.get("group")} | {n["x"]},{n["y"]},{n["w"]} | {mark}'.rstrip(" |"))
    out.append("edges (s>d type):")
    for e in data["edges"]:
        line = f'  {e["s"]}>{e["d"]} {e.get("t", "")}'
        if labels and e.get("label"):
            line += f' "{e["label"]}"'
        out.append(line)
    out.append(f'checks: {len(data.get("checks", []))}개')
    for c in data.get("changelog", [])[-2:]:
        out.append(f'changelog: {c.get("date", "")} {c.get("summary", "")[:80]}')
    return "\n".join(out)


def show(data, ids):
    have = {n["id"] for n in data["nodes"]}
    miss = [i for i in ids if i not in have]
    if miss:
        raise SystemExit(f"없는 항목: {miss}")
    sel = {"nodes": [n for n in data["nodes"] if n["id"] in ids],
           "edges": [e for e in data["edges"] if e["s"] in ids or e["d"] in ids]}
    return json.dumps(sel, ensure_ascii=False, indent=2)


def apply(data, patch):
    nodes = {n["id"]: n for n in data["nodes"]}
    added = changed = 0
    for n in patch.get("nodes", []):
        refs_add = n.pop("refs_add", None) if isinstance(n, dict) else None
        if n["id"] in nodes:
            nodes[n["id"]].update({k: v for k, v in n.items() if k != "id"})
            changed += 1
        else:
            lack = [k for k in NEW_NODE_KEYS if k not in n]
            if lack:
                raise SystemExit(f'새 항목 {n["id"]}에 필요한 필드가 없습니다: {lack}')
            data["nodes"].append(n)
            nodes[n["id"]] = n
            added += 1
        if refs_add:
            refs = nodes[n["id"]].setdefault("refs", [])
            for r in refs_add:
                if all(x.get("url") != r.get("url") for x in refs):
                    refs.append(r)
    key = lambda e: (e["s"], e["d"], e.get("t"))
    edges = {key(e): e for e in data["edges"]}
    e_added = e_changed = 0
    for e in patch.get("edges", []):
        if key(e) in edges:
            edges[key(e)].update(e)
            e_changed += 1
        else:
            data["edges"].append(e)
            edges[key(e)] = e
            e_added += 1
    for r in patch.get("remove_edges", []):
        data["edges"] = [e for e in data["edges"] if key(e) != (r["s"], r["d"], r.get("t"))]
    gone = set(patch.get("remove_nodes", []))
    if gone:
        data["nodes"] = [n for n in data["nodes"] if n["id"] not in gone]
        data["edges"] = [e for e in data["edges"] if e["s"] not in gone and e["d"] not in gone]
    data.update(patch.get("set", {}))
    if "checks_set" in patch:
        data["checks"] = patch["checks_set"]
    if patch.get("checks_add"):
        data.setdefault("checks", []).extend(patch["checks_add"])
    if patch.get("changelog_add"):
        data.setdefault("changelog", []).extend(patch["changelog_add"])
    ids = {n["id"] for n in data["nodes"]}
    for e in data["edges"]:
        for k in ("s", "d"):
            if e[k] not in ids:
                raise SystemExit(f"연결이 없는 항목을 가리킵니다: {e[k]} (적용하지 않았습니다)")
    return f"항목 추가 {added}, 수정 {changed}, 삭제 {len(gone)}; 연결 추가 {e_added}, 수정 {e_changed}"


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] not in ("summary", "show", "patch"):
        print(__doc__)
        sys.exit(1)
    data, indent, newline = load(a[1])
    if a[0] == "summary":
        print(summary(data, "--labels" in a))
    elif a[0] == "show":
        if len(a) < 3:
            raise SystemExit("show에는 항목 id가 필요합니다.")
        print(show(data, a[2:]))
    else:
        if len(a) < 3:
            raise SystemExit("patch에는 패치 파일이 필요합니다.")
        patch = json.loads(Path(a[2]).read_text(encoding="utf-8"))
        msg = apply(data, patch)
        if "--dry-run" in a:
            print("(적용하지 않음) " + msg)
            return
        Path(a[1]).write_text(json.dumps(data, ensure_ascii=False, indent=indent or 1) + ("\n" if newline else ""), encoding="utf-8")
        print(msg + ("" if indent else "  [주의: 원래 서식을 찾지 못해 들여쓰기 1칸으로 썼습니다]"))


if __name__ == "__main__":
    main()
