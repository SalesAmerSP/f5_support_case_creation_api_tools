# F5 Automation Developer Examples & Workflow Integration Scripts

This directory contains standalone, single-purpose Python scripts demonstrating how to interact directly with F5 BIG-IP iControl REST, F5 iHealth, and MyF5 Support Case APIs.

These scripts are designed for:
1. **Direct execution**: Run them as standalone utilities from the command line.
2. **Integration blueprints**: Copy and adapt individual functions and patterns into your enterprise automation pipelines (e.g., Ansible, Jenkins, GitHub Actions, custom monitoring daemons).

---

## Zero-Secret Credentials

All example scripts inherit **Zero-Secret CLI Security**:
- Passwords and client secrets can be entered interactively via masked prompt (`getpass`).
- Alternatively, export environment variables:
  ```bash
  export BIGIP_PASSWORD="YourPassword"
  export F5_CLIENT_ID="YourClientID"
  export F5_CLIENT_SECRET="YourClientSecret"
  ```
- Or configure `~/.ihealth_credentials` (mode `0600`).

---

## Directory Index

### 1. BIG-IP Appliance Management (`bigip_*.py`)
- [`bigip_connectivity_test.py`](bigip_connectivity_test.py): Validates iControl REST connectivity and system readiness against `/mgmt/tm/sys/ready`.
- [`bigip_generate_qkview.py`](bigip_generate_qkview.py): Triggers QKView archive generation on the remote appliance with polling.
- [`bigip_list_qkviews.py`](bigip_list_qkviews.py): Queries the appliance for all completed QKView diagnostic archives.
- [`bigip_download_qkview.py`](bigip_download_qkview.py): Streams chunked download of remote QKView to local disk with a progress meter.
- [`bigip_delete_qkview.py`](bigip_delete_qkview.py): Removes remote QKView files from the appliance to free storage space.

### 2. iHealth Analysis & QKView Upload (`ihealth_*.py`)
- [`ihealth_connectivity_test.py`](ihealth_connectivity_test.py): Authenticates with F5 Identity Services and validates access to the iHealth analyzer API.
- [`ihealth_list_qkviews.py`](ihealth_list_qkviews.py): Lists all QKViews uploaded under the account, showing ID, hostname, date, and analysis URL.
- [`ihealth_upload_qkview.py`](ihealth_upload_qkview.py): Uploads a local QKView file to iHealth with streaming chunked transfer and optional support case association.

### 3. MyF5 Support Case Management (`myf5_*.py`)
- [`myf5_connectivity_test.py`](myf5_connectivity_test.py): Validates authentication credentials against F5 Identity Services (`myf5_scope`).
- [`myf5_retrieve_case_creation_metadata.py`](myf5_retrieve_case_creation_metadata.py): Retrieves valid product families, versions, severities, and schemas from MyF5.
- [`myf5_create_inputs_file.py`](myf5_create_inputs_file.py): Interactive CLI wizard that queries metadata schema to create a valid case JSON file.
- [`myf5_create_new_case.py`](myf5_create_new_case.py): Submits a case JSON payload to MyF5 and retrieves the new case number and portal link.
- [`myf5_list_existing_cases.py`](myf5_list_existing_cases.py): Lists active (or all) support cases opened under the account.
- [`myf5_add_comments_to_existing_case.py`](myf5_add_comments_to_existing_case.py): Appends text comments, diagnostics, or notes to an existing support ticket.

---

## Example Usage

### Test BIG-IP Connectivity
```bash
python3 examples/bigip_connectivity_test.py --host 18.210.113.51 --no-ssl-verify
```

### List iHealth Diagnostics
```bash
python3 examples/ihealth_list_qkviews.py
```

### List Support Cases
```bash
python3 examples/myf5_list_existing_cases.py
```
