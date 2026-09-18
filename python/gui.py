"""Native Desktop GUI for F5 QKView and Support Case Operations.

STRICT DESIGN MANDATE: NO WEB SERVICES.
This module uses native Python desktop GUI widgets (tkinter/ttk) exclusively.
It binds NO network ports, starts NO web/HTTP servers, and requires NO browser.
"""

import os
import sys
import threading
import queue

try:
    from . import f5functions
except ImportError:
    import f5functions


def launch_gui():
    """Launch the native desktop GUI or provide instructions if Tkinter is missing."""
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox, filedialog
    except (ImportError, ModuleNotFoundError) as err:
        print("\n" + "=" * 65)
        print("  NOTICE: Native Tkinter desktop library not found.")
        print("=" * 65)
        print(f"Details: {err}\n")
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

    # Build Native Tkinter Application
    class QKViewMgrApp(tk.Tk):
        def __init__(self):
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

            self.log("QKView Manager initialized. Desktop GUI ready.")

        def log(self, message):
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)

        def _run_threaded(self, target, *args):
            thread = threading.Thread(target=target, args=args, daemon=True)
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
            self.auto_user.insert(0, os.getenv("BIGIP_USER", "admin"))

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

            if not host or not pw:
                self.log("ERROR: Host and password are required.")
                return

            self.log(f"Starting Auto-Pilot for BIG-IP: {host}...")
            try:
                # 1. Connectivity test
                self.log(f"Connecting to BIG-IP {host}...")
                f5functions.bigip_connectivity_test(host, user, pw, verify=verify)
                self.log("✓ BIG-IP connection verified.")

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
                    self.log(f"✓ Upload to iHealth succeeded!")
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

            except Exception as e:
                self.log(f"Auto-Pilot encountered an error: {e}")

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

            ttk.Label(frame, text="Username:").grid(row=2, column=0, sticky=tk.W, pady=4)
            self.bigip_user = ttk.Entry(frame, width=35)
            self.bigip_user.grid(row=2, column=1, sticky=tk.W, pady=4)
            self.bigip_user.insert(0, "admin")

            ttk.Label(frame, text="Password:").grid(row=3, column=0, sticky=tk.W, pady=4)
            self.bigip_pw = ttk.Entry(frame, width=35, show="*")
            self.bigip_pw.grid(row=3, column=1, sticky=tk.W, pady=4)

            btn_box = ttk.Frame(frame)
            btn_box.grid(row=4, column=0, columnspan=2, pady=15, sticky=tk.W)

            ttk.Button(btn_box, text="Test Connection", command=lambda: self._run_threaded(self._test_bigip)).pack(side=tk.LEFT, padx=4)
            ttk.Button(btn_box, text="List QKViews", command=lambda: self._run_threaded(self._list_bigip_qkviews)).pack(side=tk.LEFT, padx=4)

        def _test_bigip(self):
            h, u, p = self.bigip_host.get().strip(), self.bigip_user.get().strip(), self.bigip_pw.get().strip()
            self.log(f"Testing BIG-IP connection to {h}...")
            try:
                f5functions.bigip_connectivity_test(h, u, p, verify=False)
                self.log(f"✓ Connection to {h} succeeded.")
            except Exception as e:
                self.log(f"✗ Connection failed: {e}")

        def _list_bigip_qkviews(self):
            h, u, p = self.bigip_host.get().strip(), self.bigip_user.get().strip(), self.bigip_pw.get().strip()
            self.log(f"Querying QKViews on {h}...")
            try:
                res = f5functions.bigip_list_qkviews(h, u, p, verify=False)
                items = res.get("items", [])
                self.log(f"Found {len(items)} QKView(s) on appliance:")
                for it in items:
                    self.log(f"  - {it.get('filename')} (ID: {it.get('id')})")
            except Exception as e:
                self.log(f"✗ Listing failed: {e}")

        # ---------------------------------------------------------------------
        # Tab 3: iHealth & Case Operations
        # ---------------------------------------------------------------------
        def _build_ihealth_tab(self, parent):
            frame = ttk.Frame(parent, padding=15)
            frame.pack(fill=tk.BOTH, expand=True)

            ttk.Label(frame, text="F5 iHealth & MyF5 Case Management", font=("Helvetica", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))

            ttk.Button(frame, text="List iHealth QKViews", command=lambda: self._run_threaded(self._list_ihealth)).grid(row=1, column=0, sticky=tk.W, pady=5)
            ttk.Button(frame, text="List MyF5 Support Cases", command=lambda: self._run_threaded(self._list_cases)).grid(row=2, column=0, sticky=tk.W, pady=5)

        def _list_ihealth(self):
            self.log("Authenticating to F5 iHealth...")
            try:
                cid, csec = f5functions.resolve_ihealth_credentials()
                token = f5functions.myf5_authenticate(f5functions.IHEALTH_APP_ID, cid, csec, scope="ihealth")
                self.log("✓ Authenticated. Querying QKViews...")
                res = f5functions.ihealth_list_qkview_ids(token)
                qvs = res.get("qkviews", [])
                self.log(f"Total iHealth QKViews found: {len(qvs)}")
                for qv in qvs:
                    self.log(f"  QKView ID: {qv.get('id')} | Status: {qv.get('status')} | File: {qv.get('filename')}")
            except Exception as e:
                self.log(f"✗ iHealth query failed: {e}")

        def _list_cases(self):
            self.log("Authenticating to MyF5 Case API...")
            try:
                cid, csec = f5functions.resolve_ihealth_credentials()
                token = f5functions.myf5_authenticate(f5functions.MYF5_APP_ID, cid, csec, scope="myf5_scope")
                self.log("✓ Authenticated. Querying cases...")
                cases = f5functions.myf5_list_support_cases(token)
                self.log(f"Found support cases: {cases}")
            except Exception as e:
                self.log(f"✗ Case listing failed: {e}")

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
                except Exception as e:
                    self.log(f"✗ {name} ({fqdn}): Failed ({e})")
            self.log("Doctor check complete.")

    app = QKViewMgrApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
