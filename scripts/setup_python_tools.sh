#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

AI_SETUP_SCRIPT="tools/setup_ai_news_env.py"
SECURITY_SETUP_SCRIPT="tools/setup_security_audit_env.py"

AI_DEFAULT_VENV=".venv-ai-news"
SECURITY_DEFAULT_VENV=".venv-security-audit"
DEFAULT_SHIMS_DIR=".tools-bin"

VERIFY_ONLY=0
SKIP_AI_NEWS=0
SKIP_SECURITY_AUDIT=0
INSTALL_SHIMS=1

AI_VENV_PATH="${AI_DEFAULT_VENV}"
SECURITY_VENV_PATH="${SECURITY_DEFAULT_VENV}"
SHIMS_DIR="${DEFAULT_SHIMS_DIR}"

use_color=1
if [[ ! -t 1 ]]; then
  use_color=0
fi

color_reset=""
color_info=""
color_warn=""
color_error=""
color_success=""

setup_colors() {
  if [[ "${use_color}" -eq 1 ]]; then
    color_reset="\033[0m"
    color_info="\033[1;34m"
    color_warn="\033[1;33m"
    color_error="\033[1;31m"
    color_success="\033[1;32m"
  fi
}

log_info() {
  printf "%b[INFO]%b %s\n" "${color_info}" "${color_reset}" "$*"
}

log_warn() {
  printf "%b[WARN]%b %s\n" "${color_warn}" "${color_reset}" "$*"
}

log_error() {
  printf "%b[ERROR]%b %s\n" "${color_error}" "${color_reset}" "$*" >&2
}

log_success() {
  printf "%b[OK]%b %s\n" "${color_success}" "${color_reset}" "$*"
}

usage() {
  cat <<'USAGE'
Usage: bash scripts/setup_python_tools.sh [options]

Sets up Python virtual environments used by repository tooling and verifies
primary tool entry points are invokable.

Options:
  --verify-only                Verify existing environments and tools only.
  --skip-ai-news               Skip AI news environment setup/verification.
  --skip-security-audit        Skip security audit environment setup/verification.
  --venv-ai-news PATH          Override AI news virtualenv path.
  --venv-security-audit PATH   Override security audit virtualenv path.
  --shims-dir PATH             Directory where local command shims are created.
  --no-install-shims           Do not create local shim commands.
  --no-color                   Disable colorized output.
  -h, --help                   Show this help text.

Examples:
  bash scripts/setup_python_tools.sh
  bash scripts/setup_python_tools.sh --verify-only
  bash scripts/setup_python_tools.sh --venv-ai-news .venv-news --shims-dir .local-tools/bin
USAGE
}

require_command() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    log_error "Required command not found: ${cmd}"
    return 1
  fi
}

