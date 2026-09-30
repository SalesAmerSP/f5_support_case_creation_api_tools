"""Unit tests for download_browser tool."""

import argparse
import io
import json
import os
import sys
from unittest import mock
import pytest

_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import download_browser
import f5functions


# ---------------------------------------------------------------------------
# Utility Tests
# ---------------------------------------------------------------------------

def test_format_bytes():
    assert download_browser.format_bytes(500) == "500.00 B"
    assert download_browser.format_bytes(1024 * 1024) == "1.00 MB"
    assert download_browser.format_bytes(2475470848) == "2.31 GB"
    assert download_browser.format_bytes("invalid") == "invalid"


def test_print_banner(capsys):
    download_browser.print_banner()
    captured = capsys.readouterr().out
    assert "September 24, 2026" in captured
    assert "October 2, 2026" in captured
    assert "September 25, 2026" in captured


# ---------------------------------------------------------------------------
# Command Tests
# ---------------------------------------------------------------------------

@mock.patch("f5functions.myf5_get_downloads_metadata")
def test_cmd_families(mock_meta, capsys):
    mock_resp = mock.MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "data": {
            "productFamilies": [
                {"name": "BIG-IP", "productLines": [{"name": "line1"}]},
                {"name": "NGINX", "productLines": [{"name": "line2"}, {"name": "line3"}]}
            ]
        }
    }
    mock_meta.return_value = mock_resp

    args = argparse.Namespace(json=False, api_fqdn=f5functions.MYF5_DOWNLOADS_API_FQDN)
    rc = download_browser.cmd_families(args, token="fake-token")
    assert rc == 0
    out = capsys.readouterr().out
    assert "BIG-IP" in out
    assert "NGINX" in out

    # Test JSON output
    args.json = True
    rc = download_browser.cmd_families(args, token="fake-token")
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) == 2
    assert data[0]["name"] == "BIG-IP"
    assert data[0]["lines_count"] == 1


@mock.patch("f5functions.myf5_get_downloads_metadata")
def test_cmd_lines(mock_meta, capsys):
    mock_resp = mock.MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "data": {
            "productFamilies": [
                {
                    "name": "BIG-IP",
                    "productLines": [
                        {"name": "big-ip_v16.x", "displayName": "BIG-IP v16.x"},
                        {"name": "big-ip_v17.x", "displayName": "BIG-IP v17.x"}
                    ]
                }
            ]
        }
    }
    mock_meta.return_value = mock_resp

    args = argparse.Namespace(family="BIG-IP", filter="v16", json=False, api_fqdn=f5functions.MYF5_DOWNLOADS_API_FQDN)
    rc = download_browser.cmd_lines(args, token="fake-token")
    assert rc == 0
    out = capsys.readouterr().out
    assert "big-ip_v16.x" in out
    assert "big-ip_v17.x" not in out


@mock.patch("f5functions.myf5_get_product_versions")
def test_cmd_versions(mock_ver, capsys):
    mock_resp = mock.MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "data": {
            "versions": [
                {
                    "version": "16.1.6",
                    "releaseDate": "2026-07-29T17:42:04.000Z",
                    "containers": [{"name": "16.1.6", "files": [{"filename": "f1.iso"}]}]
                }
            ]
        }
    }
    mock_ver.return_value = mock_resp

    args = argparse.Namespace(family="BIG-IP", line="big-ip_v16.x", filter=None, json=False, api_fqdn=f5functions.MYF5_DOWNLOADS_API_FQDN)
    rc = download_browser.cmd_versions(args, token="fake-token")
    assert rc == 0
    out = capsys.readouterr().out
    assert "16.1.6" in out
    assert "2026-07-29" in out


