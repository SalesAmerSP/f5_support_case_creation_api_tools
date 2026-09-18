# Security & Supply Chain Hardening (GHAS)

This repository implements GitHub Advanced Security (GHAS) and software supply chain protection mechanisms to guard against dependency tampering, malicious code injection, and secret leakage.

---

## Security Architecture Overview

```
+---------------------------------------------------------------------------------------+
|                       GitHub Advanced Security (GHAS) Pipeline                        |
|                                                                                       |
|   +-------------------+  +--------------------+  +----------------+  +------------+   |
|   |  CodeQL Analysis  |  | Secret Leak Scan   |  | Supply Chain   |  | Dependabot |   |
|   |  (AST & Taint)    |  | (Gitleaks Engine)  |  | (Hash Pinning) |  | Security   |   |
|   +-------------------+  +--------------------+  +----------------+  +------------+   |
+---------------------------------------------------------------------------------------+
```

---

## 1. Cryptographic Lockfile Pinning (`requirements.lock`)

To prevent upstream supply chain attacks (e.g. package hijacking, compromise of PyPI accounts, or dependency confusion), all runtime dependencies are pinned with multi-architecture SHA-256 cryptographic hashes.

```bash
# Verify integrity and install only cryptographically authenticated wheels
pip install --require-hashes --no-deps -r requirements.lock
```

If an attacker modifies or replaces an upstream package file on PyPI, `pip` aborts installation immediately due to a hash mismatch.

---

## 2. Continuous Vulnerability Scanning (`pip-audit`)

Automated supply chain auditing is executed on every push and pull request via [`.github/workflows/security-audit.yml`](../.github/workflows/security-audit.yml):
- Scans all pinned dependencies against the official **PyPA Advisory Database** and **OSV (Open Source Vulnerabilities)** feed.
- Enforces strict hash-checking in CI runners.
- Exports results in standard **SARIF** (Static Analysis Results Interchange Format) to GitHub Code Scanning.

---

## 3. Semantic CodeQL Static Analysis

Static analysis runs on every push and pull request via [`.github/workflows/codeql.yml`](../.github/workflows/codeql.yml):
- Analyzes Python Abstract Syntax Trees (ASTs) for taint tracking, injection vulnerabilities, and memory/resource leaks.
- Uses GitHub's `security-extended` and `security-and-quality` rule suites.
- Flags insecure deserialization, improper certificate validation, and credential exposures.

---

## 4. Secret & Credential Leak Prevention (Gitleaks)

The repository protects against accidental commit of tokens, API keys, and device passwords:
- **CI Workflow**: [`.github/workflows/secret-scan.yml`](../.github/workflows/secret-scan.yml) runs Gitleaks across the git history on every push.
- **Custom Security Rules** ([`.gitleaks.toml`](../.gitleaks.toml)):
  - `bigip-admin-password`: Flags inline passwords for TMOS/BIG-IP.
  - `f5-auth0-client-secret`: Flags F5/Auth0/Okta client secrets.
  - `f5-icontrol-token`: Flags active iControl REST session tokens.
  - `f5-qkview-bundle-inclusion`: Blocks accidental commit of binary `.qkview` archives containing sensitive configuration data.

---

## 5. Automated Dependabot Security Updates

Configured in [`.github/dependabot.yml`](../.github/dependabot.yml):
- Checks GitHub Actions workflows and pip dependencies on a weekly schedule.
- Automatically opens PRs for security patches and CVE remediation.
- Automatically updates lockfile hashes when dependencies are bumped.

---

## 6. Pull Request Dependency Review

Configured in [`.github/workflows/dependency-review.yml`](../.github/workflows/dependency-review.yml):
- Evaluates newly added dependencies on every incoming pull request.
- Blocks pull requests that introduce packages with known CVEs or restrictive licenses.

---

## 7. Protected `main` Branch Policy

The `main` branch is protected against accidental overwrites, unvetted code, and supply chain regressions:
- **Mandatory Pull Requests**: Changes to `main` must be submitted via pull request with conversation resolution required.
- **Required CI Status Checks**: Merging requires 100% passing results from:
  - `CodeQL Code Scanning (python)` (Static AST security analysis)
  - `Secret & Credential Leak Scan` (Gitleaks token and key detection)
  - `Verify Hash-Pinned Lockfile Integrity` (Cryptographic dependency verification)
  - `Dependency Vulnerability Audit (pip-audit)` (CVE checking)
- **Destructive Operation Blocking**: Force pushes (`git push --force`) and branch deletions are strictly disabled.
- **Emergency Administrative Override**: Repository administrators can bypass when necessary for emergency hotfixes or automated releases.
