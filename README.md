# F5 Support Case Creation & QKView Automation Toolset (`qkviewmgr`)

[![Security & Supply Chain](https://github.com/SalesAmerSP/f5_support_case_creation_api_tools/actions/workflows/security-audit.yml/badge.svg)](https://github.com/SalesAmerSP/f5_support_case_creation_api_tools/actions/workflows/security-audit.yml)
[![CodeQL Analysis](https://github.com/SalesAmerSP/f5_support_case_creation_api_tools/actions/workflows/codeql.yml/badge.svg)](https://github.com/SalesAmerSP/f5_support_case_creation_api_tools/actions/workflows/codeql.yml)
[![Secret & Credential Leak Scan](https://github.com/SalesAmerSP/f5_support_case_creation_api_tools/actions/workflows/secret-scan.yml/badge.svg)](https://github.com/SalesAmerSP/f5_support_case_creation_api_tools/actions/workflows/secret-scan.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![OCI Container Image](https://img.shields.io/badge/container-ghcr.io-blue.svg)](docs/container.md)

Generates proactive and reactive support cases using MyF5 and iHealth; includes automated BIG-IP QKView generation, chunked retrieval, remote disk purge, TLS 1.3 iHealth upload, native desktop GUI, interactive terminal wizard, and hardened multi-architecture OCI container images.

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

Compatible with **Python 3.10 through 3.14**, as well as pre-built **Docker & Podman multi-arch container images** requiring **zero** local runtime dependencies.

---

## Documentation Index

Detailed guides are organized by topic in the [`docs/`](docs/) directory:

| Topic | Guide | Key Contents |
| :--- | :--- | :--- |
| **Quick Start & Setup** | [Getting Started Guide](docs/getting_started.md) | Virtual environment setup, package installation, lockfile installation, and test suite. |
| **Credentials & Auth** | [Credentials & Secret Management](docs/credentials.md) | Zero-secret CLI rules, interactive masked prompts, environment variables, and `~/.ihealth_credentials`. |
| **CLI Reference** | [Primary CLI Orchestrator (`qkviewmgr`)](docs/cli.md) | `run` (Auto-Pilot), `doctor`, and modular `bigip`, `ihealth`, and `case` subcommands. |
| **Graphical & Wizard UIs** | [GUI & Terminal Wizard Guide](docs/gui_and_wizard.md) | Native desktop GUI (strictly NO web services) and interactive terminal wizard. |
| **Container Deployment** | [Container Deployment Guide (Docker / Podman)](docs/container.md) | Multi-arch OCI image, GHCR registry, volume mounting, and unprivileged non-root security. |
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

*Or run with **zero** local Python dependencies via Docker / Podman:*
```bash
docker pull ghcr.io/salesamersp/f5_support_case_creation_api_tools:latest
docker run --rm -it -v $(pwd):/data ghcr.io/salesamersp/f5_support_case_creation_api_tools:latest doctor
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
│   ├── container.md          # Docker & Podman containerized deployment
│   ├── security_and_ghas.md  # GitHub Advanced Security & supply chain
│   └── network_and_firewall.md # F5 K15202/K000162308 network egress
├── examples/                 # Standalone developer scripts for custom workflows
│   ├── README.md             # Developer integration guide & index
│   ├── bigip_*.py            # Standalone BIG-IP utilities
│   ├── ihealth_*.py          # Standalone iHealth utilities
│   └── myf5_*.py             # Standalone MyF5 case utilities
├── tests/                    # Comprehensive unit & integration tests (96/96 passing)
│   ├── test_f5functions.py   # Core API functions and credential resolution
│   ├── test_qkviewmgr.py     # CLI dispatcher and command handlers
│   ├── test_cli.py           # CLI argument parsing and flags
│   ├── test_gui.py           # Headless GUI tests and signal handling
│   ├── test_wizard.py        # Terminal wizard interaction tests
│   └── test_live_integration.py # Live TMOS appliance integration tests
├── .github/                  # CI/CD, GHAS CodeQL, Dependabot, Container workflows
│   └── workflows/
│       ├── test.yml          # Automated pytest matrix across Python 3.10-3.13 & OS
│       ├── container.yml     # Multi-arch Docker build & push to GHCR
│       ├── codeql.yml        # CodeQL static analysis
│       ├── security-audit.yml# Hash-pinned verification & pip-audit
│       ├── secret-scan.yml   # Gitleaks secret detection
│       └── dependency-review.yml # PR dependency review
├── Dockerfile                # Hardened unprivileged multi-arch container spec
├── .dockerignore             # Container build exclusion list
├── .env.example              # Example environment configuration template
├── requirements.lock         # Cryptographically hash-pinned dependencies
├── requirements.txt          # Root dependency pointer
└── pyproject.toml            # Project packaging & pytest configuration
```

---

## Individual Developer Scripts

All 14 individual standalone scripts are maintained under [`examples/`](examples/README.md) for custom integrations:

- **BIG-IP Appliance Tools**: [`bigip_connectivity_test.py`](examples/bigip_connectivity_test.py), [`bigip_generate_qkview.py`](examples/bigip_generate_qkview.py), [`bigip_list_qkviews.py`](examples/bigip_list_qkviews.py), [`bigip_download_qkview.py`](examples/bigip_download_qkview.py), [`bigip_delete_qkview.py`](examples/bigip_delete_qkview.py).
- **iHealth Tools**: [`ihealth_connectivity_test.py`](examples/ihealth_connectivity_test.py), [`ihealth_list_qkviews.py`](examples/ihealth_list_qkviews.py), [`ihealth_upload_qkview.py`](examples/ihealth_upload_qkview.py).
- **MyF5 Support Case Tools**: [`myf5_connectivity_test.py`](examples/myf5_connectivity_test.py), [`myf5_retrieve_case_creation_metadata.py`](examples/myf5_retrieve_case_creation_metadata.py), [`myf5_create_inputs_file.py`](examples/myf5_create_inputs_file.py), [`myf5_create_new_case.py`](examples/myf5_create_new_case.py), [`myf5_list_existing_cases.py`](examples/myf5_list_existing_cases.py), [`myf5_add_comments_to_existing_case.py`](examples/myf5_add_comments_to_existing_case.py).

See [`examples/README.md`](examples/README.md) for full descriptions and usage patterns.

---

## Running Automated Tests

Run the full automated test suite (96 tests passing across Python 3.10 through 3.14):

### Inside the Execution Container:
```bash
# Run full pytest suite inside the container
podman exec -w /home/appuser/f5_support_case_creation_api_tools tmos-cert-lab pytest tests/ -v

# Run system doctor pre-flight audit inside the container
podman exec -w /home/appuser/f5_support_case_creation_api_tools tmos-cert-lab qkviewmgr doctor
```

### On Local Host / Virtual Environment:
```bash
# Run with pytest
pytest tests/ -v

# Or run with standard unittest discovery
python3 -m unittest discover -s tests -v
```

---

## Support Disclaimer

> [!CAUTION]
> This is a community automation toolset and is **not** an official F5 product. Support is not provided by F5 Technical Support. Usage is at your own risk. Please report bugs or submit enhancements via [GitHub Issues](https://github.com/SalesAmerSP/f5_support_case_creation_api_tools/issues).