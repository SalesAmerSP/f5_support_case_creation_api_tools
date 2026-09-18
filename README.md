# F5 Support Case Creation & Automation API Tools

Generates proactive and reactive support cases using MyF5 and iHealth; includes automated BIG-IP QKView generation, chunked retrieval, deletion, and upload to iHealth.

---

## Table of Contents

- [Overview](#overview)
- [Support Disclaimer](#support-disclaimer)
- [Prerequisites & Network Requirements](#prerequisites--network-requirements)
  - [API Credentials](#api-credentials)
  - [Firewall & Egress Guidelines (K15202 & K000162308)](#firewall--egress-guidelines-k15202--k000162308)
- [Installation & Environment Setup](#installation--environment-setup)
- [Toolset Reference](#toolset-reference)
  - [BIG-IP Tools](#big-ip-tools)
  - [iHealth Tools](#ihealth-tools)
  - [MyF5 Tools](#myf5-tools)
- [Workflow & Usage Guide](#workflow--usage-guide)
- [Running Automated Tests](#running-automated-tests)

---

## Overview

This toolset automates the complete lifecycle of opening F5 support cases:
1. **Verify Connectivity**: Validate access to BIG-IP devices, iHealth, and MyF5 APIs.
2. **Collect Diagnostics**: Generate full or standard QKViews on BIG-IP devices via iControl REST, stream them locally, and clean up remote disk space.
3. **Upload to iHealth**: Securely upload QKViews to F5 iHealth for automated analysis and case linking.
4. **Create & Manage Cases**: Fetch dynamic schema metadata, prepare validated JSON case payloads, submit new support tickets to MyF5, and append comments or updates.

Compatible with **Python 3.10, 3.11, 3.12, 3.13, and 3.14**.

---

## Support Disclaimer

> [!CAUTION]
> This is a community automation tool and is **not** an official F5 product. Support is not provided by F5 Technical Support. Usage is at your own risk. Please report bugs or submit enhancements via [GitHub Issues](https://github.com/f5devcentral/myf5_proactive_case_generation/issues). The MyF5 API, iHealth API, and iControl REST endpoints are subject to change.

---

## Prerequisites & Network Requirements

### API Credentials

- **MyF5 Client ID & Secret**: Generated from your MyF5 account profile.
- **iHealth Client ID & Secret**: Generated from [iHealth](https://ihealth.f5.com) Settings under API Tokens.
- **BIG-IP Credentials**: Administrative username and password with access to iControl REST.
- **Device Information**: Valid hostname/IP, TMOS version, and a serial number covered under an active F5 service contract.

### Firewall & Egress Guidelines (K15202 & K000162308)

Per **F5 Knowledge Base Article K15202** (*IP addresses for F5 hosted services*) and **K000162308** (*F5 Identity Platform Migration: Okta to Auth0*):

- **Authentication Endpoints**:
  - **Auth0 IDP** (Modern): `idp.identity.f5.com`
    - Primary Egress IPs: `34.223.200.228`, `44.253.79.202`, `35.83.64.18`, `44.254.167.76`
    - Failover Egress IPs: `100.30.52.61`, `98.95.15.62`, `44.214.121.49`, `98.89.114.213`, `54.211.123.113`
  - **Okta IDP** (Legacy): `identity.account.f5.com`
    - Egress IPs: `13.35.121.0/24`, `18.66.248.0/24`, `198.2.128.0/18`
- **Case Management API**: `support.apis.f5.com` (`35.199.173.84`)
- **iHealth Upload API**: `ihealth2-api.f5.com` and `ihealth-api.f5.com` (`185.56.152.6`)

> [!NOTE]
> All CLI scripts support the `--auth-fqdn` and `--auth-url` options. By default, legacy authentication uses `identity.account.f5.com`. For accounts migrated to Auth0, pass `--auth-fqdn idp.identity.f5.com`.

---

## Installation & Environment Setup

### 1. Clone the Repository
```bash
git clone https://github.com/f5devcentral/myf5_proactive_case_generation.git
cd myf5_support_case_creation_api_tools
```

### 2. Create and Activate a Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
Install dependencies directly from `requirements.txt` or via standard editable package install:
```bash
pip install -r python/requirements.txt
# Or editable package install:
pip install -e .
```

---

## Toolset Reference

### BIG-IP Tools

All BIG-IP tools accept the `--no-ssl-verify` flag to disable TLS certificate verification when connecting to devices using internal or self-signed certificates.

- **`bigip_connectivity_test.py`**  
  Checks device availability and tests iControl REST reachability against `/mgmt/tm/sys/ready`.
  ```bash
  python3 python/bigip_connectivity_test.py --host 192.0.2.1 --username admin --password secret [--no-ssl-verify]
  ```

- **`bigip_generate_qkview.py`**  
  Triggers generation of a QKView archive on the target BIG-IP (`/shared/tmp/qkviews`).
  ```bash
  python3 python/bigip_generate_qkview.py --host 192.0.2.1 --username admin --password secret \
      --filename my_device.qkview [--skip-wait] [--wait-interval 60] [--no-ssl-verify]
  ```

- **`bigip_list_qkviews.py`**  
  Lists all completed QKView archives present on the BIG-IP device.
  ```bash
  python3 python/bigip_list_qkviews.py --host 192.0.2.1 --username admin --password secret [--no-ssl-verify]
  ```

- **`bigip_download_qkview.py`**  
  Downloads a remote QKView to the local filesystem using chunked streaming with a progress bar.
  ```bash
  python3 python/bigip_download_qkview.py --host 192.0.2.1 --username admin --password secret \
      --filename my_device.qkview [--no-ssl-verify]
  ```

- **`bigip_delete_qkview.py`**  
  Removes a generated QKView from the BIG-IP to free disk space.
  ```bash
  python3 python/bigip_delete_qkview.py --host 192.0.2.1 --username admin --password secret \
      --filename my_device.qkview [--no-ssl-verify]
  ```

---

### iHealth Tools

- **`ihealth_connectivity_test.py`**  
  Authenticates with F5 Identity Services and validates access to the iHealth analyzer API.
  ```bash
  python3 python/ihealth_connectivity_test.py --client-id <id> --client-secret <secret> \
      [--auth-fqdn idp.identity.f5.com] [--api-fqdn ihealth2-api.f5.com]
  ```

- **`ihealth_list_qkviews.py`**  
  Displays diagnostic summaries and web URLs for all QKViews uploaded under the account.
  ```bash
  python3 python/ihealth_list_qkviews.py --client-id <id> --client-secret <secret>
  ```

- **`ihealth_upload_qkview.py`**  
  Uploads a local QKView file to iHealth. Supports automatic endpoint fallback and case linking.
  ```bash
  python3 python/ihealth_upload_qkview.py --client-id <id> --client-secret <secret> \
      --filename my_device.qkview [--support-case C1234567]
  ```

---

### MyF5 Tools

- **`myf5_connectivity_test.py`**  
  Validates authentication credentials against F5 Identity Services (`myf5_scope`).
  ```bash
  python3 python/myf5_connectivity_test.py --client-id <id> --client-secret <secret> \
      [--auth-fqdn idp.identity.f5.com]
  ```

- **`myf5_retrieve_case_creation_metadata.py`**  
  Retrieves valid product families, versions, severities, and contact methods from MyF5.
  ```bash
  python3 python/myf5_retrieve_case_creation_metadata.py --client-id <id> --client-secret <secret> \
      --output-file metadata.json [--output-to-stdout]
  ```

- **`myf5_create_inputs_file.py`**  
  Interactive wizard that queries the MyF5 metadata schema to guide creation of a valid case JSON file.
  ```bash
  python3 python/myf5_create_inputs_file.py --client-id <id> --client-secret <secret> \
      --output-file case_inputs.json
  ```

- **`myf5_create_new_case.py`**  
  Submits a case payload to MyF5, returning the created support case number and web portal link.
  ```bash
  python3 python/myf5_create_new_case.py --client-id <id> --client-secret <secret> \
      --inputs-file case_inputs.json
  ```

- **`myf5_list_existing_cases.py`**  
  Lists active support cases (or all cases including closed).
  ```bash
  python3 python/myf5_list_existing_cases.py --client-id <id> --client-secret <secret> [--show-closed]
  ```

- **`myf5_add_comments_to_existing_case.py`**  
  Appends text notes or updates to an open support case.
  ```bash
  python3 python/myf5_add_comments_to_existing_case.py --client-id <id> --client-secret <secret> \
      --case-number C1234567 --comment-text-file notes.txt
  ```

---

## Workflow & Usage Guide

```
[BIG-IP]                      [Local Machine]                   [F5 Cloud APIs]
   |                                 |                                 |
   |<-- Generate QKView -------------|                                 |
   |--- Download QKView ------------>|                                 |
   |<-- Delete remote QKView --------|                                 |
   |                                 |--- Get Schema Metadata -------->|
   |                                 |    (myf5_create_inputs_file)    |
   |                                 |--- Submit Case ---------------->| (MyF5 Case Created)
   |                                 |--- Upload QKView & Link Case -->| (iHealth Analyzer)
```

1. **Verify Connectivity**:
   ```bash
   python3 python/bigip_connectivity_test.py --host 192.0.2.1 --username admin --password secret --no-ssl-verify
   python3 python/myf5_connectivity_test.py --client-id <id> --client-secret <secret>
   python3 python/ihealth_connectivity_test.py --client-id <id> --client-secret <secret>
   ```
2. **Collect QKView from BIG-IP**:
   ```bash
   python3 python/bigip_generate_qkview.py --host 192.0.2.1 --username admin --password secret --filename host1.qkview --no-ssl-verify
   python3 python/bigip_download_qkview.py --host 192.0.2.1 --username admin --password secret --filename host1.qkview --no-ssl-verify
   python3 python/bigip_delete_qkview.py --host 192.0.2.1 --username admin --password secret --filename host1.qkview --no-ssl-verify
   ```
3. **Build Case Inputs & Create Support Ticket**:
   ```bash
   python3 python/myf5_create_inputs_file.py --client-id <id> --client-secret <secret> --output-file case_inputs.json
   python3 python/myf5_create_new_case.py --client-id <id> --client-secret <secret> --inputs-file case_inputs.json
   ```
4. **Upload QKView to iHealth Associated with the Case**:
   ```bash
   python3 python/ihealth_upload_qkview.py --client-id <id> --client-secret <secret> --filename host1.qkview --support-case C1234567
   ```
5. **(Optional) Add Subsequent Notes or Updates**:
   ```bash
   python3 python/myf5_add_comments_to_existing_case.py --client-id <id> --client-secret <secret> --case-number C1234567 --comment-text-file notes.txt
   ```

---

## Running Automated Tests

A comprehensive unit test suite is included under `tests/` covering argument parsers, SSL flag validation, Okta and Auth0 authentication flows, K000162308 error diagnostics, iHealth fallback logic, and API call payloads.

To run tests using Python's built-in `unittest` runner:
```bash
python3 -m unittest discover -s tests -v
```

If `pytest` is installed in your virtual environment:
```bash
pytest -v
```