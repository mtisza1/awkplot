"""Tests for awkplot_cli — build_awk_cmd, build_uplot_cmd, parse_size, and dry-run."""

import argparse
import subprocess
import sys
import types

import pytest

# Import the module under test
sys.path.insert(0, ".")
import awkplot_cli


# ─── helpers ──────────────────────────────────────────────────────────────────

def _parse(argv):
    """Parse *argv* through the real parser (no sys.argv mutation)."""
    parser = awkplot_cli.build_parser()
    return parser.parse_args(argv)


def _dry_run(argv):
    """Run the CLI with --dry-run and return the printed pipeline string."""
    result = subprocess.run(
        [sys.executable, "-m", "awkplot_cli", "--dry-run"] + argv,
        capture_output=True, text=True,
    )
    return result.stdout.strip(), result.returncode


# ─── parse_size ───────────────────────────────────────────────────────────────

class TestParseSize:
    def test_valid(self):
        assert awkplot_cli.parse_size("20:60") == ("20", "60")

    def test_valid_with_whitespace(self):
        assert awkplot_cli.parse_size(" 15 : 80 ") == ("15", "80")

    def test_missing_width(self):
        with pytest.raises(SystemExit):
            awkplot_cli.parse_size("20:")

    def test_missing_height(self):
        with pytest.raises(SystemExit):
            awkplot_cli.parse_size(":60")

    def test_non_numeric(self):
        with pytest.raises(SystemExit):
            awkplot_cli.parse_size("abc:60")

    def test_too_many_colons(self):
        with pytest.raises(SystemExit):
            awkplot_cli.parse_size("10:20:30")


# ─── build_awk_cmd ────────────────────────────────────────────────────────────

class TestBuildAwkCmd:
    def test_simple_program(self):
        ns = _parse(["{print $1}", "data.tsv"])
        cmd = awkplot_cli.build_awk_cmd(ns)
        assert cmd == ["awk", "{print $1}", "data.tsv"]

    def test_field_separator(self):
        ns = _parse(["-F", ",", "{print $1}", "data.csv"])
        cmd = awkplot_cli.build_awk_cmd(ns)
        assert cmd == ["awk", "-F", ",", "{print $1}", "data.csv"]

    def test_awk_vars(self):
        ns = _parse(["-v", "x=10", "-v", "y=20", "{print x, y}"])
        cmd = awkplot_cli.build_awk_cmd(ns)
        assert cmd == ["awk", "-v", "x=10", "-v", "y=20", "{print x, y}"]

    def test_prog_file(self):
        ns = _parse(["-f", "prog.awk", "data.tsv"])
        cmd = awkplot_cli.build_awk_cmd(ns)
        assert cmd == ["awk", "-f", "prog.awk", "data.tsv"]

    def test_no_program_defaults_to_print(self):
        """Issue #1: when no program and no -f, default to {print}."""
        ns = _parse(["-p", "hist"])
        cmd = awkplot_cli.build_awk_cmd(ns)
        assert cmd == ["awk", "{print}"]

    def test_no_args_at_all_defaults_to_print(self):
        """Bare invocation should also default to {print}."""
        ns = _parse([])
        cmd = awkplot_cli.build_awk_cmd(ns)
        assert cmd == ["awk", "{print}"]


# ─── build_uplot_cmd ─────────────────────────────────────────────────────────

