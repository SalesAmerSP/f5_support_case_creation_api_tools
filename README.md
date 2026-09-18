# F5 Support Case Creation & QKView Automation Toolset (`qkviewmgr`)

[![Security & Supply Chain](https://github.com/SalesAmerSP/f5_support_case_creation_api_tools/actions/workflows/security-audit.yml/badge.svg)](https://github.com/SalesAmerSP/f5_support_case_creation_api_tools/actions/workflows/security-audit.yml)
[![CodeQL Analysis](https://github.com/SalesAmerSP/f5_support_case_creation_api_tools/actions/workflows/codeql.yml/badge.svg)](https://github.com/SalesAmerSP/f5_support_case_creation_api_tools/actions/workflows/codeql.yml)
[![Secret & Credential Leak Scan](https://github.com/SalesAmerSP/f5_support_case_creation_api_tools/actions/workflows/secret-scan.yml/badge.svg)](https://github.com/SalesAmerSP/f5_support_case_creation_api_tools/actions/workflows/secret-scan.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Standalone Binary](https://img.shields.io/badge/packaging-PyInstaller%20Standalone-orange.svg)](docs/binary_packaging.md)

Generates proactive and reactive support cases using MyF5 and iHealth; includes automated BIG-IP QKView generation, chunked retrieval, remote disk purge, TLS 1.3 iHealth upload, native desktop GUI, interactive terminal wizard, and standalone binary distribution.

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

Compatible with **Python 3.10 through 3.14**, as well as pre-compiled standalone executables requiring **zero** runtime dependencies.

---

## Documentation Index

Detailed guides are organized by topic in the [`docs/`](docs/) directory:

| Topic | Guide | Key Contents |
| :--- | :--- | :--- |
| **Quick Start & Setup** | [Getting Started Guide](docs/getting_started.md) | Virtual environment setup, package installation, lockfile installation, and test suite. |
| **Credentials & Auth** | [Credentials & Secret Management](docs/credentials.md) | Zero-secret CLI rules, interactive masked prompts, environment variables, and `~/.ihealth_credentials`. |
| **CLI Reference** | [Primary CLI Orchestrator (`qkviewmgr`)](docs/cli.md) | `run` (Auto-Pilot), `doctor`, and modular `bigip`, `ihealth`, and `case` subcommands. |
| **Graphical & Wizard UIs** | [GUI & Terminal Wizard Guide](docs/gui_and_wizard.md) | Native desktop GUI (strictly NO web services) and interactive terminal wizard. |
| **Standalone Packaging** | [Standalone Binary Packaging](docs/binary_packaging.md) | PyInstaller compilation, cross-platform release matrix, SBOM, and SLSA Level 3 attestations. |
| **Security & Supply Chain** | [Security & Supply Chain Posture](docs/security_and_ghas.md) | GitHub Advanced Security (GHAS), CodeQL AST analysis, hash pinning, pip-audit, and secret scanning. |
| **Network & Firewall** | [Network Egress & Firewall Guidelines](docs/network_and_firewall.md) | F5 Articles K15202 & K000162308, port 443 egress rules, TLS 1.2+ configuration, and ciphers. |
| **Developer Scripts** | [Individual Developer Scripts Reference](examples/README.md) | 14 standalone modular scripts under `examples/` for custom integrations and workflows. |

---

## 30-Second Quick Start

### 1. Installation

```bash
git clone https://github.com/SalesAmerSP/f5_support_case_creation_api_tools.git
cd f5_support_case_creation_api_tools
pip install -e .
```

### 2. Configure Credentials

Export environment variables or let the tool prompt you interactively:
```bash
export BIGIP_USERNAME="admin"
export BIGIP_PASSWORD="YourAppliancePassword"
export F5_CLIENT_ID="YourF5SupportAPIClientID"
export F5_CLIENT_SECRET="YourF5SupportAPIClientSecret"
```

### 3. Run Pre-flight Audit

```bash
qkviewmgr doctor
```

### 4. Execute One-Touch Auto-Pilot

```bash
qkviewmgr run --host 192.0.2.1 --no-ssl-verify
```

---

## Clean Repository Structure

```
f5_support_case_creation_api_tools/
├── src/qkviewmgr/            # Canonical PEP 517/621 Python package & core engine
│   ├── __init__.py           # Package exports
│   ├── __main__.py           # Executable entrypoint (`python -m qkviewmgr`)
│   ├── qkviewmgr.py          # Unified CLI dispatcher & Auto-Pilot orchestrator
│   ├── f5functions.py        # Core iControl REST, iHealth, & MyF5 client
│   ├── gui.py                # Native desktop GUI (strictly NO web services)
│   └── wizard.py             # Interactive terminal wizard
├── docs/                     # Modular documentation guides by topic
│   ├── getting_started.md    # Installation & quick start
│   ├── credentials.md        # Credential handling & zero-secret security
│   ├── cli.md                # Full CLI command and options reference
│   ├── gui_and_wizard.md     # Desktop GUI and terminal wizard
│   ├── binary_packaging.md   # Standalone executable compilation
│   ├── security_and_ghas.md  # GitHub Advanced Security & supply chain
│   └── network_and_firewall.md # F5 K15202/K000162308 network egress
├── examples/                 # Standalone developer scripts for custom workflows
│   ├── README.md             # Developer integration guide & index
│   ├── bigip_*.py            # Standalone BIG-IP utilities
│   ├── ihealth_*.py          # Standalone iHealth utilities
│   └── myf5_*.py             # Standalone MyF5 case utilities
├── python/                   # Backward-compatibility shims for legacy invocations
├── scripts/                  # Build & packaging automation (PyInstaller)
├── tests/                    # Comprehensive unit tests (48/48 passing)
├── .github/                  # CI/CD, GHAS CodeQL, Dependabot, Releases
├── qkviewmgr.spec            # Standalone binary compilation spec
├── requirements.lock         # Cryptographically hash-pinned dependencies
├── requirements.txt          # Root dependency pointer
└── pyproject.toml            # Project packaging specification
```

---

## Individual Developer Scripts

All 14 individual standalone scripts are maintained under [`examples/`](examples/README.md) (with backward-compatibility shims under `python/`) for custom integrations:

- **BIG-IP Appliance Tools**: [`bigip_connectivity_test.py`](examples/bigip_connectivity_test.py), [`bigip_generate_qkview.py`](examples/bigip_generate_qkview.py), [`bigip_list_qkviews.py`](examples/bigip_list_qkviews.py), [`bigip_download_qkview.py`](examples/bigip_download_qkview.py), [`bigip_delete_qkview.py`](examples/bigip_delete_qkview.py).
- **iHealth Tools**: [`ihealth_connectivity_test.py`](examples/ihealth_connectivity_test.py), [`ihealth_list_qkviews.py`](examples/ihealth_list_qkviews.py), [`ihealth_upload_qkview.py`](examples/ihealth_upload_qkview.py).
- **MyF5 Support Case Tools**: [`myf5_connectivity_test.py`](examples/myf5_connectivity_test.py), [`myf5_retrieve_case_creation_metadata.py`](examples/myf5_retrieve_case_creation_metadata.py), [`myf5_create_inputs_file.py`](examples/myf5_create_inputs_file.py), [`myf5_create_new_case.py`](examples/myf5_create_new_case.py), [`myf5_list_existing_cases.py`](examples/myf5_list_existing_cases.py), [`myf5_add_comments_to_existing_case.py`](examples/myf5_add_comments_to_existing_case.py).

See [`examples/README.md`](examples/README.md) for full descriptions and usage patterns.

---

## Running Automated Tests

Run the full unit test suite:
```bash
python3 -m unittest discover -s tests -v
```

---

## Support Disclaimer

> [!CAUTION]
> This is a community automation toolset and is **not** an official F5 product. Support is not provided by F5 Technical Support. Usage is at your own risk. Please report bugs or submit enhancements via [GitHub Issues](https://github.com/SalesAmerSP/f5_support_case_creation_api_tools/issues).