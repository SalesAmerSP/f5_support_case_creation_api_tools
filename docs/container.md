# Containerized Deployment (Docker / Podman)

`qkviewmgr` is distributed as a multi-architecture OCI container image via the **GitHub Container Registry (GHCR)**.

Containerization eliminates all host-side dependencies—no Python, `pip`, or virtual environments are needed on the operator workstation or jump box. It also runs transparently on macOS (Apple Silicon & Intel), Linux, and Windows without triggering OS-level Gatekeeper, quarantine flags, or binary signing errors.

---

## 1. Quick Start

Run the container directly with Docker or Podman:

### Docker
```bash
# Pull the latest image
docker pull ghcr.io/salesamersp/f5_support_case_creation_api_tools:latest

# Run pre-flight environment diagnostics
docker run --rm ghcr.io/salesamersp/f5_support_case_creation_api_tools:latest doctor

# View CLI help
docker run --rm ghcr.io/salesamersp/f5_support_case_creation_api_tools:latest --help
```

### Podman (Rootless & Daemonless)
```bash
podman run --rm ghcr.io/salesamersp/f5_support_case_creation_api_tools:latest doctor
```

---

## 2. Working with Local Files & Volumes (`/data`)

The container sets `/data` as its internal working directory and working volume. To persist downloaded `.qkview` files or generated `case_input.json` files on your local host, mount your current working directory using `-v $(pwd):/data`:

```bash
docker run --rm -it \
  -v $(pwd):/data \
  -e BIGIP_PASSWORD='your_password' \
  ghcr.io/salesamersp/f5_support_case_creation_api_tools:latest \
  bigip download --host 192.0.2.1 --filename target.qkview --output target.qkview --no-ssl-verify
```

---

## 3. Passing Credentials Securely

All credentials can be passed seamlessly into the container via environment variables or interactive prompts:

### Via Environment Variables
```bash
docker run --rm -it \
  -v $(pwd):/data \
  -e BIGIP_USERNAME="admin" \
  -e BIGIP_PASSWORD="YourPasswordHere" \
  -e F5_CLIENT_ID="your_auth0_client_id" \
  -e F5_CLIENT_SECRET="your_auth0_client_secret" \
  ghcr.io/salesamersp/f5_support_case_creation_api_tools:latest \
  run --host 192.0.2.1 --no-ssl-verify
```

### Via Interactive Terminal Prompt
If environment variables are omitted, `qkviewmgr` securely prompts with masked input in the terminal:
```bash
docker run --rm -it \
  -v $(pwd):/data \
  ghcr.io/salesamersp/f5_support_case_creation_api_tools:latest \
  run --host 192.0.2.1 --no-ssl-verify
```

### Interactive Terminal Wizard
```bash
docker run --rm -it \
  -v $(pwd):/data \
  ghcr.io/salesamersp/f5_support_case_creation_api_tools:latest \
  wizard
```

---

## 4. Container Architecture & Security Hardening

The container image adheres to enterprise security standards:

- **Unprivileged Non-Root Execution**: Runs as user `appuser` (`UID 10001:GID 10001`). No container root capabilities are granted.
- **Cryptographic Hash Pinning**: All dependencies are locked with SHA-256 digests (`requirements.lock`) during the build; modified or untrusted packages are rejected.
- **Minimal Attack Surface**: Built on minimal `python:3.12-slim-bookworm` with all development and compiler tooling stripped.
- **Multi-Architecture**: Multi-arch images built natively for both `linux/amd64` (x86_64 servers & Intel Macs) and `linux/arm64` (Apple Silicon M1/M2/M3/M4 & ARM servers).

---

## 5. Local Container Build

To build the container image locally from the repository source:

```bash
# Using Podman
podman build -t qkviewmgr:local .

# Using Docker
docker build -t qkviewmgr:local .

# Test local build
docker run --rm qkviewmgr:local doctor
```

---

## 6. Running Pytest & Test Suites Inside Containers

You can run the complete unit and live integration test suite directly inside your execution container:

```bash
# Using Podman in an execution container (e.g. tmos-cert-lab)
podman exec -w /home/appuser/f5_support_case_creation_api_tools tmos-cert-lab pytest tests/ -v

# Run system doctor diagnostics inside container
podman exec -w /home/appuser/f5_support_case_creation_api_tools tmos-cert-lab qkviewmgr doctor

# Using Docker with volume mount
docker run --rm -v $(pwd):/workspace -w /workspace \
  ghcr.io/salesamersp/f5_support_case_creation_api_tools:latest \
  pytest tests/ -v
```
