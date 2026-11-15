#!/usr/bin/env bash
#
# Build the Tanita report.
#
# The script does four steps:
#   1. Find the virtual environment.
#   2. Create the virtual environment when it is missing.
#   3. Install the requirements when they changed.
#   4. Run tanita_report.py and write the PDF to the output folder.
#
# Usage:
#   ./run_report.sh
#   ./run_report.sh DATA1.CSV
#   ./run_report.sh DATA1.CSV --lang en
#   ./run_report.sh --lang en

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CALL_DIR="$(pwd)"

VENV_DIR="${VENV_DIR:-.venv}"
VENV_PY="$VENV_DIR/bin/python"
REQUIREMENTS="requirements.txt"
STAMP="$VENV_DIR/.requirements.sha256"
REQUIRED_PYTHON="3.11"

# The first argument is the input file when it does not start with a dash.
INPUT="DATA1.CSV"
if [ "$#" -gt 0 ] && [ "${1:0:1}" != "-" ]; then
    INPUT="$1"
    shift
fi

# Resolve the input path against the caller directory, then the project directory.
case "$INPUT" in
    /*) INPUT_PATH="$INPUT" ;;
    *) INPUT_PATH="$CALL_DIR/$INPUT" ;;
esac
if [ ! -f "$INPUT_PATH" ] && [ -f "$SCRIPT_DIR/$INPUT" ]; then
    INPUT_PATH="$SCRIPT_DIR/$INPUT"
fi

cd "$SCRIPT_DIR"

if [ ! -f "$INPUT_PATH" ]; then
    printf 'Error: input file not found: %s\n' "$INPUT" >&2
    exit 1
fi

# Step 1: find or create the virtual environment.
printf 'Step 1: check the virtual environment.\n'

if [ -d "$VENV_DIR" ] && [ -x "$VENV_PY" ] && "$VENV_PY" -c 'import sys' >/dev/null 2>&1; then
    printf 'Virtual environment found: %s\n' "$VENV_DIR"
else
    if [ -e "$VENV_DIR" ]; then
        printf 'Error: %s exists but it is not a usable virtual environment.\n' "$VENV_DIR" >&2
        printf 'Remove it and run this script again.\n' >&2
        exit 1
    fi

    printf 'Virtual environment not found. Creating it with Python %s.\n' "$REQUIRED_PYTHON"
    if command -v uv >/dev/null 2>&1; then
        uv venv --python "$REQUIRED_PYTHON" --seed "$VENV_DIR"
    elif command -v "python$REQUIRED_PYTHON" >/dev/null 2>&1; then
        "python$REQUIRED_PYTHON" -m venv "$VENV_DIR"
    else
        printf 'Error: cannot create the virtual environment.\n' >&2
        printf 'Install uv, or install Python %s.\n' "$REQUIRED_PYTHON" >&2
        exit 1
    fi
fi

if [ ! -x "$VENV_PY" ]; then
    printf 'Error: the virtual environment has no Python: %s\n' "$VENV_PY" >&2
    exit 1
fi

PYTHON_VERSION="$("$VENV_PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
if [ "$PYTHON_VERSION" != "$REQUIRED_PYTHON" ]; then
    printf 'Error: %s uses Python %s. The requirements need Python %s.\n' \
        "$VENV_DIR" "$PYTHON_VERSION" "$REQUIRED_PYTHON" >&2
    printf 'Remove %s and run this script again.\n' "$VENV_DIR" >&2
    exit 1
fi
printf 'Python version: %s\n' "$PYTHON_VERSION"

# Step 2: install the requirements when the file changed.
printf 'Step 2: check the requirements.\n'

if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
    printf 'pip is missing in %s. Installing it.\n' "$VENV_DIR"
    if ! "$VENV_PY" -m ensurepip --upgrade >/dev/null 2>&1; then
        printf 'Error: cannot install pip in %s.\n' "$VENV_DIR" >&2
        exit 1
    fi
fi

if command -v sha256sum >/dev/null 2>&1; then
    REQUIREMENTS_HASH="$(sha256sum "$REQUIREMENTS" | cut -d ' ' -f 1)"
else
    REQUIREMENTS_HASH="$(shasum -a 256 "$REQUIREMENTS" | cut -d ' ' -f 1)"
fi

if [ -f "$STAMP" ] && [ "$(cat "$STAMP")" = "$REQUIREMENTS_HASH" ]; then
    printf 'The requirements are current. No install needed.\n'
else
    printf 'Installing the requirements. This can take a few minutes.\n'
    if ! "$VENV_PY" -m pip install --quiet --disable-pip-version-check -r "$REQUIREMENTS"; then
        printf 'Error: the install failed.\n' >&2
        exit 1
    fi
    printf '%s\n' "$REQUIREMENTS_HASH" > "$STAMP"
fi

# Step 3: build the report.
printf 'Step 3: build the report.\n'

mkdir -p output
RUN_STAMP="$(date +%Y-%m-%d_%H-%M-%S)"
OUTPUT="output/tanita_report_${RUN_STAMP}.pdf"

"$VENV_PY" tanita_report.py "$INPUT_PATH" -o "$OUTPUT" "$@"

printf '\nDone. The report is in %s\n' "$OUTPUT"
