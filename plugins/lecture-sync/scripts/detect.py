#!/usr/bin/env python3
"""강의자료 폴더의 변경을 감지한다.

기본 동작(SessionStart 훅): stdin의 훅 JSON에서 cwd를 읽고, 위쪽 폴더로 올라가며
`.lecture-sync.json`을 찾는다. 없으면 아무것도 출력하지 않는다. 있으면 새 파일과
수정된 파일을 찾아, 있을 때만 클로드에게 전달할 JSON을 출력한다.

옵션:
  --root DIR       폴더를 직접 지정한다. (기본: 훅 JSON의 cwd 또는 현재 폴더)
  --list           변경 내용을 JSON으로 출력한다.
  --baseline       현재 파일을 모두 처리 완료로 기록한다. 변경으로 보고하지 않는다.
  --commit [파일]  지정한 파일(폴더 기준 상대 경로)을 처리 완료로 기록한다. 파일을 생략하면 전부 기록한다.

--list 출력의 style, transcript는 과목 설정(.lecture-sync.json)의 정리 방식과 강의 영상 스크립트 사용 여부다.
값이 null이면 아직 정하지 않은 것이므로 스킬이 사용자에게 묻고 설정 파일에 저장한다.

같은 내용의 파일(다운로드 중복 표시 "(1)" 등)은 sha256이 같으면 새 자료로 보지 않는다.
훅으로 실행될 때는 어떤 경우에도 종료 코드 0으로 끝난다.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

CONFIG = ".lecture-sync.json"
STATE_DIR = ".lecture-sync"
MANIFEST = "manifest.json"
DEFAULT_EXT = [".pptx", ".ppt", ".pdf"]
STYLES = ("slides", "examples")


def study_options(cfg):
    """정리 방식과 강의 영상 스크립트 설정. 정하지 않았으면 None."""
    style = cfg.get("style") if cfg.get("style") in STYLES else None
    tr = cfg.get("transcript")
    if not isinstance(tr, dict) or not isinstance(tr.get("enabled"), bool):
        tr = None
    return style, tr


def find_root(start):
    p = Path(start).resolve()
    for d in [p, *p.parents]:
        if (d / CONFIG).is_file():
            return d
    return None


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scan(root, cfg, cache):
    """폴더의 강의자료를 {상대경로: {sha, size, mtime}}로 돌려준다. 크기와 수정 시각이 같으면 해시를 다시 계산하지 않는다."""
    exts = {e.lower() for e in cfg.get("extensions", DEFAULT_EXT)}
    out = {}
    for dp, dn, fn in os.walk(root):
        dn[:] = sorted(d for d in dn if not d.startswith("."))
        for f in sorted(fn):
            if f.startswith("~$") or f.startswith("."):
                continue
            if Path(f).suffix.lower() not in exts:
                continue
            full = Path(dp) / f
            rel = full.relative_to(root).as_posix()
            try:
                st = full.stat()
            except OSError:
                continue
            old = cache.get(rel)
            if old and old.get("size") == st.st_size and old.get("mtime") == int(st.st_mtime):
                out[rel] = old
            else:
                out[rel] = {"sha": sha256(full), "size": st.st_size, "mtime": int(st.st_mtime)}
    return out


def diff(current, manifest):
    known = manifest.get("files", {})
    known_hashes = {v["sha"] for v in known.values()}
    new, modified, aliases = [], [], []
    for rel, info in current.items():
        if rel in known:
            if known[rel]["sha"] != info["sha"]:
                modified.append(rel)
        elif info["sha"] in known_hashes:
            aliases.append(rel)  # 이미 처리한 내용의 복사본
        else:
            new.append(rel)
    return new, modified, aliases


def save_manifest(root, manifest):
    d = root / STATE_DIR
    d.mkdir(exist_ok=True)
    manifest["updated"] = datetime.now().isoformat(timespec="seconds")
    (d / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--commit", nargs="*", default=None)
    args = ap.parse_args()

    cwd = args.root
    hook_mode = not (args.list or args.baseline or args.commit is not None)
    if not cwd and not sys.stdin.isatty():
        try:
            cwd = json.load(sys.stdin).get("cwd")
        except ValueError:
            cwd = None
    root = find_root(cwd or os.getcwd())
    if root is None:
        if not hook_mode:
            print(f"{CONFIG}를 찾지 못했습니다.", file=sys.stderr)
            sys.exit(2)
        return

    cfg = load_json(root / CONFIG, {})
    manifest = load_json(root / STATE_DIR / MANIFEST, {"version": 1, "files": {}})
    current = scan(root, cfg, manifest.get("files", {}))

    if args.baseline:
        manifest["files"] = current
        save_manifest(root, manifest)
        print(f"기준 상태를 기록했습니다: 파일 {len(current)}개")
        return

    if args.commit is not None:
        targets = args.commit or list(current)
        for rel in targets:
            if rel in current:
                manifest.setdefault("files", {})[rel] = current[rel]
        # 복사본은 알려진 내용으로 함께 기록한다.
        _, _, aliases = diff(current, manifest)
        for rel in aliases:
            manifest["files"][rel] = current[rel]
        save_manifest(root, manifest)
        print(f"처리 완료로 기록했습니다: {len(targets)}개")
        return

    first_run = not (root / STATE_DIR / MANIFEST).is_file()
    new, modified, _ = diff(current, manifest)
    style, tr = study_options(cfg)
    if args.list:
        print(json.dumps({"root": str(root), "course": cfg.get("course", ""), "first_run": first_run,
                          "style": style, "transcript": tr,
                          "new": new, "modified": modified}, ensure_ascii=False, indent=2))
        return

    if not new and not modified:
        return
    course = cfg.get("course") or root.name
    if first_run:
        # 처음 설정한 과목은 기존 파일을 모두 처리할지 사용자가 정한다.
        context = (
            f"[lecture-sync] '{course}' 폴더가 처음 설정되었습니다. 기존 강의자료가 {len(new)}개 있습니다.\n"
            "사용자의 첫 요청을 처리하기 전에 /lecture-sync:sync 스킬을 실행하세요. "
            "스킬의 '처음 실행' 절차에 따라 기존 자료를 모두 정리할지, 처리한 것으로 기록만 할지, "
            "정리 방식(장별 보충본 또는 예시 위주 예제집)과 강의 영상 스크립트 사용 여부를 사용자에게 묻습니다."
        )
        print(json.dumps({
            "systemMessage": f"lecture-sync: '{course}' 폴더를 처음 확인했습니다. 기존 자료 {len(new)}개.",
            "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context},
        }, ensure_ascii=False))
        return
    lines = [f"- {r} (신규)" for r in new] + [f"- {r} (수정)" for r in modified]
    context = (
        f"[lecture-sync] '{course}' 폴더에서 처리하지 않은 강의자료 {len(lines)}건을 감지했습니다.\n"
        + "\n".join(lines)
        + "\n사용자의 첫 요청을 처리하기 전에 /lecture-sync:sync 스킬을 실행하세요. "
          + ("정리 방식과 강의 영상 스크립트 사용 여부가 아직 정해지지 않았으므로 먼저 사용자에게 묻습니다. "
             if style is None or tr is None else "")
        + "정리 문서 작성, 지식 그래프 갱신, 알림 메일 발송까지 진행합니다. "
          "시작하기 전에 처리할 파일을 사용자에게 한 줄로 알립니다."
    )
    print(json.dumps({
        "systemMessage": f"lecture-sync: 새 강의자료 {len(lines)}건을 감지했습니다.",
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context},
    }, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # 훅이 세션 시작을 막지 않도록 한다.
        print(f"lecture-sync 오류: {type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(0)
