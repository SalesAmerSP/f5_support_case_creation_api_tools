"""Native Desktop GUI for F5 QKView and Support Case Operations.

STRICT DESIGN MANDATE: NO WEB SERVICES.
This module uses native Python desktop GUI widgets (tkinter/ttk) exclusively.
It binds NO network ports, starts NO web/HTTP servers, and requires NO browser.
"""

import os
import signal
import sys
import threading

try:
    from . import f5functions
except ImportError:
    import f5functions

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    TKINTER_AVAILABLE = True
    _BaseApp = tk.Tk
    _TKINTER_IMPORT_ERROR = None
except (ImportError, ModuleNotFoundError) as _err:
    tk = None
    ttk = None
    messagebox = None
    filedialog = None
    TKINTER_AVAILABLE = False
    _BaseApp = object
    _TKINTER_IMPORT_ERROR = str(_err)


class QKViewMgrApp(_BaseApp):
    """Native Tkinter Desktop GUI Application for F5 QKView & Support Case Management."""

    def __init__(self):
        if not TKINTER_AVAILABLE:
            raise RuntimeError(f"Tkinter is not available: {_TKINTER_IMPORT_ERROR}")
        super().__init__()
        self.title("F5 QKView Manager (qkviewmgr)")
        self.geometry("780x580")
        self.minsize(640, 480)

        # Styling
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # Layout Notebook (Tabs)
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tab_auto = ttk.Frame(notebook)
        tab_bigip = ttk.Frame(notebook)
        tab_ihealth = ttk.Frame(notebook)
        tab_doctor = ttk.Frame(notebook)

        notebook.add(tab_auto, text="  One-Touch Auto-Pilot  ")
        notebook.add(tab_bigip, text="  BIG-IP Direct  ")
        notebook.add(tab_ihealth, text="  iHealth & Cases  ")
        notebook.add(tab_doctor, text="  System Doctor  ")

        self._build_auto_tab(tab_auto)
        self._build_bigip_tab(tab_bigip)
        self._build_ihealth_tab(tab_ihealth)
        self._build_doctor_tab(tab_doctor)

        # Bottom Log View
        log_frame = ttk.LabelFrame(self, text="Activity Log (Zero Web Services - Pure Native GUI)")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.log_text = tk.Text(log_frame, height=8, wrap=tk.WORD, font=("Courier", 11))
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # Intercept window manager close event
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Polling timer allowing Python interpreter to process signals (like SIGINT / Ctrl+C)
        self._poll_sigint()

        self.log("QKView Manager initialized. Desktop GUI ready.")

    def _poll_sigint(self):
        """Periodic callback that gives Python interpreter control to handle signals."""
        try:
            self.after(200, self._poll_sigint)
        except Exception:
            pass

    def _on_close(self):
        """Handle window manager close event cleanly."""
        try:
            self.destroy()
        except Exception:
            pass

    def log(self, message):
        try:
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
        except Exception:
            pass

    def _run_threaded(self, target, *args):
        def _worker():
            try:
                target(*args)
            except (Exception, SystemExit) as err:
                err_msg = str(err)
                if not err_msg and hasattr(err, "code"):
                    err_msg = str(err.code)
                if not err_msg:
                    err_msg = type(err).__name__
                self.log(f"✗ Operation encountered an error: {err_msg}")
            except BaseException:
                pass

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    # ---------------------------------------------------------------------
    # Tab 1: One-Touch Auto-Pilot
    # ---------------------------------------------------------------------
    def _build_auto_tab(self, parent):
        frame = ttk.Frame(parent, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Automated End-to-End Workflow: BIG-IP -> Local -> iHealth", font=("Helvetica", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))

        ttk.Label(frame, text="BIG-IP Host / IP:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.auto_host = ttk.Entry(frame, width=35)
        self.auto_host.grid(row=1, column=1, sticky=tk.W, pady=4)
        self.auto_host.insert(0, os.getenv("BIGIP_HOST", ""))

        ttk.Label(frame, text="Username:").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.auto_user = ttk.Entry(frame, width=35)
        self.auto_user.grid(row=2, column=1, sticky=tk.W, pady=4)
        self.auto_user.insert(0, os.getenv("BIGIP_USERNAME") or os.getenv("BIGIP_USER") or "admin")

        ttk.Label(frame, text="Password:").grid(row=3, column=0, sticky=tk.W, pady=4)
        self.auto_pw = ttk.Entry(frame, width=35, show="*")
        self.auto_pw.grid(row=3, column=1, sticky=tk.W, pady=4)
        if os.getenv("BIGIP_PASSWORD"):
            self.auto_pw.insert(0, os.getenv("BIGIP_PASSWORD"))

        self.auto_ssl_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Verify SSL Certificate (Uncheck for self-signed lab appliances)", variable=self.auto_ssl_var).grid(row=4, column=1, sticky=tk.W, pady=4)

        ttk.Label(frame, text="Support Case # (optional):").grid(row=5, column=0, sticky=tk.W, pady=4)
        self.auto_case = ttk.Entry(frame, width=35)
        self.auto_case.grid(row=5, column=1, sticky=tk.W, pady=4)

        btn_start = ttk.Button(frame, text="▶ Run Auto-Pilot", command=lambda: self._run_threaded(self._exec_auto_pilot))
        btn_start.grid(row=6, column=1, sticky=tk.W, pady=15)

    def _exec_auto_pilot(self):
        host = self.auto_host.get().strip()
        user = self.auto_user.get().strip()
        pw = self.auto_pw.get().strip()
        verify = self.auto_ssl_var.get()
        case = self.auto_case.get().strip() or None

        if not host:
            self.log("ERROR: BIG-IP Host / IP is required.")
            return
        if not user:
            self.log("ERROR: Username is required.")
            return
        if not pw:
            self.log("ERROR: Password is required.")
            return

        self.log(f"Starting Auto-Pilot for BIG-IP: {host}...")
        try:
            # 1. Connectivity test
            self.log(f"Connecting to BIG-IP {host} (SSL verify: {verify})...")
            res = f5functions.bigip_connectivity_test(host, user, pw, verify=verify)
            if res.status_code == 200:
                self.log("✓ BIG-IP connection verified (HTTP 200 OK - System Ready).")
            elif res.status_code == 401:
                self.log(f"✗ Authentication failed on {host}: HTTP 401 Unauthorized. Check username and password.")
                return
            elif res.status_code == 403:
                self.log(f"✗ Authorization failed on {host}: HTTP 403 Forbidden. User lacks required permissions.")
                return
            else:
                self.log(f"✗ BIG-IP connection returned HTTP {res.status_code}: {res.text}")
                return

            # 2. Generate
            qkview_name = f"{host.replace('.', '_')}_autopilot.qkview"
            self.log(f"Generating QKView '{qkview_name}' on appliance...")
            f5functions.bigip_generate_qkview(host, user, pw, qkview_name, verify=verify)
            self.log("✓ QKView generated on appliance.")

            # 3. Download
            local_path = os.path.join(".", qkview_name)
            self.log(f"Downloading {qkview_name} to local storage...")
            f5functions.bigip_download_qkview(host, user, pw, qkview_name, local_path, verify=verify)
            self.log(f"✓ Download complete: {local_path} ({os.path.getsize(local_path):,} bytes)")

            # 4. Purge remote
            self.log(f"Purging remote QKView from appliance storage...")
            f5functions.bigip_delete_qkview(host, user, pw, qkview_name, verify=verify)
            self.log("✓ Remote storage purged.")

            # 5. iHealth Upload
            self.log("Resolving iHealth API credentials...")
            cid, csec = f5functions.resolve_ihealth_credentials()
            token = f5functions.myf5_authenticate(f5functions.IHEALTH_APP_ID, cid, csec, scope="ihealth")
            self.log("✓ Authenticated to F5 Identity Services.")
            self.log(f"Streaming {qkview_name} to F5 iHealth over TLS 1.3...")
            resp = f5functions.ihealth_upload_qkview(token, local_path, case_number=case, description="Uploaded via qkviewmgr GUI")
            if resp.status_code in [200, 201, 202]:
                self.log("✓ Upload to iHealth succeeded!")
                try:
                    res_data = resp.json()
                    qid = res_data.get("id") or res_data.get("qkview_id")
                    if qid:
                        self.log(f"   QKView ID: {qid}")
                        self.log(f"   Analysis URL: https://ihealth.f5.com/qkview-analyzer/qv/{qid}")
                except Exception:
                    pass
            else:
                self.log(f"Upload failed: HTTP {resp.status_code}: {resp.text}")

        except (Exception, SystemExit) as e:
            err_msg = str(e)
            if not err_msg and hasattr(e, "code"):
                err_msg = str(e.code)
            self.log(f"Auto-Pilot encountered an error: {err_msg}")

    # ---------------------------------------------------------------------
    # Tab 2: BIG-IP Direct Operations
    # ---------------------------------------------------------------------
    def _build_bigip_tab(self, parent):
        frame = ttk.Frame(parent, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="BIG-IP Direct Device Management", font=("Helvetica", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))

        ttk.Label(frame, text="Host / IP:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.bigip_host = ttk.Entry(frame, width=35)
        self.bigip_host.grid(row=1, column=1, sticky=tk.W, pady=4)
        self.bigip_host.insert(0, os.getenv("BIGIP_HOST", ""))

        ttk.Label(frame, text="Username:").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.bigip_user = ttk.Entry(frame, width=35)
        self.bigip_user.grid(row=2, column=1, sticky=tk.W, pady=4)
        self.bigip_user.insert(0, os.getenv("BIGIP_USERNAME") or os.getenv("BIGIP_USER") or "admin")

        ttk.Label(frame, text="Password:").grid(row=3, column=0, sticky=tk.W, pady=4)
        self.bigip_pw = ttk.Entry(frame, width=35, show="*")
        self.bigip_pw.grid(row=3, column=1, sticky=tk.W, pady=4)
        if os.getenv("BIGIP_PASSWORD"):
            self.bigip_pw.insert(0, os.getenv("BIGIP_PASSWORD"))

        self.bigip_ssl_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Verify SSL Certificate (Uncheck for self-signed lab appliances)", variable=self.bigip_ssl_var).grid(row=4, column=1, sticky=tk.W, pady=4)

        btn_box = ttk.Frame(frame)
        btn_box.grid(row=5, column=0, columnspan=2, pady=15, sticky=tk.W)

        ttk.Button(btn_box, text="Test Connection", command=lambda: self._run_threaded(self._test_bigip)).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_box, text="List QKViews", command=lambda: self._run_threaded(self._list_bigip_qkviews)).pack(side=tk.LEFT, padx=4)

    def _test_bigip(self):
        h = self.bigip_host.get().strip()
        u = self.bigip_user.get().strip()
        p = self.bigip_pw.get().strip()
        verify = self.bigip_ssl_var.get()

        if not h:
            self.log("ERROR: BIG-IP Host / IP is required.")
            return
        if not u:
            self.log("ERROR: Username is required.")
            return
        if not p:
            self.log("ERROR: Password is required.")
            return

        self.log(f"Testing BIG-IP connection to {h} (SSL verify: {verify})...")
        try:
            res = f5functions.bigip_connectivity_test(h, u, p, verify=verify)
            if res.status_code == 200:
                self.log(f"✓ Connection to {h} succeeded (HTTP 200 OK - System Ready).")
            elif res.status_code == 401:
                self.log(f"✗ Authentication failed on {h}: HTTP 401 Unauthorized. Check username and password.")
            elif res.status_code == 403:
                self.log(f"✗ Authorization failed on {h}: HTTP 403 Forbidden. User lacks required permissions.")
            else:
                self.log(f"✗ Connection to {h} returned unexpected status HTTP {res.status_code}: {res.text}")
        except (Exception, SystemExit) as e:
            err_msg = str(e)
            if not err_msg and hasattr(e, "code"):
                err_msg = str(e.code)
            self.log(f"✗ Connection to {h} failed: {err_msg}")

    def _list_bigip_qkviews(self):
        h = self.bigip_host.get().strip()
        u = self.bigip_user.get().strip()
        p = self.bigip_pw.get().strip()
        verify = self.bigip_ssl_var.get()

        if not h:
            self.log("ERROR: BIG-IP Host / IP is required.")
            return
        if not u:
            self.log("ERROR: Username is required.")
            return
        if not p:
            self.log("ERROR: Password is required.")
            return

        self.log(f"Querying QKViews on {h} (SSL verify: {verify})...")
        try:
            res = f5functions.bigip_list_qkviews(h, u, p, verify=verify)
            if res.status_code == 200:
                items = res.json().get("items", [])
                self.log(f"Found {len(items)} QKView(s) on appliance:")
                for it in items:
                    self.log(f"  - {it.get('name', 'N/A')} (ID: {it.get('id', 'N/A')})")
            elif res.status_code == 401:
                self.log(f"✗ Authentication failed on {h}: HTTP 401 Unauthorized. Check username and password.")
            elif res.status_code == 403:
                self.log(f"✗ Authorization failed on {h}: HTTP 403 Forbidden. User lacks required permissions.")
            else:
                self.log(f"✗ Failed to list QKViews (HTTP {res.status_code}): {res.text}")
        except (Exception, SystemExit) as e:
            err_msg = str(e)
            if not err_msg and hasattr(e, "code"):
                err_msg = str(e.code)
            self.log(f"✗ Listing failed: {err_msg}")

    # ---------------------------------------------------------------------
    # Tab 3: iHealth & Case Operations
    # ---------------------------------------------------------------------
    def _build_ihealth_tab(self, parent):
        frame = ttk.Frame(parent, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="F5 iHealth & MyF5 Case Management", font=("Helvetica", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))

        btn_box = ttk.Frame(frame)
        btn_box.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        ttk.Button(btn_box, text="Test iHealth API", command=lambda: self._run_threaded(self._test_ihealth)).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_box, text="Test MyF5 Case API", command=lambda: self._run_threaded(self._test_myf5)).pack(side=tk.LEFT, padx=4)

        ttk.Button(frame, text="List iHealth QKViews", command=lambda: self._run_threaded(self._list_ihealth)).grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Button(frame, text="List MyF5 Support Cases", command=lambda: self._run_threaded(self._list_cases)).grid(row=3, column=0, sticky=tk.W, pady=5)

    def _test_ihealth(self):
        self.log("Testing F5 iHealth API connectivity & auth...")
        try:
            cid, csec = f5functions.resolve_ihealth_credentials()
            if not cid or not csec:
                self.log("ERROR: Missing F5 Client ID or Secret in ~/.ihealth_credentials or environment variables.")
                return
            token = f5functions.myf5_authenticate(f5functions.IHEALTH_APP_ID, cid, csec, scope="ihealth")
            self.log("✓ Authenticated to F5 Identity Services.")
            res = f5functions.ihealth_connectivity_test(token)
            if res.status_code == 200:
                self.log("✓ iHealth API connection and token verified (HTTP 200 OK).")
            else:
                self.log(f"✗ iHealth API returned HTTP {res.status_code}: {res.text}")
        except (Exception, SystemExit) as e:
            err_msg = str(e)
            if not err_msg and hasattr(e, "code"):
                err_msg = str(e.code)
            self.log(f"✗ iHealth connectivity test failed: {err_msg}")

    def _test_myf5(self):
        self.log("Testing MyF5 Case API connectivity & auth...")
        try:
            cid, csec = f5functions.resolve_ihealth_credentials()
            if not cid or not csec:
                self.log("ERROR: Missing F5 Client ID or Secret in ~/.ihealth_credentials or environment variables.")
                return
            token = f5functions.myf5_authenticate(f5functions.MYF5_APP_ID, cid, csec, scope="myf5_scope")
            self.log("✓ Authenticated to F5 Identity Services.")
            res = f5functions.myf5_connectivity_test(token)
            if res.status_code == 200:
                self.log("✓ MyF5 Support API connection and token verified (HTTP 200 OK).")
            else:
                self.log(f"✗ MyF5 Support API returned HTTP {res.status_code}: {res.text}")
        except (Exception, SystemExit) as e:
            err_msg = str(e)
            if not err_msg and hasattr(e, "code"):
                err_msg = str(e.code)
            self.log(f"✗ MyF5 connectivity test failed: {err_msg}")

    def _list_ihealth(self):
        self.log("Authenticating to F5 iHealth...")
        try:
            cid, csec = f5functions.resolve_ihealth_credentials()
            if not cid or not csec:
                self.log("ERROR: Missing F5 Client ID or Secret in ~/.ihealth_credentials or environment variables.")
                return
            token = f5functions.myf5_authenticate(f5functions.IHEALTH_APP_ID, cid, csec, scope="ihealth")
            self.log("✓ Authenticated. Querying QKViews...")
            res = f5functions.ihealth_list_qkview_ids(token)
            if res.status_code == 200:
                ids = res.json().get("id", [])
                self.log(f"Total iHealth QKViews found: {len(ids)}")
                for qid in ids:
                    self.log(f"  - QKView ID: {qid}")
            elif res.status_code == 401:
                self.log("✗ Authentication failed on iHealth API: HTTP 401 Unauthorized.")
            elif res.status_code == 403:
                self.log("✗ Authorization failed on iHealth API: HTTP 403 Forbidden.")
            else:
                self.log(f"✗ Failed to list iHealth QKViews (HTTP {res.status_code}): {res.text}")
        except (Exception, SystemExit) as e:
            err_msg = str(e)
            if not err_msg and hasattr(e, "code"):
                err_msg = str(e.code)
            self.log(f"✗ iHealth query failed: {err_msg}")

    def _list_cases(self):
        self.log("Authenticating to MyF5 Case API...")
        try:
            cid, csec = f5functions.resolve_ihealth_credentials()
            if not cid or not csec:
                self.log("ERROR: Missing F5 Client ID or Secret in ~/.ihealth_credentials or environment variables.")
                return
            token = f5functions.myf5_authenticate(f5functions.MYF5_APP_ID, cid, csec, scope="myf5_scope")
            self.log("✓ Authenticated. Querying cases...")
            cases = f5functions.myf5_list_support_cases(token)
            if cases.status_code == 200:
                data = cases.json().get("data", [])
                self.log(f"Found {len(data)} support case(s):")
                for c in data:
                    self.log(f"  - Case {c.get('caseNumber', 'N/A')}: {c.get('subject', 'No Subject')} [{c.get('status', 'Open')}]")
            elif cases.status_code == 401:
                self.log("✗ Authentication failed on MyF5 Case API: HTTP 401 Unauthorized.")
            elif cases.status_code == 403:
                self.log("✗ Authorization failed on MyF5 Case API: HTTP 403 Forbidden.")
            else:
                self.log(f"✗ Case listing failed (HTTP {cases.status_code}): {cases.text}")
        except (Exception, SystemExit) as e:
            err_msg = str(e)
            if not err_msg and hasattr(e, "code"):
                err_msg = str(e.code)
            self.log(f"✗ Case listing failed: {err_msg}")

    # ---------------------------------------------------------------------
    # Tab 4: System Doctor
    # ---------------------------------------------------------------------
    def _build_doctor_tab(self, parent):
        frame = ttk.Frame(parent, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Environment & Security Health Check", font=("Helvetica", 12, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0, 15))

        ttk.Button(frame, text="Run Diagnostic Health Check", command=lambda: self._run_threaded(self._exec_doctor)).grid(row=1, column=0, sticky=tk.W, pady=5)

    def _exec_doctor(self):
        self.log("Running QKViewMgr System Doctor...")
        self.log(f"Python: {sys.version.split()[0]} | OpenSSL: {f5functions.ssl.OPENSSL_VERSION}")
        creds_file = os.path.expanduser("~/.ihealth_credentials")
        self.log(f"Credentials File ~/.ihealth_credentials: {'Found' if os.path.isfile(creds_file) else 'Not Found'}")
        session = f5functions.get_secure_session(verify=True)
        for name, fqdn in [
            ("F5 Identity (Legacy)", f5functions.OKTA_IDENTITY_FQDN),
            ("F5 Identity (Auth0)", f5functions.AUTH0_IDENTITY_FQDN),
            ("F5 iHealth API", f5functions.IHEALTH_API_FQDN),
            ("MyF5 Support API", f5functions.MYF5_API_FQDN),
        ]:
            try:
                r = session.get(f"https://{fqdn}", timeout=5)
                self.log(f"✓ {name} ({fqdn}): Reachable (HTTP {r.status_code})")
            except (Exception, SystemExit) as e:
                err_msg = str(e)
                if not err_msg and hasattr(e, "code"):
                    err_msg = str(e.code)
                self.log(f"✗ {name} ({fqdn}): Failed ({err_msg})")
        self.log("Doctor check complete.")


def launch_gui():
    """Launch the native desktop GUI or provide instructions if Tkinter is missing."""
    if not TKINTER_AVAILABLE:
        print("\n" + "=" * 65)
        print("  NOTICE: Native Tkinter desktop library not found.")
        print("=" * 65)
        if _TKINTER_IMPORT_ERROR:
            print(f"Details: {_TKINTER_IMPORT_ERROR}\n")
        if sys.platform == "darwin":
            print("To enable native desktop GUI on macOS Homebrew Python:")
            print("    brew install python-tk@3.14")
        elif sys.platform.startswith("linux"):
            print("To enable native desktop GUI on Linux:")
            print("    sudo apt-get install python3-tk  (Debian/Ubuntu)")
            print("    sudo dnf install python3-tkinter (RHEL/Fedora)")
        print("\nLaunching interactive terminal wizard instead...")
        print("=" * 65 + "\n")
        try:
            from . import wizard
            wizard.main_menu()
        except ImportError:
            import wizard
            wizard.main_menu()
        return

    app = QKViewMgrApp()

    # Clean signal handling for SIGINT (Ctrl+C)
    def _handle_sigint(signum=None, frame=None):
        print("\nReceived Ctrl+C. Exiting QKView Manager GUI cleanly...", file=sys.stderr)
        try:
            app.destroy()
        except Exception:
            pass
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, _handle_sigint)
    except (ValueError, AttributeError):
        pass

    try:
        app.mainloop()
    except KeyboardInterrupt:
        _handle_sigint()


if __name__ == "__main__":
    launch_gui()
