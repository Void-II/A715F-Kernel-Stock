#!/usr/bin/env python3
"""
scripts/gcc-wrapper.py in this kernel tree is written for Python 2
(`print >> sys.stderr, ...` syntax, and treats subprocess stderr as
raw bytes). On any modern distro `python` resolves to Python 3, so
every compiler invocation the kernel build makes crashes silently
the moment gcc emits anything on stderr - which kbuild then
misreports as "flag not supported by compiler". This patches the
wrapper to be Python 3 compatible in place.
"""
path = "scripts/gcc-wrapper.py"

with open(path) as f:
    src = f.read()

replacements = [
    ('print >> sys.stderr, "error, forbidden warning:", m.group(2)',
     'print("error, forbidden warning:", m.group(2), file=sys.stderr)'),
    ('print >> sys.stderr, line,',
     "print(line, end='', file=sys.stderr)"),
    ("print >> sys.stderr, args[0] + ':',e.strerror",
     "print(args[0] + ':', e.strerror, file=sys.stderr)"),
    ("print >> sys.stderr, 'Is your PATH set correctly?'",
     "print('Is your PATH set correctly?', file=sys.stderr)"),
    ("print >> sys.stderr, ' '.join(args), str(e)",
     "print(' '.join(args), str(e), file=sys.stderr)"),
    ("proc = subprocess.Popen(args, stderr=subprocess.PIPE)",
     "proc = subprocess.Popen(args, stderr=subprocess.PIPE, universal_newlines=True)"),
]

missing = [old for old, _ in replacements if old not in src]
if missing:
    raise SystemExit(
        "gcc-wrapper.py patch targets not found - the script may have "
        f"changed upstream, review it manually: {missing}"
    )

for old, new in replacements:
    src = src.replace(old, new)

with open(path, "w") as f:
    f.write(src)

print("scripts/gcc-wrapper.py patched for Python 3 compatibility.")
