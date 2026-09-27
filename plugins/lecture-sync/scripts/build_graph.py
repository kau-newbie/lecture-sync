#!/usr/bin/env python3
"""과목 폴더의 graph.json을 읽어 지식 그래프 HTML을 만든다.

사용: build_graph.py GRAPH_JSON --out OUT.html [--check]

graph.json은 과목마다 따로 있다. 이 스크립트와 틀(graph_template.html)에는 특정 과목의 내용이 없다.

graph.json 형식:
{
  "title": "그래프 제목(2~4단어)",
  "lead": "도입 문단",
  "caption": "그림 설명 문단",
  "viewBox": [x, y, 너비, 높이],
  "groups": [{"id": 1, "label": "1주차", "special": true}, ...],   # id 1~6. special은 id 1에만 쓴다.
  "hulls":  [{"x":, "y":, "w":, "h":, "label": "", "special": false}, ...],
  "nodes":  [{"id":, "label":, "weeks":, "group": 1~6, "x":, "y":, "w":, "desc":, "ring": false}, ...],
  "edges":  [{"s":, "d":, "t": "h|u|c", "label": "", "sides": "rl", "pts": [[x,y],...], "src": "근거"}, ...],
  "checks": ["확인이 필요한 점(HTML 가능)", ...],
  "changelog": [{"date": "2026-09-27", "summary": "..."}, ...],
  "artifact_url": ""
}
t: h 분류 하위(선), u 전제·적용(화살표), c 비교·대조(점선).
node의 x, y는 중심 좌표이고 높이는 44로 고정이다. pts를 주면 그 꺾은선을 따라 그리고, 없으면 곡선으로 잇는다.
--check: 선이 다른 노드를 지나가는 곳만 검사하고 HTML은 만들지 않는다.
"""
import argparse
import html
import json
import math
import sys
from pathlib import Path

H = 44
DIR = {"l": (-1, 0), "r": (1, 0), "t": (0, -1), "b": (0, 1)}
OPP = {"l": "r", "r": "l", "t": "b", "b": "t"}


def esc(s):
    return html.escape(str(s), quote=True)