@mock.patch("f5functions.myf5_get_product_versions")
def test_cmd_files(mock_ver, capsys):
    mock_resp = mock.MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "data": {
            "versions": [
                {
                    "version": "16.1.6",
                    "containers": [
                        {
                            "name": "16.1.6",
                            "files": [
                                {
                                    "filename": "BIGIP-16.1.6-0.0.12.iso",
                                    "bytes": 2475470848,
                                    "description": "Full base image"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }
    mock_ver.return_value = mock_resp

    args = argparse.Namespace(family="BIG-IP", line="big-ip_v16.x", version="16.1.6", container="16.1.6", filter=None, json=False, api_fqdn=f5functions.MYF5_DOWNLOADS_API_FQDN)
    rc = download_browser.cmd_files(args, token="fake-token")
    assert rc == 0
    out = capsys.readouterr().out
    assert "BIGIP-16.1.6-0.0.12.iso" in out
    assert "2.31 GB" in out


@mock.patch("f5functions.myf5_get_download_file_links")
def test_cmd_links(mock_links, capsys):
    mock_resp = mock.MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "data": {
            "bytes": 2475470848,
            "sha256": "abcdef1234567890",
            "md5": "md5hash123",
            "downloadLinks": [
                {"region": "USA - EAST COAST", "href": "https://s3.amazonaws.com/f5/bigip.iso"}
            ]
        }
    }
    mock_links.return_value = mock_resp

    args = argparse.Namespace(
        family="BIG-IP", line="big-ip_v16.x", version="16.1.6", container="16.1.6",
        file="BIGIP-16.1.6-0.0.12.iso", language="english", json=False,
        api_fqdn=f5functions.MYF5_DOWNLOADS_API_FQDN
    )
    rc = download_browser.cmd_links(args, token="fake-token")
    assert rc == 0
    out = capsys.readouterr().out
    assert "abcdef1234567890" in out
    assert "USA - EAST COAST" in out


@mock.patch("f5functions.myf5_download_file")
@mock.patch("f5functions.myf5_get_download_file_links")
def test_cmd_download(mock_links, mock_dl):
    mock_resp = mock.MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "data": {
            "bytes": 2475470848,
            "sha256": "abcdef1234567890",
            "downloadLinks": [
                {"region": "USA - EAST COAST", "href": "https://s3.amazonaws.com/f5/bigip.iso"}
            ]
        }
    }
    mock_links.return_value = mock_resp
    mock_dl.return_value = "/tmp/BIGIP-16.1.6-0.0.12.iso"

    args = argparse.Namespace(
        family="BIG-IP", line="big-ip_v16.x", version="16.1.6", container="16.1.6",
        file="BIGIP-16.1.6-0.0.12.iso", output="/tmp/BIGIP-16.1.6-0.0.12.iso",
        dest_dir=".", region="USA", no_verify=False, language="english",
        api_fqdn=f5functions.MYF5_DOWNLOADS_API_FQDN
    )
    rc = download_browser.cmd_download(args, token="fake-token")
    assert rc == 0
    mock_dl.assert_called_once_with(
        "https://s3.amazonaws.com/f5/bigip.iso",
        "/tmp/BIGIP-16.1.6-0.0.12.iso",
        expected_checksum="abcdef1234567890",
        checksum_algo="sha256"
    )


@mock.patch("f5functions.myf5_download_file")
def test_cmd_url(mock_dl):
    mock_dl.return_value = "/tmp/image.iso"
    args = argparse.Namespace(
        url="https://s3.amazonaws.com/my-f5/image.iso?presigned=true",
        output="/tmp/image.iso",
        checksum="hash123",
        algo="sha256"
    )
    rc = download_browser.cmd_url(args)
    assert rc == 0
    mock_dl.assert_called_once_with(
        "https://s3.amazonaws.com/my-f5/image.iso?presigned=true",
        "/tmp/image.iso",
        expected_checksum="hash123",
        checksum_algo="sha256"
    )


@mock.patch("f5functions.myf5_get_downloads_metadata")
@mock.patch("f5functions.myf5_authenticate")
@mock.patch("f5functions.resolve_ihealth_credentials")
def test_cmd_status(mock_creds, mock_auth, mock_meta, capsys):
    mock_creds.return_value = ("test-client-id", "test-secret")
    mock_auth.return_value = "token-123"
    mock_resp = mock.MagicMock(status_code=200)
    mock_resp.json.return_value = {"data": {"productFamilies": [{"name": "BIG-IP"}]}}
    mock_meta.return_value = mock_resp

    args = argparse.Namespace()
    rc = download_browser.cmd_status(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "September 24, 2026" in out
    assert "September 25, 2026" in out
    assert "October 2, 2026" in out
    assert "[PASS]" in out


@mock.patch("f5functions.myf5_get_downloads_metadata")
@mock.patch("f5functions.myf5_authenticate")
@mock.patch("f5functions.resolve_ihealth_credentials")
def test_browse_interactive_quit(mock_creds, mock_auth, mock_meta, monkeypatch):
    mock_creds.return_value = ("cid", "csec")
    mock_auth.return_value = "tok"
    mock_resp = mock.MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "data": {
            "productFamilies": [{"name": "BIG-IP", "productLines": []}]
        }
    }
    mock_meta.return_value = mock_resp

    # Simulate user typing 'q' to quit immediately at family menu
    monkeypatch.setattr("builtins.input", lambda prompt: "q")

    args = argparse.Namespace(api_fqdn=f5functions.MYF5_DOWNLOADS_API_FQDN)
    rc = download_browser.browse_interactive(args)
    assert rc == 0


def test_download_browser_main_prohibits_client_secret():
    """Verify download_browser rejects --client-secret with exit code 2."""
    with mock.patch("sys.argv", ["download_browser", "--client-secret", "supersecret"]):
        with pytest.raises(SystemExit) as exc_info:
            download_browser.main()
        assert exc_info.value.code == 2


def test_download_browser_main_prohibits_password():
    """Verify download_browser rejects --password with exit code 2."""
    with mock.patch("sys.argv", ["download_browser", "--password", "secretpw"]):
        with pytest.raises(SystemExit) as exc_info:
            download_browser.main()
        assert exc_info.value.code == 2


@mock.patch("f5functions.myf5_authenticate", return_value="tok_123")
@mock.patch("f5functions.resolve_ihealth_credentials", return_value=("cid", "csec"))
def test_download_browser_get_token(mock_creds, mock_auth):
    """Verify get_token resolves credentials via resolve_ihealth_credentials."""
    args = argparse.Namespace(auth_fqdn="identity.api.f5.com", profile="prod")
    token = download_browser.get_token(args)
    assert token == "tok_123"
    mock_creds.assert_called_once_with(client_id=None, client_secret=None, profile="prod")
    mock_auth.assert_called_once_with(
        f5functions.MYF5_APP_ID, "cid", "csec", scope="myf5_scope", auth_fqdn="identity.api.f5.com"
    )
