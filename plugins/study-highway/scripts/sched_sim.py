#!/usr/bin/env python3
"""단일 CPU 실시간 스케줄링을 1 시간 단위로 시뮬레이션하고, build_notes.py의 timeline 그림 데이터를 만든다.

보충본의 인터랙티브 그림은 손으로 칸을 채우지 않고 이 모듈로 계산한다. 슬라이드 예제와 결과(완료 시각,
response time)를 대조해 검증한 뒤 쓴다.

사용 예:
    from sched_sim import Task, Job, simulate
    tasks = [Task("T1", prio=1, period=4, wcet=1), Task("T2", prio=2, period=6, wcet=2)]
    r = simulate(tasks, horizon=12, policy="fixed")
    r.timeline()      # build_notes.py의 figures[].timeline 값
    r.response        # {job 이름: response time}

Task 필드
    id, prio(작을수록 높음, fixed 정책), period, wcet, deadline(상대, 기본 period), phase(기본 0),
    segs: job 하나의 실행 순서. 칸마다 그 1단위 동안 잡고 있어야 하는 자원. "" 또는 "E"는 자원 없음,
    "Q"는 Q를 잡고 실행, "Q+V"는 둘 다 잡고 실행(nested). 없으면 ["E"] * wcet.
    label: 행 이름(기본 id). jobs가 따로 주어지면 period가 없어도 된다.
Job 필드 (주기 없이 job을 직접 줄 때)
    task(Task id), release, segs(없으면 task의 segs), deadline(절대 시각, 선택)

policy: "fixed"(Task.prio), "edf"(절대 deadline), "lst"(slack = deadline - t - 남은 실행 시간)
ceilings: {자원: 우선순위}로 ceiling을 직접 정한다. 예: non-preemptable section은 자원 "NPS"를 쓰고
          protocol="pce", ceilings={"NPS": 가장 높은 우선순위}로 흉내 낸다.
protocol: "none", "pip"(Basic Priority Inheritance), "pcp"(Priority Ceiling Protocol),
          "pce"(Priority Ceiling Emulation). ceiling은 fixed 정책에서 그 자원을 쓰는 task의 가장 높은 우선순위다.
preemptive: False면 실행 중인 job이 끝날 때까지 계속 실행한다.
같은 우선순위면 먼저 release된 job, 그다음 task 순서가 먼저다(tie="release").
tie="order"이면 task 순서(번호가 작은 task)가 먼저다.
tie="running"이면 실행 중이던 job, 그다음 deadline이 빠른 job이 먼저다(LST 그림처럼 동점에서 계속 실행).
모든 대기 job이 서로 막혀 실행할 job이 없으면 deadlock으로 보고, 그 시각부터 막힌 job을 D로 채운다.
"""
from dataclasses import dataclass, field
from typing import Optional


_DIGIT_BATCHIM = {"0": True, "1": True, "2": False, "3": True, "4": False, "5": False, "6": True, "7": True, "8": True, "9": False}
_LATIN_BATCHIM = set("LMNR")


def _batchim(word):
    w = str(word).rstrip(" )]")
    if not w:
        return False
    c = w[-1]
    if "가" <= c <= "힣":
        return (ord(c) - 0xAC00) % 28 != 0
    if c in _DIGIT_BATCHIM:
        return _DIGIT_BATCHIM[c]
    return c.upper() in _LATIN_BATCHIM


def josa(word, pair):
    """josa("T1", "이/가") -> "T1이". pair는 "이/가", "을/를", "은/는", "과/와"."""
    a, b = pair.split("/")
    return f"{word}{a if _batchim(word) else b}"


@dataclass
class Task:
    id: str
    prio: int = 0
    period: Optional[int] = None
    wcet: int = 1
    deadline: Optional[int] = None
    phase: int = 0
    segs: Optional[list] = None
    label: Optional[str] = None


@dataclass
class Job:
    task: str
    release: int
    segs: Optional[list] = None
    deadline: Optional[int] = None
    name: str = ""
    # 실행 중 상태
    pos: int = 0
    held: frozenset = field(default_factory=frozenset)
    finish: Optional[int] = None


def _tok(x):
    x = (x or "").strip()
    if x in ("", "E", "L"):
        return frozenset()
    return frozenset(p.strip() for p in x.split("+") if p.strip())


