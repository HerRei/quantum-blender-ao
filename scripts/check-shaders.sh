#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
shader_root="$project_root/shaderpack/shaders"

if [[ ! -f "$shader_root/composite.vsh" || ! -f "$shader_root/composite.fsh" ]]; then
    printf '%s\n' "error: composite.vsh/composite.fsh pair is incomplete" >&2
    exit 1
fi

status=0
while IFS= read -r shader; do
    first_line="$(sed -n '/[^[:space:]]/{p;q;}' "$shader")"
    if [[ "$first_line" != \#version* ]]; then
        printf 'error: %s has no leading #version directive\n' "$shader" >&2
        status=1
    fi
    opening="$(tr -cd '{' < "$shader" | wc -c | tr -d ' ')"
    closing="$(tr -cd '}' < "$shader" | wc -c | tr -d ' ')"
    if [[ "$opening" != "$closing" ]]; then
        printf 'error: %s has unbalanced braces\n' "$shader" >&2
        status=1
    fi
done < <(find "$shader_root" -type f \( -name '*.vsh' -o -name '*.fsh' \) -print | sort)

while IFS= read -r include; do
    relative="${include#/}"
    if [[ ! -f "$shader_root/$relative" ]]; then
        printf 'error: missing shader include %s\n' "$include" >&2
        status=1
    fi
done < <(find "$shader_root" -type f \( -name '*.vsh' -o -name '*.fsh' \) \
    -exec sed -n 's/^[[:space:]]*#include[[:space:]]*"\([^"]*\)".*/\1/p' {} +)

if [[ "$status" -ne 0 ]]; then
    exit "$status"
fi
printf '%s\n' "shader scaffold static checks passed"