abs_path() {
  local maybe_relative="$1"
  if [[ "${maybe_relative}" = /* ]]; then
    printf "%s\n" "${maybe_relative}"
    return 0
  fi
  printf "%s/%s\n" "${REPO_ROOT}" "${maybe_relative}"
}

venv_python_path() {
  local venv_path="$1"
  local unix_python="${venv_path}/bin/python"
  local win_python="${venv_path}/Scripts/python.exe"
  if [[ -x "${unix_python}" ]]; then
    printf "%s\n" "${unix_python}"
    return 0
  fi
  if [[ -f "${win_python}" ]]; then
    printf "%s\n" "${win_python}"
    return 0
  fi
  return 1
}

run_setup_script() {
  local label="$1"
  local script_rel="$2"
  local venv_path="$3"

  local script_abs
  script_abs="$(abs_path "${script_rel}")"
  if [[ ! -f "${script_abs}" ]]; then
    log_error "Missing setup script for ${label}: ${script_rel}"
    return 1
  fi

  local -a args
  args=(python3 "${script_abs}" --venv "${venv_path}")
  if [[ "${VERIFY_ONLY}" -eq 1 ]]; then
    args+=(--verify-only)
  fi

  log_info "Running ${label} environment script (${script_rel})"
  "${args[@]}"
}

verify_tool_command() {
  local label="$1"
  local python_bin="$2"
  local script_rel="$3"

  local script_abs
  script_abs="$(abs_path "${script_rel}")"
  if [[ ! -f "${script_abs}" ]]; then
    log_error "Cannot verify ${label}; missing script: ${script_rel}"
    return 1
  fi

  if "${python_bin}" "${script_abs}" --help >/dev/null 2>&1; then
    log_success "Verified ${label} is invokable"
    return 0
  fi

  log_error "Failed to invoke ${label}: ${script_rel}"
  return 1
}

write_shim() {
  local shim_name="$1"
  local interpreter_path="$2"
  local script_rel="$3"

  local shim_path="${SHIMS_DIR}/${shim_name}"
  local script_abs
  script_abs="$(abs_path "${script_rel}")"

  cat > "${shim_path}" <<SHIM
#!/usr/bin/env bash
set -euo pipefail
exec "${interpreter_path}" "${script_abs}" "\$@"
SHIM

  chmod +x "${shim_path}"
}

install_base_shims() {
  local python_bin="$1"
  write_shim "tool-find-similar-item-names" "${python_bin}" "tools/find_similar_item_names.py"
  write_shim "tool-generate-db-column-map" "${python_bin}" "tools/generate_db_column_map.py"
}

install_ai_news_shims() {
  local python_bin="$1"
  write_shim "tool-ai-news-retrieve" "${python_bin}" "tools/ai_news_crawler/retrieve_articles.py"
  write_shim "tool-ai-news-summarize" "${python_bin}" "tools/ai_news_crawler/summarize_articles.py"
}

install_security_audit_shims() {
  local python_bin="$1"
  write_shim "tool-map-directory-structure" "${python_bin}" "tools/security_audit/map_directory_structure.py"
  write_shim "tool-map-function-calls" "${python_bin}" "tools/security_audit/map_function_calls.py"
  write_shim "tool-generate-security-audit-report" "${python_bin}" "tools/security_audit/generate_security_audit_report.py"
}

verify_shim_invocation() {
  local shim_name="$1"
  local shim_path="${SHIMS_DIR}/${shim_name}"

  if [[ ! -x "${shim_path}" ]]; then
    log_error "Expected shim was not created: ${shim_path}"
    return 1
  fi

  if "${shim_path}" --help >/dev/null 2>&1; then
    log_success "Verified shim is invokable: ${shim_name}"
    return 0
  fi

  log_error "Shim exists but failed on --help: ${shim_name}"
  return 1
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --verify-only)
        VERIFY_ONLY=1
        ;;
      --skip-ai-news)
        SKIP_AI_NEWS=1
        ;;
      --skip-security-audit)
        SKIP_SECURITY_AUDIT=1
        ;;
      --venv-ai-news)
        if [[ $# -lt 2 ]]; then
          log_error "Missing value for --venv-ai-news"
          exit 2
        fi
        AI_VENV_PATH="$2"
        shift
        ;;
      --venv-security-audit)
        if [[ $# -lt 2 ]]; then
          log_error "Missing value for --venv-security-audit"
          exit 2
        fi
        SECURITY_VENV_PATH="$2"
        shift
        ;;
      --shims-dir)
        if [[ $# -lt 2 ]]; then
          log_error "Missing value for --shims-dir"
          exit 2
        fi
        SHIMS_DIR="$2"
        shift
        ;;
      --no-install-shims)
        INSTALL_SHIMS=0
        ;;
      --no-color)
        use_color=0
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        log_error "Unknown argument: $1"
        usage
        exit 2
        ;;
    esac
    shift
  done
}

main() {
  parse_args "$@"
  setup_colors

  require_command bash
  require_command python3

  cd "${REPO_ROOT}"

  if [[ "${SKIP_AI_NEWS}" -eq 1 && "${SKIP_SECURITY_AUDIT}" -eq 1 ]]; then
    log_error "Both tool environments were skipped; nothing to do."
    return 2
  fi

  local ai_python=""
  local security_python=""

  if [[ "${SKIP_AI_NEWS}" -eq 0 ]]; then
    run_setup_script "AI news" "${AI_SETUP_SCRIPT}" "${AI_VENV_PATH}"
    if ! ai_python="$(venv_python_path "$(abs_path "${AI_VENV_PATH}")")"; then
      log_error "AI news virtualenv is missing a Python executable: ${AI_VENV_PATH}"
      return 1
    fi
    verify_tool_command "AI news retrieve CLI" "${ai_python}" "tools/ai_news_crawler/retrieve_articles.py"
    verify_tool_command "AI news summarize CLI" "${ai_python}" "tools/ai_news_crawler/summarize_articles.py"
  fi

  if [[ "${SKIP_SECURITY_AUDIT}" -eq 0 ]]; then
    run_setup_script "Security audit" "${SECURITY_SETUP_SCRIPT}" "${SECURITY_VENV_PATH}"
    if ! security_python="$(venv_python_path "$(abs_path "${SECURITY_VENV_PATH}")")"; then
      log_error "Security audit virtualenv is missing a Python executable: ${SECURITY_VENV_PATH}"
      return 1
    fi
    verify_tool_command "Security audit directory mapper" "${security_python}" "tools/security_audit/map_directory_structure.py"
    verify_tool_command "Security audit function-call mapper" "${security_python}" "tools/security_audit/map_function_calls.py"
    verify_tool_command "Security audit report generator" "${security_python}" "tools/security_audit/generate_security_audit_report.py"
  fi

  if [[ "${INSTALL_SHIMS}" -eq 1 ]]; then
    mkdir -p "${SHIMS_DIR}"

    if [[ -n "${security_python}" ]]; then
      install_base_shims "${security_python}"
      install_security_audit_shims "${security_python}"
    elif [[ -n "${ai_python}" ]]; then
      install_base_shims "${ai_python}"
    else
      log_warn "No Python interpreter available for base shim generation."
    fi

    if [[ -n "${ai_python}" ]]; then
      install_ai_news_shims "${ai_python}"
    fi

    if [[ -n "${ai_python}" || -n "${security_python}" ]]; then
      log_success "Installed local tool shims in ${SHIMS_DIR}"
      if [[ -n "${security_python}" ]]; then
        verify_shim_invocation "tool-map-directory-structure"
      fi
      if [[ -n "${ai_python}" ]]; then
        verify_shim_invocation "tool-ai-news-retrieve"
      fi
    else
      log_warn "No shims were generated."
    fi
  fi

  log_success "Python tool environment setup complete"
  if [[ "${INSTALL_SHIMS}" -eq 1 ]]; then
    log_info "Add shims to PATH with: export PATH=\"${REPO_ROOT}/${SHIMS_DIR}:\$PATH\""
  fi
  return 0
}

main "$@"
