#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
    pwd -P
)"

REPO_ROOT="$(
    cd -- "${SCRIPT_DIR}/.."
    pwd -P
)"

TARGET_INPUT="${1:-${REPO_ROOT}/insar_timeseries_viewer}"


fail() {
    printf '\nERRO: %s\n' "$1" >&2
    exit 1
}


for command_name in python3 bandit detect-secrets flake8; do
    if ! command -v "${command_name}" >/dev/null 2>&1; then
        fail "comando obrigatório não encontrado: ${command_name}. Instale as dependências com: python3 -m pip install -e '.[dev]'"
    fi
done


if [[ ! -d "${TARGET_INPUT}" ]]; then
    fail "diretório para análise não encontrado: ${TARGET_INPUT}"
fi


TARGET_DIR="$(
    cd -- "${TARGET_INPUT}"
    pwd -P
)"

SECRETS_REPORT="$(mktemp)"

cleanup() {
    rm -f "${SECRETS_REPORT}"
}

trap cleanup EXIT


printf '\n============================================\n'
printf 'Security and quality checks\n'
printf '============================================\n'
printf 'Diretório: %s\n' "${TARGET_DIR}"


printf '\n[1/3] Executando Bandit...\n'
bandit -r "${TARGET_DIR}"


printf '\n[2/3] Executando detect-secrets...\n'
detect-secrets scan "${TARGET_DIR}" --all-files > "${SECRETS_REPORT}"

python3 - "${SECRETS_REPORT}" <<'PY'
import json
import sys
from pathlib import Path


report_path = Path(sys.argv[1])

try:
    report = json.loads(report_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(
        f"ERRO: não foi possível ler o relatório do detect-secrets: {exc}"
    ) from exc

results = report.get("results", {})
finding_count = sum(len(findings) for findings in results.values())

if finding_count:
    print(
        f"ERRO: detect-secrets encontrou {finding_count} ocorrência(s).",
        file=sys.stderr,
    )

    for filename, findings in sorted(results.items()):
        for finding in findings:
            finding_type = finding.get("type", "tipo desconhecido")
            line_number = finding.get("line_number", "?")
            print(
                f"- {filename}:{line_number}: {finding_type}",
                file=sys.stderr,
            )

    raise SystemExit(1)

print("detect-secrets: nenhuma ocorrência encontrada.")
PY


printf '\n[3/3] Executando Flake8 compatível com o scanner QGIS...\n'
flake8 \
    --extend-ignore=E501 \
    --extend-select=W503 \
    "${TARGET_DIR}"


printf '\nTodos os scans passaram.\n'
