# Baseline Testing

| Prüfung | Befehl | Exitcode | Ergebnis |
| ------- | ------ | -------: | -------- |
| Environment Check | `./scripts/check-environment.sh` | 0 | Environment check passed |
| Shader Scaffold Check | `./scripts/check-shaders.sh` | 0 | Shader scaffold static checks passed |
| Python Lint (Ruff) | `uv run ... ruff check` | 0 | All checks passed (no issues in 21 files) |
| Python Type (Mypy) | `uv run ... mypy` | 0 | Success |
| Python Tests | `uv run ... pytest` | 0 | 104 passed in 19.78s |
| Java Tests / Build | `./gradlew build --no-daemon` | 0 | BUILD SUCCESSFUL |

All baseline checks passed cleanly without modifications.
