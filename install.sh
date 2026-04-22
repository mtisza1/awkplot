#!/usr/bin/env bash
# awkplot installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/mtisza1/awkplot/main/install.sh | bash
#
# Env vars:
#   AWKPLOT_PREFIX    install dir (default: $HOME/.local/bin)
#   AWKPLOT_REF       git ref / branch / tag (default: main)
#   AWKPLOT_REPO      GitHub repo slug (default: mtisza1/awkplot)
#   AWKPLOT_SKIP_DEPS set to 1 to skip installing uplot

set -euo pipefail

REPO="${AWKPLOT_REPO:-mtisza1/awkplot}"
REF="${AWKPLOT_REF:-main}"
PREFIX="${AWKPLOT_PREFIX:-$HOME/.local/bin}"
SKIP_DEPS="${AWKPLOT_SKIP_DEPS:-0}"
RAW_BASE="https://raw.githubusercontent.com/${REPO}/${REF}"

c_reset=$'\033[0m'; c_bold=$'\033[1m'
c_green=$'\033[32m'; c_yellow=$'\033[33m'; c_red=$'\033[31m'; c_blue=$'\033[34m'
info()  { printf "%s==>%s %s\n" "${c_blue}${c_bold}" "${c_reset}" "$*"; }
warn()  { printf "%swarn:%s %s\n" "${c_yellow}${c_bold}" "${c_reset}" "$*" >&2; }
err()   { printf "%serror:%s %s\n" "${c_red}${c_bold}" "${c_reset}" "$*" >&2; }
ok()    { printf "%sok:%s %s\n" "${c_green}${c_bold}" "${c_reset}" "$*"; }
have()  { command -v "$1" >/dev/null 2>&1; }

case "$(uname -s)" in
  Darwin) PLATFORM=macos ;;
  Linux)  PLATFORM=linux ;;
  *)      err "unsupported OS: $(uname -s)"; exit 1 ;;
esac
info "platform: $PLATFORM"

have python3 || { err "python3 not found — awkplot needs python3 on PATH"; exit 1; }
ok "python3: $(command -v python3)"

have awk || { err "awk not found (unusual)"; exit 1; }
ok "awk: $(command -v awk)"

install_uplot() {
  [[ "$SKIP_DEPS" == "1" ]] && { warn "AWKPLOT_SKIP_DEPS=1 — skipping uplot install"; return 0; }

  case "$PLATFORM" in
    macos)
      if have brew; then
        info "installing uplot via homebrew…"
        brew install youplot
      elif have gem; then
        info "installing uplot via rubygems…"
        gem install youplot
      else
        err "need 'brew' (https://brew.sh) or 'gem' to install uplot"
        echo "  or rerun with AWKPLOT_SKIP_DEPS=1 after installing uplot manually"
        exit 1
      fi
      ;;
    linux)
      if have gem; then
        info "installing uplot via rubygems…"
        gem install --user-install youplot || gem install youplot
      elif have apt-get; then
        warn "ruby/gem not found — installing ruby via apt (may require sudo)"
        sudo apt-get update && sudo apt-get install -y ruby ruby-dev
        gem install --user-install youplot
      else
        err "could not find 'gem' or 'apt-get'"
        echo "  install ruby, then: gem install youplot"
        echo "  or rerun with AWKPLOT_SKIP_DEPS=1 after installing uplot manually"
        exit 1
      fi
      ;;
  esac
}

if have uplot; then
  ok "uplot: $(command -v uplot)"
else
  install_uplot
  if have uplot; then
    ok "uplot: $(command -v uplot)"
  else
    warn "uplot install finished but 'uplot' is not on PATH"
    warn "you may need: export PATH=\"\$(gem env user_gemhome)/bin:\$PATH\""
  fi
fi

mkdir -p "$PREFIX"
info "installing awkplot to: $PREFIX"

fetch() {
  if have curl; then curl -fsSL "$1" -o "$2"
  elif have wget; then wget -qO "$2" "$1"
  else err "need curl or wget to download awkplot"; exit 1
  fi
}

fetch "${RAW_BASE}/awkplot"        "${PREFIX}/awkplot"
fetch "${RAW_BASE}/awkplot_cli.py" "${PREFIX}/awkplot_cli.py"
chmod +x "${PREFIX}/awkplot"

ok "installed: ${PREFIX}/awkplot"
ok "installed: ${PREFIX}/awkplot_cli.py"

case ":$PATH:" in
  *":$PREFIX:"*) ok "$PREFIX is on PATH" ;;
  *)
    warn "$PREFIX is NOT on PATH"
    echo "  add to your shell rc:  export PATH=\"$PREFIX:\$PATH\""
    ;;
esac

echo
info "quick verification:"
if "${PREFIX}/awkplot" --dry-run -p hist '{print $1}' /dev/null >/dev/null 2>&1; then
  ok "awkplot is working"
else
  warn "awkplot installed but --dry-run failed — check python3 shebang"
fi

echo
printf "%sawkplot installed!%s Try:\n" "${c_green}${c_bold}" "${c_reset}"
printf "  awkplot -p hist 'BEGIN{srand();for(i=0;i<200;i++)print int(rand()*50)}'"
