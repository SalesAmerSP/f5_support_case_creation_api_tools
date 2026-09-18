# Standalone Binary Packaging (PyInstaller)

For operational jump boxes, customer sites, or air-gapped environments where Python and external dependencies cannot be installed, `qkviewmgr` can be packaged and run as a single, self-contained executable binary.

---

## Why Standalone Binaries?

- **Zero Runtime Dependencies**: The operator does not need Python, `pip`, or virtual environments installed.
- **Embedded SSL Trust Stores**: Bundles Mozilla's trusted root certificates via `certifi` directly into the binary.
- **Tamper-Resistant**: The entire runtime and application code are bundled into a single signed binary executable.

---

## Local Compilation

The project includes an automated build script and a hardened PyInstaller specification:

```bash
# Ensure build requirements are installed
pip install pyinstaller

# Run compilation script
python3 scripts/build_binary.py
```

### Build Artifacts
- The standalone binary is produced in `dist/`:
  - **macOS / Linux**: `dist/qkviewmgr`
  - **Windows**: `dist/qkviewmgr.exe`
- The build script automatically executes a post-build smoke test (`qkviewmgr --version` and `qkviewmgr --help`) to verify binary integrity before completion.

---

## PyInstaller Specification Details (`qkviewmgr.spec`)

The build specification defines:
- **Entrypoint**: `src/qkviewmgr/qkviewmgr.py`
- **Data Bundling**: Embeds `certifi/cacert.pem` to ensure valid TLS root CA trust across all operating systems.
- **Hidden Imports**: Explicitly includes `tqdm`, `urllib3`, `requests`, `certifi`, and Tkinter modules.
- **Console Mode**: Enables full terminal I/O for interactive prompts, streaming progress bars, and logging.

---

## Multi-Platform CI Release Matrix

On every release tag (`v*`), our GitHub Actions release workflow (`.github/workflows/release.yml`) compiles cross-platform binaries across three platforms:

| Platform Artifact | Target Architecture | Runner |
| :--- | :--- | :--- |
| `qkviewmgr-macos-arm64` | macOS Apple Silicon (M1/M2/M3/M4) | `macos-14` |
| `qkviewmgr-linux-x86_64` | Linux 64-bit (glibc) | `ubuntu-latest` |
| `qkviewmgr-windows-x64.exe` | Windows 64-bit | `windows-latest` |

---

## Supply Chain Provenance & Cryptographic Attestations

Every binary distributed in GitHub Releases includes enterprise supply chain attestations:

1. **Software Bill of Materials (SBOM)**:
   - Generated in SPDX JSON format via Anchore Syft.
   - Catalogues all bundled components and versions.
2. **SLSA Level 3 Build Provenance**:
   - Built and signed using GitHub Artifact Attestations (`actions/attest-build-provenance`).
   - Cryptographically binds the compiled binary to the exact commit SHA and GitHub Actions runner that produced it.
   - Verifiable using the GitHub CLI:
     ```bash
     gh attestation verify dist/qkviewmgr --owner SalesAmerSP
     ```