class Result:
    def __init__(self, tasks, horizon, cells, prio, marks, notes, jobs, res, intro, deadlock_at):
        self.tasks, self.T, self.cells, self.prio, self.marks = tasks, horizon, cells, prio, marks
        self.notes, self.jobs, self.res, self.intro, self.deadlock_at = notes, jobs, res, intro, deadlock_at
        self.finish = {j.name: j.finish for j in jobs}
        self.response = {j.name: (j.finish - j.release) if j.finish is not None else None for j in jobs}
        self.missed = [j.name for j in jobs if j.deadline is not None and (j.finish is None or j.finish > j.deadline)
                       and j.deadline <= horizon]

    def timeline(self, labels=None, extra_notes=None, intro=None, show_prio=True, **opts):
        rows = []
        for t in self.tasks:
            r = {"id": t.id, "label": (labels or {}).get(t.id, t.label or t.id), "short": t.id}
            if show_prio and self.prio.get(t.id):
                r["base"] = t.prio
            rows.append(r)
        notes = dict(self.notes)
        for k, v in (extra_notes or {}).items():
            k = str(k)
            notes[k] = (notes[k] + "<br>" + v) if k in notes else v
        d = {"T": self.T, "rows": rows, "cells": self.cells, "res": self.res, "marks": self.marks,
             "notes": notes, "intro": intro or self.intro}
        if show_prio and any(self.prio.values()):
            d["prio"] = self.prio
        d.update(opts)
        return d

    def table(self):
        """디버깅용 문자열 표."""
        out = []
        for t in self.tasks:
            out.append(f"{t.id:>4} " + "".join(f"{(c or '.'):>4}" for c in self.cells[t.id]))
        return "\n".join(out)


def make_jobs(tasks, horizon, jobs=None):
    tmap = {t.id: t for t in tasks}
    out = []
    if jobs:
        for j in jobs:
            t = tmap[j.task]
            segs = j.segs or t.segs or ["E"] * t.wcet
            out.append(Job(j.task, j.release, list(segs), j.deadline if j.deadline is not None else
                           (j.release + t.deadline if t.deadline is not None else None)))
    else:
        for t in tasks:
            if not t.period:
                out.append(Job(t.id, t.phase, list(t.segs or ["E"] * t.wcet),
                               t.phase + t.deadline if t.deadline is not None else None))
                continue
            D = t.deadline if t.deadline is not None else t.period
            r = t.phase
            while r < horizon:
                out.append(Job(t.id, r, list(t.segs or ["E"] * t.wcet), r + D))
                r += t.period
    cnt = {}
    for j in sorted(out, key=lambda j: (j.task, j.release)):
        cnt[j.task] = cnt.get(j.task, 0) + 1
        j.name = f"{j.task},{cnt[j.task]}"
    return out