class TestBuildUplotCmd:
    def test_default_hist(self):
        ns = _parse(["{print $1}"])
        cmd = awkplot_cli.build_uplot_cmd(ns)
        assert cmd == ["uplot", "hist"]

    def test_plot_type(self):
        ns = _parse(["-p", "bar", "{print $1}"])
        cmd = awkplot_cli.build_uplot_cmd(ns)
        assert cmd == ["uplot", "bar"]

    def test_header(self):
        ns = _parse(["-H", "{print $1}"])
        cmd = awkplot_cli.build_uplot_cmd(ns)
        assert "--header" in cmd

    def test_colors(self):
        ns = _parse(["-c", "red,blue", "{print $1}"])
        cmd = awkplot_cli.build_uplot_cmd(ns)
        assert cmd == ["uplot", "hist", "--color", "red", "--color", "blue"]

    def test_size(self):
        ns = _parse(["-s", "20:60", "{print $1}"])
        cmd = awkplot_cli.build_uplot_cmd(ns)
        assert "--height" in cmd and "--width" in cmd
        h_idx = cmd.index("--height")
        w_idx = cmd.index("--width")
        assert cmd[h_idx + 1] == "20"
        assert cmd[w_idx + 1] == "60"

    def test_title(self):
        ns = _parse(["-t", "My Title", "{print $1}"])
        cmd = awkplot_cli.build_uplot_cmd(ns)
        assert cmd == ["uplot", "hist", "--title", "My Title"]

    def test_delimiter(self):
        ns = _parse(["-d", ",", "{print $1}"])
        cmd = awkplot_cli.build_uplot_cmd(ns)
        assert cmd == ["uplot", "hist", "--delimiter", ","]

    def test_uplot_args_passthrough(self):
        ns = _parse(["--uplot-args", "--nbins 30", "{print $1}"])
        cmd = awkplot_cli.build_uplot_cmd(ns)
        assert "--nbins" in cmd
        assert "30" in cmd

    def test_all_flags(self):
        ns = _parse([
            "-p", "scatter", "-H", "-c", "cyan", "-s", "20:60",
            "-t", "test", "-d", "\t", "{print $1, $2}",
        ])
        cmd = awkplot_cli.build_uplot_cmd(ns)
        assert cmd[1] == "scatter"
        assert "--header" in cmd
        assert "--color" in cmd
        assert "--height" in cmd
        assert "--title" in cmd
        assert "--delimiter" in cmd


# ─── swallowed flags detection (issue #2) ────────────────────────────────────

class TestSwallowedFlags:
    def test_flag_after_program_errors(self):
        """Issue #2: flags after awk program should error, not be swallowed."""
        with pytest.raises(SystemExit):
            ns = _parse(["{print $1}", "data.csv", "-p", "bar", "-t", "hi"])
            awkplot_cli.build_awk_cmd(ns)

    def test_flag_after_files_with_prog_file_errors(self):
        """When -f is used, positionals that look like flags should error."""
        with pytest.raises(SystemExit):
            ns = _parse(["-f", "prog.awk", "data.tsv", "--title", "oops"])
            awkplot_cli.build_awk_cmd(ns)


# ─── dry-run integration tests ───────────────────────────────────────────────

class TestDryRun:
    def test_simple(self):
        output, rc = _dry_run(["{print $1}", "data.tsv"])
        assert rc == 0
        assert "awk" in output
        assert "{print $1}" in output
        assert "data.tsv" in output
        assert "uplot hist" in output

    def test_with_flags(self):
        output, rc = _dry_run(["-p", "scatter", "-t", "test", "-s", "20:60",
                               "{print $1, $2}", "data.csv"])
        assert rc == 0
        assert "uplot scatter" in output
        assert "--title" in output
        assert "--height" in output

    def test_no_program_defaults_to_print(self):
        """Issue #1: dry-run should work with no awk program."""
        output, rc = _dry_run(["-p", "hist", "-t", "test"])
        assert rc == 0
        assert "{print}" in output

    def test_field_sep(self):
        output, rc = _dry_run(["-F", ",", "{print $1}", "data.csv"])
        assert rc == 0
        assert "-F" in output

    def test_prog_file(self):
        output, rc = _dry_run(["-f", "prog.awk", "data.tsv"])
        assert rc == 0
        assert "-f" in output
        assert "prog.awk" in output

    def test_uplot_args_passthrough(self):
        output, rc = _dry_run(["--uplot-args", "--nbins 30", "{print $1}"])
        assert rc == 0
        assert "--nbins" in output
        assert "30" in output


# ─── version flag ─────────────────────────────────────────────────────────────

class TestVersion:
    def test_version_flag(self):
        result = subprocess.run(
            [sys.executable, "-m", "awkplot_cli", "--version"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert awkplot_cli.__version__ in result.stdout
