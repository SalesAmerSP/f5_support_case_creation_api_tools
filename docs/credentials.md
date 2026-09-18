# Credentials & Secret Management

This guide explains how credentials and API secrets are securely handled in `qkviewmgr` and all standalone example scripts.

---

## Security Philosophy: Zero Plaintext Secrets in CLI Arguments

Passing passwords or API keys as command-line arguments is insecure for production and multi-user environments:
- Secrets appear in plain text in process listings (`ps aux`, `/proc/<pid>/cmdline`).
- Secrets are persisted to shell history files (`~/.bash_history`, `~/.zsh_history`).
- Secrets can be logged by endpoint detection and response (EDR) agents or system audit daemons (`auditd`).

> [!IMPORTANT]
> `qkviewmgr` enforces **Zero-Secret CLI Operations**. If `--password`, `--client-id`, or `--client-secret` is passed via CLI arguments, a security warning is emitted to alert the operator to the process-listing risk.

---

## Supported Authentication Methods

All tools resolve credentials through a prioritized hierarchy:
1. **Command-line arguments** (supported for legacy workflows, but emits a security warning)
2. **Environment variables** (ideal for CI/CD pipelines, containerized deployments, and automation)
3. **Local profile file** (`~/.ihealth_credentials` mode `0600`)
4. **Interactive masked prompts** (`getpass`)

---

### Method 1: Environment Variables (Recommended for Automation)

Export the desired environment variables in your shell profile or pipeline runner:

```bash
# BIG-IP Appliance Credentials
export BIGIP_USERNAME="admin"
export BIGIP_PASSWORD="YourAppliancePassword"

# F5 Cloud / iHealth / MyF5 API Credentials
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
| `F5_CLIENT_ID` | `IHEALTH_CLIENT_ID` | OAuth2 Client ID for F5 Identity Services | Interactive prompt / config file |
| `F5_CLIENT_SECRET` | `IHEALTH_CLIENT_SECRET` | OAuth2 Client Secret for F5 Identity Services | Interactive prompt / config file |
| `F5_MYF5_API_K_VALUE`| `MYF5_K_VALUE` | Query parameter authorization key for MyF5 API | Built-in production key |

---

### Method 2: Credential Profile File (`~/.ihealth_credentials`)

For persistent local developer workstations, store credentials in an INI-formatted file at `~/.ihealth_credentials`.

```ini
[default]
clientid = YourF5SupportAPIClientID
clientsecret = YourF5SupportAPIClientSecret

[production]
clientid = ProdF5SupportAPIClientID
clientsecret = ProdF5SupportAPIClientSecret
```

#### Restrict Permissions
Ensure the file is readable only by your user account:
```bash
chmod 0600 ~/.ihealth_credentials
```

#### Selecting Profiles
Specify an alternate profile using the `--profile` option:
```bash
qkviewmgr ihealth list --profile production
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