def simulate(tasks, horizon, policy="fixed", protocol="none", jobs=None, preemptive=True, narrate=True, tie="release", ceilings=None):
    order = {t.id: i for i, t in enumerate(tasks)}
    tmap = {t.id: t for t in tasks}
    J = make_jobs(tasks, horizon, jobs)
    uses = {}
    for j in J:
        for s in j.segs:
            for r in _tok(s):
                uses.setdefault(r, set()).add(j.task)
    res = sorted(uses)
    # 우선순위 값: 클수록 높다. fixed에서 prio p는 -p.
    ceil = {r: max(-tmap[t].prio for t in ts) for r, ts in uses.items()}
    for r, pr in (ceilings or {}).items():
        ceil[r] = -pr
    cells = {t.id: [""] * horizon for t in tasks}
    prio = {t.id: [None] * horizon for t in tasks}
    marks, notes = [], {}
    last = None
    deadlock_at = None
    holder_prev = {}

    def note(t, s):
        if narrate:
            notes[str(t)] = (notes[str(t)] + " " + s) if str(t) in notes else s

    for j in J:
        if j.release < horizon:
            marks.append({"row": j.task, "t": j.release, "type": "rel"})
        if j.deadline is not None and j.deadline <= horizon:
            marks.append({"row": j.task, "t": j.deadline, "type": "dl"})

    def base(j, t):
        if policy == "fixed":
            return -tmap[j.task].prio
        if policy == "edf":
            return -(j.deadline if j.deadline is not None else 10 ** 9)
        if policy == "lst":
            rem = len(j.segs) - j.pos
            return -((j.deadline if j.deadline is not None else 10 ** 9) - t - rem)
        raise ValueError(policy)

    for t in range(horizon):
        act = [j for j in J if j.release <= t and j.finish is None]
        for j in act:
            if j.release == t:
                note(t, f"{j.task} release.")
        if not act:
            last = None
            continue
        eff = {id(j): base(j, t) for j in act}
        if protocol == "pce":
            for j in act:
                for r in j.held:
                    eff[id(j)] = max(eff[id(j)], ceil[r])
        holder = {}
        for j in act:
            for r in j.held:
                holder[r] = j
        blocked = {}
        for _ in range(len(act) + 3):
            blocked = {}
            for j in act:
                need = _tok(j.segs[j.pos])
                new = need - j.held
                if not new:
                    continue
                direct = [holder[r] for r in new if r in holder and holder[r] is not j]
                if direct:
                    blocked[id(j)] = ("B", direct[0], sorted(r for r in new if r in holder)[0])
                    continue
                if protocol == "pcp":
                    others = [(ceil[r], r, holder[r]) for r in holder if holder[r] is not j]
                    if others:
                        c, r, h = max(others, key=lambda x: (x[0], x[1]))
                        if not eff[id(j)] > c:
                            blocked[id(j)] = ("K", h, r)
            if protocol in ("pip", "pcp"):
                changed = False
                for j in act:
                    if id(j) in blocked:
                        h = blocked[id(j)][1]
                        if eff[id(h)] < eff[id(j)]:
                            eff[id(h)] = eff[id(j)]
                            changed = True
                if not changed:
                    break
            else:
                break
        runnable = [j for j in act if id(j) not in blocked]
        if not runnable:
            deadlock_at = t
            note(t, "실행할 수 있는 job이 없습니다. 서로가 잡은 자원을 기다리므로 deadlock입니다.")
            for tt in range(t, horizon):
                for j in act:
                    cells[j.task][tt] = "D"
            break
        if not preemptive and last is not None and last in runnable:
            run = last
        else:
            if tie == "running":
                run = max(runnable, key=lambda j: (eff[id(j)], j is last, -(j.deadline if j.deadline is not None else 10 ** 9),
                                                   -j.release, -order[j.task]))
            elif tie == "order":
                run = max(runnable, key=lambda j: (eff[id(j)], -order[j.task], -j.release))
            else:
                run = max(runnable, key=lambda j: (eff[id(j)], -j.release, -order[j.task]))
        # 기록: 막힌 job은 원래 실행될 차례(실행 job 이상 우선순위)일 때만 blocked로 표시한다.
        shown_blk = {k: v for k, v in blocked.items()
                     if eff[k] >= eff[id(run)]}
        for j in act:
            p = eff[id(j)]
            prio[j.task][t] = -p if policy == "fixed" else None
            if j is run:
                continue
            if id(j) in shown_blk:
                kind, h, r = shown_blk[id(j)]
                cells[j.task][t] = kind
            elif (protocol == "pce" and (run.held or _tok(run.segs[run.pos]))
                  and eff[id(run)] >= eff[id(j)] > base(run, t)):
                cells[j.task][t] = "K"
                key = (j.name, "K", run.name)
                if holder_prev.get(j.name) != key:
                    note(t, f"{josa(j.task, "은/는")} {josa(run.task, "이/가")} 자원을 잡아 ceiling 우선순위 {-eff[id(run)]}로 올라가 있어 실행되지 못함.")
                    holder_prev[j.name] = key
            else:
                cells[j.task][t] = "W"
        need = _tok(run.segs[run.pos])
        cells[run.task][t] = ("C:" + "+".join(sorted(need))) if need else "R"
        # 설명
        for j in act:
            if id(j) in shown_blk:
                kind, h, r = shown_blk[id(j)]
                key = (j.name, kind, h.name)
                if holder_prev.get(j.name) != key:
                    if kind == "B":
                        note(t, f"{josa(j.task, "이/가")} {josa(r, "을/를")} 요청했지만 {josa(h.task, "이/가")} 잡고 있어 blocked.")
                    else:
                        note(t, f"{j.task}의 lock 요청 거절: {josa(h.task, "이/가")} 잡은 {r}의 ceiling {-ceil[r]}보다 {j.task}의 우선순위가 높지 않음.")
                    if protocol in ("pip", "pcp"):
                        note(t, f"{josa(h.task, "이/가")} 우선순위 {josa(-eff[id(h)], "을/를")} 물려받음.")
                    holder_prev[j.name] = key
            elif cells[j.task][t] != "K":
                holder_prev.pop(j.name, None)
        if run is not last and last is not None and last.finish is None and last in act:
            note(t, f"{josa(run.task, "이/가")} {josa(last.task, "을/를")} 선점.")
        newl = need - run.held
        for r in sorted(newl):
            note(t, f"{josa(run.task, "이/가")} {josa(r, "을/를")} lock" + (f"하고 우선순위가 ceiling {-ceil[r]}로 올라감." if protocol == "pce" else "."))
        # 실행
        run.pos += 1
        nxt = _tok(run.segs[run.pos]) if run.pos < len(run.segs) else frozenset()
        keep = need & nxt
        for r in sorted(need - keep):
            note(t, f"{josa(run.task, "이/가")} {josa(r, "을/를")} unlock.")
        run.held = frozenset(keep)
        last = run
        if run.pos >= len(run.segs):
            run.finish = t + 1
            marks.append({"row": run.task, "t": t + 1, "type": "done"})
            note(t, f"{run.task} 완료 (response time {run.finish - run.release}).")
        for j in act:
            if j.deadline is not None and j.deadline == t + 1 and j.finish is None:
                marks.append({"row": j.task, "t": t + 1, "type": "miss"})
                note(t, f"{josa(j.task, "이/가")} deadline {josa(j.deadline, "을/를")} 놓침.")
    intro = None
    return Result(tasks, horizon, cells, {k: v for k, v in prio.items()}, marks, notes, J, res, intro, deadlock_at)


def table_timeline(rows, horizon, spans, notes=None, marks=None, intro=None, res=None, **opts):
    """미리 정한 표(cyclic executive 등)를 timeline으로 만든다.
    rows: [(id, label)], spans: [(시작, 끝, row id, 칸 기호)]"""
    cells = {r: [""] * horizon for r, _ in rows}
    for a, b, r, v in spans:
        for t in range(a, b):
            cells[r][t] = v
    d = {"T": horizon, "rows": [{"id": r, "label": l, "short": r} for r, l in rows], "cells": cells,
         "res": res or [], "marks": marks or [], "notes": {str(k): v for k, v in (notes or {}).items()},
         "intro": intro}
    d.update(opts)
    return d
