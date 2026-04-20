"""
awkplot — awk piped to uplot for terminal plots.
Usage: awkplot [awkplot-opts] [awk-opts] 'awk program' [file ...]
       awkplot [awkplot-opts] [awk-opts] -f prog.awk [file ...]
"""

import argparse
import shlex
import shutil
import signal
import subprocess
import sys

PLOT_TYPES = ["hist", "bar", "line", "lineplot", "scatter", "density", "box", "count"]


def build_parser():
    p = argparse.ArgumentParser(
        prog="awkplot",
        usage="%(prog)s [awkplot-opts] [awk-opts] 'program' [file ...]\n"
              "       %(prog)s [awkplot-opts] [awk-opts] -f prog.awk [file ...]",
        description="Run an awk program and pipe its output to uplot for terminal visualization.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""awk options:
  -F SEP           field separator (forwarded to awk)
  -v VAR=VAL       assign variable (repeatable, forwarded to awk)
  -f PROGFILE      read awk program from file (repeatable; first positional becomes a data file)

plot options:
  -p TYPE          plot type: hist bar line lineplot scatter density box count  [default: hist]
  -H               treat first output row as column headers (uplot --header)
  -c COLORS        comma-separated color(s), e.g. red,blue  (uplot --color)
  -s H:W           height:width, e.g. 20:60  (uplot --height / --width)
  -t TITLE         plot title  (uplot --title)
  -d DELIM         output column delimiter passed to uplot  (uplot --delimiter)
  --dry-run        print the awk | uplot command without running it

examples:
  awkplot -p hist '{print $3}' data.tsv
  awkplot -F, -H -p scatter -c cyan -s 20:60 '{print $2,$5}' data.csv
  cat data | awkplot -v t=10 -p bar '$1>t {print $2,$3}'
  awkplot -f prog.awk -p line data.tsv
""",
    )

    # ── awk passthrough flags ──────────────────────────────────────────────────
    p.add_argument("-F", dest="field_sep", metavar="SEP",
                   help="awk field separator")
    p.add_argument("-v", dest="awk_vars", metavar="VAR=VAL", action="append",
                   help="awk variable assignment (repeatable)")
    p.add_argument("-f", dest="prog_files", metavar="PROGFILE", action="append",
                   help="read awk program from file (repeatable)")

    # ── awkplot / uplot flags ─────────────────────────────────────────────────
    p.add_argument("-p", "--plot", dest="plot_type", metavar="TYPE",
                   default="hist", choices=PLOT_TYPES,
                   help="plot type [default: hist]")
    p.add_argument("-H", "--header", dest="header", action="store_true",
                   help="first output row is column headers")
    p.add_argument("-c", "--colors", dest="colors", metavar="COLORS",
                   help="comma-separated color list, e.g. red,blue")
    p.add_argument("-s", "--size", dest="size", metavar="H:W",
                   help="plot size as height:width, e.g. 20:60")
    p.add_argument("-t", "--title", dest="title", metavar="TITLE",
                   help="plot title")
    p.add_argument("-d", "--delimiter", dest="delimiter", metavar="DELIM",
                   help="output column delimiter for uplot")

    p.add_argument("--dry-run", dest="dry_run", action="store_true",
                   help="print the command pipeline without executing")

    # ── positionals ───────────────────────────────────────────────────────────
    p.add_argument("args", nargs=argparse.REMAINDER,
                   help="awk program (first arg) then input files, or just files when -f is used")

    return p


def parse_size(size_str):
    """Parse 'H:W' into (height, width) as strings."""
    parts = size_str.split(":")
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        sys.exit(f"awkplot: -s/--size must be H:W (e.g. 20:60), got: {size_str!r}")
    h, w = parts[0].strip(), parts[1].strip()
    if not h.isdigit() or not w.isdigit():
        sys.exit(f"awkplot: -s/--size values must be integers, got: {size_str!r}")
    return h, w


def check_deps():
    missing = []
    if not shutil.which("awk"):
        missing.append("awk  (brew install gawk)")
    if not shutil.which("uplot"):
        missing.append("uplot  (brew install youplot)")
    if missing:
        sys.exit("awkplot: required tools not found on PATH:\n  " + "\n  ".join(missing))


def build_awk_cmd(ns):
    cmd = ["awk"]
    if ns.field_sep is not None:
        cmd += ["-F", ns.field_sep]
    for var in (ns.awk_vars or []):
        cmd += ["-v", var]
    for pf in (ns.prog_files or []):
        cmd += ["-f", pf]

    positionals = ns.args
    if ns.prog_files:
        # all positionals are input files
        cmd += positionals
    else:
        # first positional is the awk program
        if not positionals:
            sys.exit("awkplot: awk program required as first positional argument\n"
                     "  hint: awkplot [opts] 'awk program' [file ...]")
        cmd.append(positionals[0])
        cmd += positionals[1:]

    return cmd


def build_uplot_cmd(ns):
    cmd = ["uplot", ns.plot_type]
    if ns.header:
        cmd.append("--header")
    if ns.colors:
        for color in ns.colors.split(","):
            color = color.strip()
            if color:
                cmd += ["--color", color]
    if ns.size:
        h, w = parse_size(ns.size)
        cmd += ["--height", h, "--width", w]
    if ns.title:
        cmd += ["--title", ns.title]
    if ns.delimiter:
        cmd += ["--delimiter", ns.delimiter]
    return cmd


def main():
    parser = build_parser()
    ns = parser.parse_args()

    awk_cmd = build_awk_cmd(ns)
    uplot_cmd = build_uplot_cmd(ns)

    if ns.dry_run:
        print(shlex.join(awk_cmd) + " | " + shlex.join(uplot_cmd))
        sys.exit(0)

    check_deps()

    # ── execute pipeline ───────────────────────────────────────────────────────
    # Ignore SIGPIPE in the parent so closing the write end doesn't crash us.
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)

    try:
        awk_proc = subprocess.Popen(awk_cmd, stdout=subprocess.PIPE)
        uplot_proc = subprocess.Popen(uplot_cmd, stdin=awk_proc.stdout)
        # Let awk_proc receive SIGPIPE if uplot exits early.
        awk_proc.stdout.close()

        uplot_rc = uplot_proc.wait()
        awk_rc = awk_proc.wait()

    except KeyboardInterrupt:
        sys.exit(130)
    except FileNotFoundError as e:
        sys.exit(f"awkplot: {e}")

    # Surface the first non-zero exit code, awk takes priority.
    if awk_rc != 0:
        sys.exit(awk_rc)
    if uplot_rc != 0:
        sys.exit(uplot_rc)


if __name__ == "__main__":
    main()
