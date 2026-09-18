# Getting Started

This guide walks you through installing and configuring `qkviewmgr` and verifying your environment.

---

## Prerequisites

- **Operating System**: macOS, Linux, or Windows.
- **Python**: Version 3.10, 3.11, 3.12, 3.13, or 3.14.
- **OpenSSL**: Version 1.1.1 or higher (OpenSSL 3.0+ recommended for TLS 1.3 support).

> [!TIP]
> If you do not have Python installed on your target machine, see the [Container Deployment Guide](container.md) to run the tool via Docker or Podman with zero local dependencies:
> ```bash
> docker run --rm -it -v $(pwd):/data ghcr.io/salesamersp/f5_support_case_creation_api_tools:latest run --help
> ```

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/SalesAmerSP/f5_support_case_creation_api_tools.git
cd f5_support_case_creation_api_tools
```

### 2. Create and Activate a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

*On Windows PowerShell:*
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install the Toolset

#### Standard Development Installation
Installs the package in editable mode along with the `qkviewmgr` console command:
```bash
pip install -e .
```

#### Strict Supply-Chain-Hardened Installation
To protect against dependency tampering or supply chain injection attacks, install using the cryptographically hash-pinned lockfile:
```bash
pip install --require-hashes --no-deps -r requirements.lock
pip install --no-deps -e .
```

---

## 30-Second Quick Start

### 1. Configure Credentials (Zero CLI Plaintext)

Export your credentials as environment variables or let the tool prompt you interactively:
```bash
export BIGIP_USERNAME="admin"
export BIGIP_PASSWORD="YourAppliancePassword"
export F5_CLIENT_ID="YourF5SupportAPIClientID"
export F5_CLIENT_SECRET="YourF5SupportAPIClientSecret"
```

For complete details on secure credential configuration, see the [Credentials & Secret Management Guide](credentials.md).

### 2. Run Pre-flight Diagnostic Check

Verify Python runtime, TLS ciphers, credentials, and network connectivity to all F5 hosted endpoints:
```bash
qkviewmgr doctor
```

### 3. Run One-Touch Auto-Pilot

Generate a fresh QKView from your BIG-IP, download it, delete the temporary file from appliance disk, stream it to iHealth over TLS 1.3, and retrieve the diagnostic analysis link:
```bash
qkviewmgr run --host 192.0.2.1 --no-ssl-verify
```

---

## Running the Automated Test Suite

The repository includes a comprehensive unit test suite with mock integrations for appliance REST APIs, iHealth, and MyF5 services.

Run all tests:
```bash
python3 -m unittest discover -s tests -v
```

All tests execute in isolated environments with mocked network requests and zero external dependencies.
