# F5 Support Case Creation & QKView Automation Toolset (`qkviewmgr`)

Generates proactive and reactive support cases using MyF5 and iHealth; includes automated BIG-IP QKView generation, chunked retrieval, remote disk purge, TLS 1.3 iHealth upload, native desktop GUI, interactive terminal wizard, and standalone binary distribution.

---

## Table of Contents

- [Overview & Architecture](#overview--architecture)
- [Zero-Secret Credential Security](#zero-secret-credential-security)
- [Primary Orchestrator: `qkviewmgr`](#primary-orchestrator-qkviewmgr)
  - [1. One-Touch Auto-Pilot (`qkviewmgr run`)](#1-one-touch-auto-pilot-qkviewmgr-run)
  - [2. System Doctor Pre-flight Check (`qkviewmgr doctor`)](#2-system-doctor-pre-flight-check-qkviewmgr-doctor)
  - [3. Native Desktop GUI (`qkviewmgr gui`)](#3-native-desktop-gui-qkviewmgr-gui)
  - [4. Interactive Terminal Wizard (`qkviewmgr wizard`)](#4-interactive-terminal-wizard-qkviewmgr-wizard)
  - [5. Modular Subcommands (`bigip`, `ihealth`, `case`)](#5-modular-subcommands-bigip-ihealth-case)
- [Standalone Binary Packaging (PyInstaller)](#standalone-binary-packaging-pyinstaller)
- [Individual Developer Scripts Reference](#individual-developer-scripts-reference)
  - [BIG-IP Tools](#big-ip-tools)
  - [iHealth Tools](#ihealth-tools)
  - [MyF5 Tools](#myf5-tools)
- [Installation & Quick Start](#installation--quick-start)
- [Security & Supply Chain Posture (GHAS)](#security--supply-chain-posture-ghas)
- [Firewall & Egress Guidelines (K15202 & K000162308)](#firewall--egress-guidelines-k15202--k000162308)
- [Running Automated Tests](#running-automated-tests)
- [Support Disclaimer](#support-disclaimer)

---

## Overview & Architecture

This toolset automates the complete lifecycle of opening F5 support cases and managing QKView diagnostics:

```
+---------------------------------------------------------------------------------------+
|                                    qkviewmgr CLI                                      |
|                                                                                       |
|   +-------------------+  +--------------------+  +----------------+  +------------+   |
|   |  run / auto-pilot |  | native desktop gui |  | terminal wizard|  |   doctor   |   |
|   +-------------------+  +--------------------+  +----------------+  +------------+   |
+-------------------------------------------+-------------------------------------------+
                                            |
                    +-----------------------+-----------------------+
                    |                                               |
         [BIG-IP Appliance]                                [F5 Cloud APIs]
        (iControl REST API)                       (Auth0 IDP / MyF5 / iHealth)
      - Connectivity test                      - TLS 1.3 Streaming QKView Upload
      - Non-truncating QKView (-s0)            - Support Case Creation & Commenting
      - Chunked download with progress         - Diagnostic Analysis Polling
      - Remote disk purge
```

Compatible with **Python 3.10, 3.11, 3.12, 3.13, and 3.14**, as well as pre-compiled standalone executables requiring **zero** runtime dependencies.

---

## Zero-Secret Credential Security

Passing passwords or API keys as command-line arguments is insecure because secrets appear in plain text in process listings (`ps aux`), process audit logs, and shell history (`.bash_history`, `.zsh_history`).

`qkviewmgr` and all 14 standalone scripts support **Zero-Secret CLI Operations**:

### 1. Interactive Masked Prompts
If no secret is provided, the CLI will safely prompt for passwords using masked inputs (`getpass`):
```bash
qkviewmgr bigip test --host 18.210.113.51 --username admin
# Prompts: Password for admin@18.210.113.51: [hidden]
```

### 2. Environment Variables
You can configure credentials via standard environment variables:
```bash
export BIGIP_PASSWORD="YourAppliancePassword"
export F5_CLIENT_ID="YourF5SupportAPIClientID"
export F5_CLIENT_SECRET="YourF5SupportAPIClientSecret"
```

### 3. Credential Profile File (`~/.ihealth_credentials`)
Store API credentials in `~/.ihealth_credentials` (mode `0600`):
```ini
[default]
clientid = JyLTjnHsBhGhm8eykbyJUmTcVy4fllbU
clientsecret = O2QL0nVXodOo9lQTkXjUWNW-zq6Wa-uULjTHAacCqwAJFQGtc2Zwq_3JOlASKC8Z
```

> [!IMPORTANT]
> If a user passes `--password`, `--client-id`, or `--client-secret` via command-line arguments, a security warning is logged to remind them of process table leakage risks.

---

## Primary Orchestrator: `qkviewmgr`

`qkviewmgr` is installed as a direct system console command when installing the package (`pip install -e .`), or executed via `python3 python/qkviewmgr.py`.

### 1. One-Touch Auto-Pilot (`qkviewmgr run`)
Executes the complete diagnostic pipeline in a single command:
1. Tests BIG-IP reachability and authentication.
2. Triggers QKView generation on appliance.
3. Downloads the archive locally with a real-time progress bar.
4. Purges the temporary QKView from appliance storage to free disk space.
5. Authenticates to F5 Identity and streams the file to iHealth over TLS 1.3 with a progress meter.
6. Polls iHealth until diagnostic processing completes, returning the iHealth web analysis URL.

```bash
# Basic run (password prompted interactively or read from BIGIP_PASSWORD)
qkviewmgr run --host 18.210.113.51 --no-ssl-verify

# Associate with an existing support ticket and complete full analysis tracking
qkviewmgr run --host 18.210.113.51 --case-number C3456789 --description "Core crash investigation" --no-ssl-verify
```

### 2. System Doctor Pre-flight Check (`qkviewmgr doctor`)
Verifies local Python runtime, OpenSSL version, TLS 1.2/1.3 ciphers, credential store status, and network reachability to all F5 Cloud endpoints:
```bash
qkviewmgr doctor
```

Output:
```
=================================================================
          qkviewmgr System Doctor & Pre-flight Audit
=================================================================

1. Runtime Environment:
   Python Executable: /opt/homebrew/bin/python3
   Python Version   : 3.14.7
   OpenSSL Version  : OpenSSL 3.6.4 25 Aug 2026

2. Credential Configuration:
   ✓ Found ~/.ihealth_credentials
   ℹ F5_CLIENT_ID set in environment
   ℹ BIGIP_PASSWORD set in environment

3. TLS 1.2+ Network Endpoint Reachability:
   ✓ F5 Identity (Legacy) (https://identity.account.f5.com): Reachable (HTTP 200)
   ✓ F5 iHealth API (https://ihealth2-api.f5.com): Reachable (HTTP 401)
   ✓ MyF5 Support API (https://support.apis.f5.com): Reachable (HTTP 404)
=================================================================
   ✓ All pre-flight diagnostic checks passed!
=================================================================
```

### 3. Native Desktop GUI (`qkviewmgr gui`)
Launches a native desktop window using Python's standard `tkinter`/`ttk` libraries.

> [!TIP]
> **Strictly NO Web Services**: The GUI binds zero HTTP/TCP listening ports, starts no background web servers, and requires no web browser. It is fully local, threaded, and secure.

```bash
qkviewmgr gui
```
Features:
- **One-Touch Auto-Pilot Tab**: Fill in BIG-IP credentials, click "Run Auto-Pilot", and watch live streaming activity.
- **BIG-IP Direct Tab**: Test appliance connectivity, generate, and list QKViews on BIG-IP.
- **iHealth & Cases Tab**: List account QKViews and search open support tickets.
- **System Doctor Tab**: Run one-click network and environment diagnostics.

### 4. Interactive Terminal Wizard (`qkviewmgr wizard`)
For SSH jump boxes, headless servers, and terminal users, launch the guided CLI wizard:
```bash
qkviewmgr wizard
```

### 5. Modular Subcommands (`bigip`, `ihealth`, `case`)
```bash
# BIG-IP Appliance Management
qkviewmgr bigip test --host 18.210.113.51 --no-ssl-verify
qkviewmgr bigip list --host 18.210.113.51 --no-ssl-verify
qkviewmgr bigip generate --host 18.210.113.51 --filename prod_diag.qkview --no-truncate --no-ssl-verify
qkviewmgr bigip download --host 18.210.113.51 --filename prod_diag.qkview --output ./prod_diag.qkview --no-ssl-verify
qkviewmgr bigip delete --host 18.210.113.51 --filename prod_diag.qkview --no-ssl-verify

# iHealth Management
qkviewmgr ihealth list
qkviewmgr ihealth show --qkview-id 26894783
qkviewmgr ihealth upload --filename ./prod_diag.qkview --case-number C3456789

# Support Case Management
qkviewmgr case list
qkviewmgr case metadata
qkviewmgr case create --json-file case_inputs.json
qkviewmgr case comment --case-number C3456789 --comment "Uploaded new QKView 26894783."
```

---

## Standalone Binary Packaging (PyInstaller)

Users and operators who do not have Python or necessary libraries installed can run `qkviewmgr` as a single standalone executable.

### Local Binary Compilation
```bash
# Build standalone binary locally
python3 scripts/build_binary.py
```
Compiled output is saved to `dist/qkviewmgr` (or `dist/qkviewmgr.exe` on Windows).

### Multi-Platform Release Matrix & SLSA Attestations
Our GitHub Actions release workflow (`.github/workflows/release.yml`) compiles cross-platform binaries on every release tag (`v*`):
- `qkviewmgr-macos-arm64` (Apple Silicon macOS)
- `qkviewmgr-linux-x86_64` (Standard 64-bit Linux)
- `qkviewmgr-windows-x64.exe` (Windows 64-bit)
- Software Bill of Materials (SBOM) in SPDX format
- **SLSA Level 3 Build Provenance Attestations** signed cryptographically by GitHub.

---

## Individual Developer Scripts Reference

All 14 individual standalone scripts are retained under `python/` for custom integrations, automation scripts, and workflows. All scripts inherit zero-secret credential resolution:

### BIG-IP Tools
- **`bigip_connectivity_test.py`**: Validate iControl REST reachability against `/mgmt/tm/sys/ready`.
- **`bigip_generate_qkview.py`**: Trigger QKView generation on target BIG-IP (supports `-s0` non-truncate).
- **`bigip_list_qkviews.py`**: List all completed QKView archives on the BIG-IP device.
- **`bigip_download_qkview.py`**: Download remote QKView with live chunked progress meter.
- **`bigip_delete_qkview.py`**: Free appliance disk space by deleting remote QKView.

### iHealth Tools
- **`ihealth_connectivity_test.py`**: Authenticate and validate access to iHealth analyzer API.
- **`ihealth_list_qkviews.py`**: Fetch diagnostic summaries, processing status, and URLs for all uploaded QKViews.
- **`ihealth_upload_qkview.py`**: Upload local QKView file to iHealth with real-time transfer progress meter.

### MyF5 Tools
- **`myf5_connectivity_test.py`**: Validate authentication credentials against F5 Identity Services.
- **`myf5_retrieve_case_creation_metadata.py`**: Retrieve valid product families, severities, and schemas.
- **`myf5_create_inputs_file.py`**: Interactive wizard generating valid case JSON payload files.
- **`myf5_create_new_case.py`**: Submit case payload to MyF5 and retrieve created case number.
- **`myf5_list_existing_cases.py`**: List active or closed support cases.
- **`myf5_add_comments_to_existing_case.py`**: Append notes or updates to an open support case.

---

## Installation & Quick Start

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/SalesAmerSP/f5_support_case_creation_api_tools.git
cd f5_support_case_creation_api_tools
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
# Standard install:
pip install -e .

# Or strict hash-pinned production install:
pip install --require-hashes --no-deps -r requirements.lock
```

---

## Security & Supply Chain Posture (GHAS)

This repository implements enterprise-grade GitHub Advanced Security (GHAS) controls:

1. **Semantic CodeQL Analysis (`.github/workflows/codeql.yml`)**: Continuous Abstract Syntax Tree (AST) scanning with `security-extended` and `security-and-quality` rules.
2. **Cryptographic Lockfile Pinning (`requirements.lock`)**: All production dependencies pinned with multi-architecture SHA-256 hashes against supply chain tampering.
3. **Automated Vulnerability Audits (`.github/workflows/security-audit.yml`)**: Continuous scanning with `pip-audit` exporting SARIF alerts to GitHub Code Scanning.
4. **Secret Leak Prevention (`.github/workflows/secret-scan.yml` & `.gitleaks.toml`)**: Automated secret scanning preventing accidental token or password commits.
5. **PR Dependency Review (`.github/workflows/dependency-review.yml`)**: Automatic blocking of pull requests introducing vulnerable or non-compliant dependencies.
6. **Automated Dependabot Security Updates (`.github/dependabot.yml`)**: Weekly automated dependency bump PRs.

---

## Firewall & Egress Guidelines (K15202 & K000162308)

Per **F5 Article K15202** (*IP addresses for F5 hosted services*) and **K000162308** (*F5 Identity Platform Migration: Okta to Auth0*):

- **F5 Identity Service (Auth0)**: `idp.identity.f5.com`
- **F5 Identity Service (Legacy Okta)**: `identity.account.f5.com`
- **Case Management API**: `support.apis.f5.com` (`35.199.173.84`)
- **iHealth Upload API**: `ihealth2-api.f5.com` and `ihealth-api.f5.com` (`185.56.152.6`)

---

## Running Automated Tests

Run the complete 44-test unit test suite:
```bash
python3 -m unittest discover -s tests -v
```

---

## Support Disclaimer

> [!CAUTION]
> This is a community automation toolset and is **not** an official F5 product. Support is not provided by F5 Technical Support. Usage is at your own risk. Please report bugs or submit enhancements via [GitHub Issues](https://github.com/SalesAmerSP/f5_support_case_creation_api_tools/issues).