#!/usr/bin/env python3
"""監視スロットの登録runnerを確認する。ネットワーク・通知・CSV台帳には触れない。"""
import argparse
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / 'monitoring' / 'state.json'


def _write_atomic(path, state):
    raw = json.dumps(state, ensure_ascii=False, indent=2).encode('utf-8') + b'\n'
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.runner-guard-')
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def check(state_path, slot, actor, record=False, attempted_at=None):
    """Return (exit code, message) for a runner registration check."""
    path = Path(state_path)
    try:
        state = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return 2, 'state.jsonが存在しないか形式不正です'
    if not isinstance(state, dict):
        return 2, 'state.jsonが存在しないか形式不正です'
    runners = state.get('runners', {})
    if not isinstance(runners, dict):
        return 2, 'state.jsonのrunners形式が不正です'
    registration = runners.get(slot)
    if registration is not None and (
            not isinstance(registration, dict)
            or not isinstance(registration.get('actor'), str)
            or not registration['actor']):
        return 2, 'state.jsonのrunner登録形式が不正です'

    if registration is None:
        code = 4
        message = '未登録: slot=%s actor=%s' % (slot, actor)
        detail = 'runner未登録: slot=%s actor=%s' % (slot, actor)
    elif registration['actor'] != actor:
        code = 3
        message = 'runner不一致: slot=%s registered=%s requested=%s' % (
            slot, registration['actor'], actor)
        detail = message
    else:
        return 0, 'runner一致: slot=%s actor=%s' % (slot, actor)

    if record:
        state['lastAttemptAt'] = attempted_at or datetime.now().astimezone().isoformat(timespec='seconds')
        state['lastStatus'] = 'SKIPPED'
        state['detail'] = detail
        try:
            _write_atomic(path, state)
        except OSError:
            return 2, 'state.jsonへSKIPPEDを記録できません'
    return code, message


def main(argv=None):
    parser = argparse.ArgumentParser(description='監視スロットのrunner登録を確認します')
    subparsers = parser.add_subparsers(dest='command', required=True)
    command = subparsers.add_parser('check')
    command.add_argument('--slot', required=True)
    command.add_argument('--actor', required=True)
    command.add_argument('--record', action='store_true')
    command.add_argument('--state', default=str(DEFAULT_STATE), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not (len(args.slot) == 4 and args.slot.isdigit()):
        parser.error('--slot は4桁の時刻です（例 0730）')
    code, message = check(args.state, args.slot, args.actor, args.record)
    print(message)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
