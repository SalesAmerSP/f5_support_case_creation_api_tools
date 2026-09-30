# Credentials & Secret Management

This guide explains how credentials and API secrets are securely handled in `qkviewmgr` and all standalone example scripts.

---

## Security Philosophy: Zero Plaintext Secrets in CLI Arguments

Passing passwords or API keys as command-line arguments is strictly prohibited:
- Secrets appear in plain text in process listings (`ps aux`, `/proc/<pid>/cmdline`).
- Secrets are persisted to shell history files (`~/.bash_history`, `~/.zsh_history`).
- Secrets can be logged by endpoint detection and response (EDR) agents or system audit daemons (`auditd`).

> [!IMPORTANT]
> `qkviewmgr` and all bundled utilities enforce **Zero-Secret CLI Security**. If `--password`, `--client-id`, `--client-secret`, or related secret flags are passed on the command line, execution is immediately halted with exit code 2 and a security advisory is printed.

---

## Required Authentication Methods

All tools require credentials to be stored in **environment variables** or **configuration files**:

1. **Environment Variables**: Best for CI/CD pipelines, containerized deployments, and automation.
2. **Credential Files**: Best for local developer workstations:
   - Primary: `~/.f5api_credentials` (mode `0600`)
   - Fallback: `~/.ihealth_credentials`
3. **Interactive Masked Prompts**: Fallback for appliance passwords via `getpass`.

---

### Method 1: Environment Variables (Recommended for Automation)

Export the credentials in your shell environment or CI/CD runner:

```bash
# BIG-IP Appliance Credentials
export BIGIP_USERNAME="admin"
export BIGIP_PASSWORD="YourAppliancePassword"

# F5 Cloud / iHealth / MyF5 / Downloads API Credentials
export F5_CLIENT_ID="YourF5SupportAPIClientID"
export F5_CLIENT_SECRET="YourF5SupportAPIClientSecret"

# Optional: Enterprise Proxy / Alternate MyF5 API K-Value Override
export F5_MYF5_API_K_VALUE="UKKD3Vxv7NHrM3QmYk8Fk2mZnLtljAKX"
```

#### Supported Environment Variable Aliases

| Variable | Supported Aliases | Description | Default if Unset |
| :--- | :--- | :--- | :--- |
| `BIGIP_USERNAME` | `BIGIP_USER`, `F5_USERNAME` | Username for target BIG-IP appliance | `'admin'` |
| `BIGIP_PASSWORD` | `F5_PASSWORD` | Password for target BIG-IP appliance | Interactive prompt |
| `F5_CLIENT_ID` | `IHEALTH_CLIENT_ID` | OAuth2 Client ID for F5 Identity Services | Read from `~/.f5api_credentials` |
| `F5_CLIENT_SECRET` | `IHEALTH_CLIENT_SECRET` | OAuth2 Client Secret for F5 Identity Services | Read from `~/.f5api_credentials` |
| `F5_MYF5_API_K_VALUE`| `MYF5_K_VALUE` | Query parameter authorization key for MyF5 API | Built-in production key |

---

### Method 2: Primary Credential File (`~/.f5api_credentials`)

Store your F5 API credentials in `~/.f5api_credentials`. This file supports simple `KEY=VALUE` formatting or INI profile sections:

**Simple format (`KEY=VALUE`):**
```bash
username=g.robinson@f5.com
client_id=YourF5SupportAPIClientID
client_secret=YourF5SupportAPIClientSecret
```

**INI Profile format:**
```ini
[default]
client_id = YourF5SupportAPIClientID
client_secret = YourF5SupportAPIClientSecret

[production]
client_id = ProdF5SupportAPIClientID
client_secret = ProdF5SupportAPIClientSecret
```

#### Restrict Permissions
Ensure your credentials file is readable only by your user account:
```bash
chmod 0600 ~/.f5api_credentials
```

#### Selecting Profiles
Specify an alternate profile using the `--profile` option:
```bash
qkviewmgr ihealth list --profile production
download_browser families --profile production
```

---

### Method 3: Interactive Masked Prompts (Recommended for Manual CLI Sessions)

When executing commands without pre-configured environment variables or credentials files, the CLI prompts you safely using `getpass`. Input is masked and never echoed to the screen or shell history:

```bash
qkviewmgr bigip test --host 192.0.2.1
# Output:
# Enter BIG-IP password for admin@192.0.2.1: [hidden]
```

```bash
qkviewmgr ihealth list
# Output:
# Enter F5 API Client ID: [hidden]
# Enter F5 API Client Secret: [hidden]
```

---

## Auditing Credential Status with System Doctor

To verify whether your credentials are recognized without performing any live API operations, run:

```bash
qkviewmgr doctor
```

Sample audit output:
```
2. Credential Configuration:
   ✓ Found ~/.ihealth_credentials
   ✓ BIGIP_USERNAME set in environment (admin)
   ✓ BIGIP_PASSWORD set in environment
   ✓ F5_CLIENT_ID set in environment
```
