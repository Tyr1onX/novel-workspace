from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path('novels/walk-to-earn/chapters')
PATTERNS = [
    ('record-only marker', re.compile('\u8fd9\u6761\u8bb0\u5f55\u53ea\u843d\u5728')),
    ('chapter-paragraph marker', re.compile(r'\u7b2c[0-9\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e\u96f6]+\u7ae0\u7b2c[0-9\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e\u96f6]+\u6bb5')),
    ('chapter-title wrapper', re.compile(r'\u7b2c[0-9\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e\u96f6]+\u7ae0\u300a[^\u300b]{2,60}\u300b\u5f00\u59cb\u65f6')),
]


def main() -> int:
    failures: list[str] = []
    if not ROOT.exists():
        print(f'Missing chapter directory: {ROOT}', file=sys.stderr)
        return 1
    for path in sorted(ROOT.glob('chapter-*.md')):
        text = path.read_text(encoding='utf-8')
        for name, pattern in PATTERNS:
            match = pattern.search(text)
            if match:
                failures.append(f'{path}: forbidden {name}: {match.group(0)}')
    if failures:
        print('Walk to Earn quality gate failed: batch/template markers remain.', file=sys.stderr)
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    print('Template marker check passed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
