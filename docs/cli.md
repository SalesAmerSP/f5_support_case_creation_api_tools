# Primary CLI Orchestrator: `qkviewmgr`

`qkviewmgr` provides a unified command-line interface that consolidates all BIG-IP, iHealth, and MyF5 case operations into a single tool.

---

## Command Syntax Overview

```bash
qkviewmgr [--version] [-h] <subcommand> [options]
```

### Subcommands

| Subcommand | Description |
| :--- | :--- |
| `run` (or `auto`) | One-Touch Auto-Pilot diagnostic workflow |
| `doctor` | Pre-flight runtime, credential, and network reachability audit |
| `bigip` | Direct BIG-IP appliance management (`test`, `list`, `generate`, `download`, `delete`) |
| `ihealth` | Direct iHealth diagnostic operations (`test`, `list`, `show`, `upload`) |
| `case` | MyF5 support case operations (`list`, `create`, `comment`, `metadata`) |
| `gui` | Launch native desktop GUI (Tkinter, zero web services) |
| `wizard` | Launch interactive terminal wizard |

---

## 1. One-Touch Auto-Pilot (`qkviewmgr run`)

The `run` subcommand executes the complete end-to-end support pipeline in one command:
1. **Verifies BIG-IP connectivity & credentials** against `/mgmt/tm/sys/ready`.
2. **Generates a full QKView archive** on the appliance (using `-s0` non-truncate by default to preserve diagnostic fidelity).
3. **Downloads the QKView archive** to local storage with a real-time progress bar.
4. **Purges the remote archive** from `/var/tmp/` on the appliance to prevent disk exhaustion.
5. **Uploads to F5 iHealth** using TLS 1.3 streaming and a progress meter.
6. **Monitors iHealth processing**, reporting completion and returning the diagnostic analysis link.

```bash
# Basic run with interactive prompt or BIGIP_PASSWORD env var
qkviewmgr run --host 192.0.2.1 --no-ssl-verify

# Custom output file and associated MyF5 support case
qkviewmgr run \
  --host 192.0.2.1 \
  --username admin \
  --qkview-name bigip01_core_dump.qkview \
  --output-dir ./diagnostics \
  --case-number C1234567 \
  --description "Kernel panic after failover event" \
  --no-ssl-verify
```

### Auto-Pilot Options

| Flag | Description | Default |
| :--- | :--- | :--- |
| `--host` | Target BIG-IP hostname or IP address *(Required)* | — |
| `--username` | BIG-IP admin username | `$BIGIP_USERNAME` or `'admin'` |
| `--password` | BIG-IP password (emits security warning if passed on CLI) | `$BIGIP_PASSWORD` or masked prompt |
| `--no-ssl-verify` | Disable SSL validation for lab devices with self-signed certificates | `False` (SSL verified) |
| `--qkview-name` | Custom name for the generated QKView archive | `<host>_diag.qkview` |
| `--no-truncate` | Pass `-s0` to qkview to prevent truncation of large log files | `False` |
| `--output-dir` | Local directory for downloaded QKView file | `.` |
| `--no-delete-remote` | Keep temporary QKView on BIG-IP `/var/tmp/` after download | `False` (purged automatically) |
| `--no-upload` | Skip upload to iHealth (only generate and download) | `False` (uploaded) |
| `--case-number` | Associate iHealth upload with existing MyF5 case | `None` |
| `--description` | Descriptive title for iHealth upload | `None` |
| `--no-wait` | Exit immediately after upload without polling for analysis completion | `False` (polls until complete) |
| `--client-id` | F5 Identity Client ID | `$F5_CLIENT_ID` or `~/.ihealth_credentials` |
| `--client-secret` | F5 Identity Client Secret | `$F5_CLIENT_SECRET` or `~/.ihealth_credentials` |
| `--profile` | Configuration section in `~/.ihealth_credentials` | `'default'` |

---

## 2. System Doctor (`qkviewmgr doctor`)

Performs a pre-flight audit of the local runtime, credentials, and network connectivity without modifying any systems or creating cases:

```bash
qkviewmgr doctor
```

Checks performed:
- Python executable path, Python version, and OpenSSL version.
- Credential detection (`~/.ihealth_credentials`, environment variables).
- TLS 1.2+ handshake and connectivity to all F5 Cloud endpoints:
  - F5 Identity (Auth0): `idp.identity.f5.com`
  - F5 Identity (Okta): `identity.account.f5.com`
  - F5 iHealth API: `ihealth2-api.f5.com`
  - MyF5 Support API: `support.apis.f5.com`

---

## 3. Direct BIG-IP Appliance Subcommands (`qkviewmgr bigip`)

```bash
# Test appliance reachability & system readiness
qkviewmgr bigip test --host 192.0.2.1 --no-ssl-verify

# List existing QKView files on the appliance (/var/tmp)
qkviewmgr bigip list --host 192.0.2.1 --no-ssl-verify

# Generate a QKView file on the appliance
qkviewmgr bigip generate --host 192.0.2.1 --filename diag.qkview --no-truncate --no-ssl-verify

# Download a QKView from the appliance
qkviewmgr bigip download --host 192.0.2.1 --filename diag.qkview --output ./diag.qkview --no-ssl-verify

# Delete a QKView from appliance storage
qkviewmgr bigip delete --host 192.0.2.1 --filename diag.qkview --no-ssl-verify
```

---

## 4. Direct iHealth Subcommands (`qkviewmgr ihealth`)

```bash
# Verify authentication to F5 iHealth API
qkviewmgr ihealth test

# List all QKViews uploaded under your account
qkviewmgr ihealth list

# Show metadata, processing status, and diagnostic results for a specific QKView
qkviewmgr ihealth show --qkview-id 26894783

# Upload a local QKView file to iHealth
qkviewmgr ihealth upload --filename ./diag.qkview --case-number C1234567 --description "Investigating failover"
```

---

## 5. Direct MyF5 Support Case Subcommands (`qkviewmgr case`)

```bash
# List open support cases
qkviewmgr case list

# Retrieve case creation schema metadata (valid product lines, severity levels, components)
qkviewmgr case metadata

# Create a new support case from a JSON payload
qkviewmgr case create --json-file case_inputs.json

# Add an update comment to an existing support case
qkviewmgr case comment --case-number C1234567 --comment "Uploaded new diagnostic QKView file."
```
