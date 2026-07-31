#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "$script_dir/.." && pwd)"
required_missing=0

say() {
  printf '%s\n' "$*"
}

check_required() {
  tool="$1"
  if command -v "$tool" >/dev/null 2>&1; then
    say "required: $tool -> $(command -v "$tool")"
  else
    say "MISSING required tool: $tool"
    required_missing=1
  fi
}

check_optional() {
  tool="$1"
  if command -v "$tool" >/dev/null 2>&1; then
    say "optional: $tool -> $(command -v "$tool")"
  else
    say "optional: $tool not found"
  fi
}

say "project: $project_root"
say "system: $(uname -a)"

check_required git
check_required uv
check_required java

if command -v git >/dev/null 2>&1; then
  git --version
fi
if command -v uv >/dev/null 2>&1; then
  uv --version
fi
if command -v java >/dev/null 2>&1; then
  java -version 2>&1 | sed -n '1,3p'
fi

case "$(uname -s)" in
  Darwin)
    say "host role: supported CPU-development host; Intel/AMD GPU tools are not expected"
    check_optional xcode-select
    ;;
  Linux)
    say "host role: Linux development/target candidate"
    check_optional lspci
    check_optional vulkaninfo
    check_optional clinfo
    check_optional sycl-ls
    check_optional zeinfo
    if [ -d /dev/dri ]; then
      say "DRM nodes:"
      ls -l /dev/dri
    else
      say "optional: /dev/dri not present"
    fi
    ;;
  *)
    say "warning: this operating system is not covered by the setup guides"
    ;;
esac

if [ -x "$project_root/minecraft-mod/gradlew" ]; then
  say "required: Gradle wrapper is executable"
else
  say "MISSING required executable: minecraft-mod/gradlew"
  required_missing=1
fi

if [ "$required_missing" -ne 0 ]; then
  say "environment check failed: install missing prerequisites; no changes were made"
  exit 1
fi

say "environment check passed (optional GPU capabilities may still be absent)"