class Graph:
    def __init__(self, data):
        self.d = data
        self.N = {n["id"]: n for n in data["nodes"]}
        self.E = data["edges"]
        ids = set(self.N)
        for e in self.E:
            for k in ("s", "d"):
                if e[k] not in ids:
                    raise SystemExit(f"연결이 없는 항목을 가리킵니다: {e[k]}")
        self.special = next((g["id"] for g in data["groups"] if g.get("special")), None)

    @staticmethod
    def rect(n):
        return (n["x"] - n["w"] / 2, n["y"] - H / 2, n["w"], H)

    @staticmethod
    def anchor(n, side):
        x, y, w = n["x"], n["y"], n["w"]
        return {"l": (x - w / 2, y), "r": (x + w / 2, y), "t": (x, y - H / 2), "b": (x, y + H / 2)}[side]

    @staticmethod
    def auto_sides(a, b):
        dx, dy = b["x"] - a["x"], b["y"] - a["y"]
        if abs(dy) > abs(dx):
            s = "b" if dy > 0 else "t"
        else:
            s = "r" if dx > 0 else "l"
        return s, OPP[s]

    def build(self, e):
        a, b = self.N[e["s"]], self.N[e["d"]]
        if e.get("pts"):
            pts = [tuple(p) for p in e["pts"]]
            r = 10
            d = f"M{pts[0][0]} {pts[0][1]}"

            def toward(p, q, dist):
                L = math.hypot(q[0] - p[0], q[1] - p[1]) or 1
                dist = min(dist, L / 2)
                return (p[0] + (q[0] - p[0]) * dist / L, p[1] + (q[1] - p[1]) * dist / L)

            for i in range(1, len(pts) - 1):
                s = toward(pts[i], pts[i - 1], r)
                t = toward(pts[i], pts[i + 1], r)
                d += f" L{s[0]:.1f} {s[1]:.1f} Q{pts[i][0]} {pts[i][1]} {t[0]:.1f} {t[1]:.1f}"
            d += f" L{pts[-1][0]} {pts[-1][1]}"
            best = max(range(len(pts) - 1), key=lambda i: math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]))
            lp = ((pts[best][0] + pts[best + 1][0]) / 2, (pts[best][1] + pts[best + 1][1]) / 2)
            if e.get("lp"):
                lp = tuple(e["lp"])
            smp = []
            for i in range(len(pts) - 1):
                for k in range(41):
                    t = k / 40
                    smp.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t))
            return d, lp, smp
        sides = e.get("sides")
        ss, ds = (sides[0], sides[1]) if sides else self.auto_sides(a, b)
        p0, p3 = self.anchor(a, ss), self.anchor(b, ds)
        dist = math.hypot(p3[0] - p0[0], p3[1] - p0[1])
        k = max(30, min(120, dist * 0.4))
        p1 = (p0[0] + DIR[ss][0] * k, p0[1] + DIR[ss][1] * k)
        p2 = (p3[0] + DIR[ds][0] * k, p3[1] + DIR[ds][1] * k)
        d = f"M{p0[0]:.1f} {p0[1]:.1f} C{p1[0]:.1f} {p1[1]:.1f} {p2[0]:.1f} {p2[1]:.1f} {p3[0]:.1f} {p3[1]:.1f}"

        def bz(t):
            u = 1 - t
            return (u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1])

        return d, bz(0.5), [bz(i / 60) for i in range(61)]

    def collisions(self):
        bad = []
        for e in self.E:
            _, _, smp = self.build(e)
            for nid, n in self.N.items():
                if nid in (e["s"], e["d"]):
                    continue
                x, y, w, h = self.rect(n)
                if any(x - 1 < px < x + w + 1 and y - 1 < py < y + h + 1 for px, py in smp):
                    bad.append((e["s"], e["d"], nid))
        return bad

    def overlaps(self):
        """노드끼리 겹치는 곳을 찾는다."""
        bad, ns = [], list(self.N.values())
        for i, a in enumerate(ns):
            for b in ns[i + 1:]:
                ax, ay, aw, ah = self.rect(a)
                bx, by, bw, bh = self.rect(b)
                if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                    bad.append((a["id"], b["id"]))
        return bad

    def svg(self):
        d = self.d
        vb = d.get("viewBox", [0, 0, 1450, 1000])
        o = [f'<svg id="g" class="fig" viewBox="{vb[0]} {vb[1]} {vb[2]} {vb[3]}" width="{vb[2]}" role="img" '
             f'aria-label="{esc(d["title"])}. 노드는 개념이고 선은 개념 사이의 관계이다.">']
        o.append('<defs>'
                 '<marker id="a-u" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 1 L10 5 L0 9 z" style="fill:var(--edge)"/></marker>'
                 '<marker id="a-1" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 1 L10 5 L0 9 z" style="fill:var(--w1-s)"/></marker>'
                 '</defs>')
        for h in d.get("hulls", []):
            sp = h.get("special")
            o.append(f'<rect class="hull{" hull-1" if sp else ""}" x="{h["x"]}" y="{h["y"]}" width="{h["w"]}" height="{h["h"]}" rx="14"/>')
            o.append(f'<text class="hull-t{" hull-t1" if sp else ""}" x="{h["x"] + 16}" y="{h["y"] + 22}">{esc(h["label"])}</text>')
        for e in self.E:
            path, lp, _ = self.build(e)
            src_sp = self.special is not None and self.N[e["s"]]["group"] == self.special and e["t"] == "u"
            cls = {"h": "e-h", "u": "e-w1" if src_sp else "e-u", "c": "e-c"}[e["t"]]
            marker = ""
            if e["t"] == "u":
                marker = ' marker-end="url(#a-1)"' if src_sp else ' marker-end="url(#a-u)"'
            lab = e.get("label", "")
            o.append(f'<g class="edge" data-from="{esc(e["s"])}" data-to="{esc(e["d"])}"><path class="{cls}" d="{path}"{marker}/>'
                     + (f'<text class="elbl" x="{lp[0]:.1f}" y="{lp[1] - 5:.1f}" text-anchor="middle">{esc(lab)}</text>' if lab else "")
                     + '</g>')
        for n in self.N.values():
            x, y, w, h = self.rect(n)
            g = [f'<g class="node" data-id="{esc(n["id"])}" tabindex="0" role="button" aria-label="{esc(n["label"])} ({esc(n["weeks"])})">',
                 f'<title>{esc(n["label"])} · {esc(n["weeks"])}: {esc(n["desc"])}</title>']
            if n.get("ring"):
                g.append(f'<rect class="ring" x="{x - 4}" y="{y - 4}" width="{w + 8}" height="{h + 8}" rx="14"/>')
            g.append(f'<rect class="p-w{n["group"]}" x="{x}" y="{y}" width="{w}" height="{h}" rx="11"/>')
            g.append(f'<text class="nt" x="{n["x"]}" y="{y + 19}" text-anchor="middle">{esc(n["label"])}</text>')
            g.append(f'<text class="nw" x="{n["x"]}" y="{y + 34}" text-anchor="middle">{esc(n["weeks"])}</text></g>')
            o.append("".join(g))
        o.append("</svg>")
        return "\n".join(o)

    def legend(self):
        li = [f'<li><span class="sw w{g["id"]}"></span>{esc(g["label"])}</li>' for g in self.d["groups"]]
        sp = next((g for g in self.d["groups"] if g.get("special")), None)
        if sp:
            li.append(f'<li><span class="sw ring"></span>{esc(sp["label"])}에도 나온 항목</li>')
            li.append(f'<li><span class="ln hull1"></span>{esc(sp["label"])} 묶음 (실선)</li>')
            li.append('<li><span class="ln hull"></span>그 밖의 묶음 (점선)</li>')
        else:
            li.append('<li><span class="ln hull"></span>묶음 (점선)</li>')
        li += ['<li><span class="ln h"></span>분류의 하위 항목</li>',
               '<li><span class="ln"></span>전제·적용 (화살표 방향)</li>',
               '<li><span class="ln c"></span>비교·대조</li>']
        if sp:
            li.append(f'<li><span class="ln w1"></span>{esc(sp["label"])}에서 나온 연결</li>')
        return "\n".join(li)

    def reading(self):
        sp = next((g for g in self.d["groups"] if g.get("special")), None)
        items = ["<li><b>색:</b> 항목을 처음 자세히 다룬 그룹입니다. 여러 주차에 걸친 항목은 항목 안의 작은 글씨에 주차를 모두 적었습니다.</li>"]
        if sp:
            items.append(f'<li><b>{esc(sp["label"])} 표시:</b> {esc(sp["label"])} 내용은 붉은색이고, 묶음 선도 실선입니다. '
                         f'{esc(sp["label"])}에서 나온 뒤 다시 나온 항목은 바깥에 붉은 테두리를 하나 더 붙였습니다.</li>')
        items.append("<li><b>선의 종류:</b> 회색 굵은 선은 분류의 하위 항목입니다. 화살표는 앞의 내용이 뒤의 내용에 쓰이거나 적용된다는 뜻입니다. 점선은 서로 비교되는 관계입니다.</li>")
        items.append("<li><b>강조:</b> 항목을 선택하면 그 항목과 직접 이어진 항목과 선만 남고, 선 위에 관계 설명이 나타납니다. 같은 항목을 다시 선택하거나 빈 곳을 선택하면 해제됩니다.</li>")
        return "\n".join(items)

    def render(self, template):
        d = self.d
        log = "\n".join(f'<li><b>{esc(c["date"])}:</b> {esc(c["summary"])}</li>' for c in reversed(d.get("changelog", [])))
        checks = "\n".join(f"<li>{c}</li>" for c in d.get("checks", []))
        data = json.dumps({k: dict(l=v["label"], w=v["weeks"], d=v["desc"]) for k, v in self.N.items()}, ensure_ascii=False)
        rep = {"{{TITLE}}": esc(d["title"]), "{{LEAD}}": d.get("lead", ""), "{{LEGEND}}": self.legend(),
               "{{SVG}}": self.svg(), "{{CAPTION}}": d.get("caption", ""), "{{READING}}": self.reading(),
               "{{CHANGELOG}}": log or "<li>아직 수정 이력이 없습니다.</li>",
               "{{CHECKS}}": checks or "<li>확인이 필요한 점이 없습니다.</li>", "{{DATA}}": data.replace("</", "<\\/"),
               "{{NN}}": str(len(self.N)), "{{NE}}": str(len(self.E))}
        out = template
        for k, v in rep.items():
            out = out.replace(k, v)
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("graph")
    ap.add_argument("--out")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    g = Graph(json.loads(Path(a.graph).read_text(encoding="utf-8")))
    bad, ov = g.collisions(), g.overlaps()
    print(f"항목 {len(g.N)}개, 연결 {len(g.E)}개, 노드를 지나가는 선 {len(bad)}건, 겹치는 노드 {len(ov)}건")
    for b in bad:
        print("  선이 노드를 지나감:", b)
    for b in ov:
        print("  노드가 겹침:", b)
    if a.check:
        sys.exit(1 if (bad or ov) else 0)
    if not a.out:
        raise SystemExit("--out 이 필요합니다.")
    tpl = (Path(__file__).with_name("graph_template.html")).read_text(encoding="utf-8")
    Path(a.out).write_text(g.render(tpl), encoding="utf-8")
    print("작성:", a.out)


if __name__ == "__main__":
    main()
