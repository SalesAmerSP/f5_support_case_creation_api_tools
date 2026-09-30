# Network Egress & Firewall Guidelines

This document details the network egress requirements, endpoints, and cryptographic protocols required for `qkviewmgr` and standalone tools to communicate with F5 cloud services and target BIG-IP appliances.

---

## Authoritative F5 References

- **F5 Article K15202**: *IP addresses for F5 hosted services* (Updated Sep 4, 2026)
- **F5 Article K000162308**: *F5 Identity Platform Migration: Okta to Auth0*

---

## Required Outbound Network Egress Rules

Firewalls and enterprise proxy systems must permit outbound TCP traffic on **Port 443 (HTTPS)** to the following endpoints:

| Service / Destination | FQDN | IP Address / Range | Purpose & Notes |
| :--- | :--- | :--- | :--- |
| **F5 Identity Service (Auth0)** | `idp.identity.f5.com` | F5 Cloud Anycast | Modern OAuth2 token service for MyF5 and iHealth APIs |
| **F5 Identity Service (Legacy Okta)** | `identity.account.f5.com` | Okta / F5 Cloud | Legacy OAuth2 token service (`aus19gt5bu0jGw9Fi358`) |
| **F5 iHealth Upload API (Primary)** | `ihealth2-api.f5.com` | `185.56.152.6` | QKView multipart upload and analysis metadata queries |
| **F5 iHealth Upload API (Fallback)** | `ihealth-api.f5.com` | `185.56.152.6` | High-availability fallback endpoint if primary fails |
| **MyF5 Support Case API** | `support.apis.f5.com` | `35.199.173.84` | Case creation, comment updates, and metadata schema |
| **MyF5 Software Downloads API** | `api.software.downloads.f5.com` | AWS CloudFront / F5 XC Anycast | Catalog metadata, release versions, and signed download URLs (Effective Oct 2, 2026; no `k` param) |
| **Local BIG-IP Appliance** | `<appliance-ip-or-fqdn>` | Local Subnet / Mgmt | Target appliance running TMOS iControl REST |

---

## Network & DNS Maintenance Advisories

### 1. Friday, September 25, 2026: DNS Cutover to F5 Distributed Cloud (XC)
- **Time Window**: Friday, September 25, starting at 9:00 AM PT for 2 hours (09:00 - 11:00 AM PT / 16:00 - 18:00 UTC).
- **Scope & Actions**:
  - DNS change for `callhome.f5.com` and `api.f5.com` pointing to F5 Distributed Cloud (XC).
  - Wide IPs disabled for `callhome.f5.com` and `api.f5.com`, cutting over active traffic to XC.
  - Live production traffic routed to new Enterprise Service Delivery Platform (ESDP) for 1 hour (9:00 - 10:00 AM PT).
- **Service Availability**: Services **WILL be available** throughout the testing window.
- **Affected Services**:
  - `callhome.f5.com`: Used by BIG-IP, BIG-IQ, and all F5 appliances for phone-home and automated diagnostic telemetry.
  - `api.f5.com`: Used by MyF5 RSS Feed, BIG-IP, BIG-IQ, and appliance license verification.

### 2. Friday, October 2, 2026: Downloads API Base URL Migration
- **Change**: MyF5 Software Downloads API moves permanently to `https://api.software.downloads.f5.com`.
- **Action Required**: The legacy `k` query parameter is eliminated and will be rejected. All queries use OAuth2 Bearer token authentication only.
- **Built-in Resilience**: Tools (`download_browser`, `qkviewmgr downloads`) automatically use `api.software.downloads.f5.com` without `k`, and gracefully fall back during the transition window.

---

## Inbound Appliance Communication

The tool communicates with target BIG-IP appliances using standard **HTTPS (TCP 443)** via iControl REST:
- `/mgmt/tm/sys/ready`: Appliance readiness test
- `/mgmt/tm/util/qkview`: Asynchronous non-truncating QKView generation (`-s0`)
- `/mgmt/tm/util/bash`: Fallback execution
- `/mgmt/cm/autodeploy/qkview`: QKView listing, chunked download, and deletion

---

## Cryptographic Security: TLS 1.2+ & Modern PFS AEAD Ciphers

All HTTP sessions to F5 Cloud APIs are established through a custom `SecureTLSAdapter` enforcing:
1. **Minimum TLS Version**: TLSv1.2 (SSLv2, SSLv3, TLS 1.0, and TLS 1.1 are strictly rejected).
2. **Modern Perfect Forward Secrecy (PFS) & AEAD Ciphers**:
   - `ECDHE-ECDSA-AES128-GCM-SHA256`
   - `ECDHE-RSA-AES128-GCM-SHA256`
   - `ECDHE-ECDSA-AES256-GCM-SHA384`
   - `ECDHE-RSA-AES256-GCM-SHA384`
   - `ECDHE-ECDSA-CHACHA20-POLY1305`
   - `ECDHE-RSA-CHACHA20-POLY1305`
   - `DHE-RSA-AES128-GCM-SHA256`
   - `DHE-RSA-AES256-GCM-SHA384`
3. **CA Verification**: Mozilla's curated root CA bundle via `certifi`.

---

## Diagnosing Egress & Connectivity Issues

Use the built-in system doctor to audit connectivity from your host or jump box:

```bash
qkviewmgr doctor
```

If an endpoint fails:
1. Verify DNS resolution for the FQDN:
   ```bash
   dig +short idp.identity.f5.com
   dig +short support.apis.f5.com
   ```
2. Verify TCP reachability on port 443:
   ```bash
   nc -zv support.apis.f5.com 443
   ```
3. Check for corporate SSL inspection proxies that terminate TLS or alter certificates.
