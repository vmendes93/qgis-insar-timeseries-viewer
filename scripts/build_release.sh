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

PLUGIN_NAME="insar_timeseries_viewer"
PLUGIN_DIR="${REPO_ROOT}/${PLUGIN_NAME}"
METADATA_FILE="${PLUGIN_DIR}/metadata.txt"
DIST_DIR="${REPO_ROOT}/dist"

DEFAULT_OUTPUT_DIR="$(dirname "${REPO_ROOT}")"
OUTPUT_DIR_INPUT="${1:-${DEFAULT_OUTPUT_DIR}}"


fail() {
    printf '\nERRO: %s\n' "$1" >&2
    exit 1
}


for command_name in python3 sha256sum cp; do
    if ! command -v "${command_name}" >/dev/null 2>&1; then
        fail "comando obrigatório não encontrado: ${command_name}"
    fi
done


if [[ ! -f "${METADATA_FILE}" ]]; then
    fail "metadata.txt não encontrado: ${METADATA_FILE}"
fi


mkdir -p "${OUTPUT_DIR_INPUT}"

OUTPUT_DIR="$(
    cd -- "${OUTPUT_DIR_INPUT}"
    pwd -P
)"


VERSION="$(
    python3 - "${METADATA_FILE}" <<'PY'
import configparser
import sys
from pathlib import Path


metadata_path = Path(sys.argv[1])

parser = configparser.ConfigParser(interpolation=None)
parser.optionxform = str
parser.read(metadata_path, encoding="utf-8")

if "general" not in parser:
    raise SystemExit(
        f"Seção [general] não encontrada em {metadata_path}"
    )

version = parser["general"].get("version", "").strip()

if not version:
    raise SystemExit(
        f"Versão não encontrada em {metadata_path}"
    )

print(version)
PY
)"


ARCHIVE_NAME="${PLUGIN_NAME}-${VERSION}.zip"
CHECKSUM_NAME="${ARCHIVE_NAME}.sha256"

ARCHIVE_PATH="${DIST_DIR}/${ARCHIVE_NAME}"
CHECKSUM_PATH="${DIST_DIR}/${CHECKSUM_NAME}"

FINAL_ARCHIVE="${OUTPUT_DIR}/${ARCHIVE_NAME}"
FINAL_CHECKSUM="${OUTPUT_DIR}/${CHECKSUM_NAME}"


printf '\n'
printf '============================================\n'
printf 'InSAR Time Series Viewer %s\n' "${VERSION}"
printf '============================================\n'


cd "${REPO_ROOT}"


printf '\n[1/6] Validando a estrutura da release...\n'
python3 scripts/validate_release.py


printf '\n[2/6] Removendo pacotes anteriores da versão...\n'
rm -f "${ARCHIVE_PATH}"
rm -f "${CHECKSUM_PATH}"


printf '\n[3/6] Criando o ZIP instalável...\n'
python3 scripts/package_plugin.py


if [[ ! -f "${ARCHIVE_PATH}" ]]; then
    fail "ZIP não foi criado: ${ARCHIVE_PATH}"
fi

if [[ ! -f "${CHECKSUM_PATH}" ]]; then
    fail "checksum não foi criado: ${CHECKSUM_PATH}"
fi


printf '\n[4/6] Verificando o checksum em dist/...\n'

(
    cd "${DIST_DIR}"
    sha256sum -c "${CHECKSUM_NAME}"
)


printf '\n[5/6] Verificando a estrutura interna do ZIP...\n'

python3 - "${ARCHIVE_PATH}" "${VERSION}" <<'PY'
import configparser
import sys
from pathlib import Path
from zipfile import BadZipFile, ZipFile


archive_path = Path(sys.argv[1])
expected_version = sys.argv[2]
plugin_name = "insar_timeseries_viewer"
prefix = f"{plugin_name}/"

required_files = {
    f"{prefix}__init__.py",
    f"{prefix}metadata.txt",
    f"{prefix}LICENSE",
    f"{prefix}README.md",
    f"{prefix}icon.png",
    f"{prefix}index.html",
}

try:
    with ZipFile(archive_path) as archive:
        names = archive.namelist()

        if not names:
            raise SystemExit("ERRO: o ZIP está vazio.")

        invalid_root_files = [
            name
            for name in names
            if not name.startswith(prefix)
        ]

        if invalid_root_files:
            raise SystemExit(
                "ERRO: arquivos fora da pasta principal:\n"
                + "\n".join(invalid_root_files[:20])
            )

        generated_files = [
            name
            for name in names
            if "__pycache__" in name
            or name.endswith((".pyc", ".pyo"))
        ]

        if generated_files:
            raise SystemExit(
                "ERRO: arquivos Python gerados dentro do ZIP:\n"
                + "\n".join(generated_files[:20])
            )

        missing_files = sorted(
            required_files.difference(names)
        )

        if missing_files:
            raise SystemExit(
                "ERRO: arquivos obrigatórios ausentes:\n"
                + "\n".join(missing_files)
            )

        metadata_text = archive.read(
            f"{prefix}metadata.txt"
        ).decode("utf-8")

except BadZipFile as exc:
    raise SystemExit(
        f"ERRO: arquivo ZIP inválido: {exc}"
    ) from exc


parser = configparser.ConfigParser(interpolation=None)
parser.optionxform = str
parser.read_string(metadata_text)

zip_version = parser["general"].get("version", "").strip()

if zip_version != expected_version:
    raise SystemExit(
        "ERRO: versão interna do ZIP não corresponde: "
        f"{zip_version!r} != {expected_version!r}"
    )

print(f"Arquivos no ZIP: {len(names)}")
print(f"Versão interna: {zip_version}")
print("Estrutura interna: OK")
PY


printf '\n[6/6] Copiando o pacote para o destino final...\n'

cp -f "${ARCHIVE_PATH}" "${FINAL_ARCHIVE}"
cp -f "${CHECKSUM_PATH}" "${FINAL_CHECKSUM}"

(
    cd "${OUTPUT_DIR}"
    sha256sum -c "${CHECKSUM_NAME}"
)


printf '\n'
printf 'Pacote preparado com sucesso.\n'
printf '\n'
printf 'ZIP:\n%s\n' "${FINAL_ARCHIVE}"
printf '\n'
printf 'Checksum:\n%s\n' "${FINAL_CHECKSUM}"
printf '\n'
