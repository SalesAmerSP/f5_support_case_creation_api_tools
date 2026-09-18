# User Interfaces: Native Desktop GUI & Terminal Wizard

For operators who prefer graphical workflows or interactive terminal prompts over command-line flags, `qkviewmgr` includes both a **Native Desktop GUI** and an **Interactive Terminal Wizard**.

---

## 1. Native Desktop GUI (`qkviewmgr gui`)

The graphical interface is built using Python's standard `tkinter` and `ttk` libraries.

```bash
qkviewmgr gui
```

> [!TIP]
> **Strictly NO Web Services**:
> - Does **NOT** run an HTTP/web server.
> - Does **NOT** bind to any local TCP ports (no `localhost:8080`, `localhost:5000`, etc.).
> - Does **NOT** open a web browser.
> - Executes 100% locally on the host desktop windowing system (X11, Wayland, macOS Cocoa, or Windows User32).
> - All network operations (file generation, chunked downloads, uploads) execute in background worker threads to keep the UI smooth and responsive.

### Graphical Tabs Walkthrough

#### Tab 1: Auto-Pilot
- Input the target BIG-IP appliance hostname or IP.
- Enter username (defaults to `$BIGIP_USERNAME` or `admin`).
- Enter password in a masked password field (or leave blank if `$BIGIP_PASSWORD` is exported).
- Toggle SSL verification (`--no-ssl-verify` for lab appliances with self-signed certificates).
- Optional: enter existing MyF5 Case Number or custom QKView filename.
- Click **Run Auto-Pilot** to watch the real-time activity stream as the archive is generated, downloaded, purged from the appliance, and submitted to iHealth.

#### Tab 2: BIG-IP Direct Operations
- Execute individual appliance tasks without running the full pipeline:
  - **Test Connection**: Validates `/mgmt/tm/sys/ready`.
  - **List QKViews**: Displays archives stored in `/var/tmp/`.
  - **Generate**: Triggers QKView generation with optional `-s0` non-truncate flag.
  - **Download**: Pulls an archive to local disk.
  - **Delete**: Cleans up old archives to free appliance storage.

#### Tab 3: iHealth & Case Management
- Query and view uploaded QKView diagnostics and analysis status.
- Inspect active and closed MyF5 support cases.

#### Tab 4: System Doctor
- One-click health check testing Python runtime, OpenSSL version, cipher suites, credential detection, and network reachability to all F5 Cloud endpoints.

### Graceful Fallback for Headless Systems

If the desktop GUI is invoked in an environment where Python `tkinter` is unavailable (e.g. headless Linux, minimal container, or missing `python3-tk`), `qkviewmgr` handles the condition gracefully:
1. Emits a clear message explaining why the GUI cannot open.
2. Displays the exact OS package manager command to install `tkinter` (e.g. `sudo apt-get install python3-tk` or `brew install python-tk`).
3. Automatically falls back to the **Guided Terminal Wizard**.

---

## 2. Interactive Terminal Wizard (`qkviewmgr wizard`)

For SSH jump boxes, bastions, or terminal-only environments, the Guided Terminal Wizard walks operators through operations step-by-step with interactive prompts and masked password inputs.

```bash
qkviewmgr wizard
```

### Wizard Main Menu

```
=================================================================
          qkviewmgr Interactive Terminal Wizard
=================================================================

1. Run Auto-Pilot (Generate -> Download -> Purge -> Upload)
2. Direct BIG-IP Operations (Test, List, Download, Delete)
3. Direct iHealth Operations (Test, List, Upload)
4. System Doctor (Pre-flight Runtime & Network Diagnostics)
5. Exit
```

### Key Wizard Capabilities
- **Pre-populated Defaults**: Automatically detects and displays values from environment variables (`BIGIP_USERNAME`, `BIGIP_PASSWORD`, `F5_CLIENT_ID`).
- **Masked Passwords**: Password inputs use `getpass` masking so passwords never display on-screen.
- **Confirmation Prompts**: Requires explicit confirmation before destructive actions (e.g. deleting remote QKView files).
