"""
SPECTRE Test Suite — Burp Bridge XML Parsing Tests
Tests for agents.web_audit_bridge.parse_burp_xml

Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5
"""

import base64
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from agents.web_audit_bridge import parse_burp_xml


# ── Helper ────────────────────────────────────────────────────────────────────

def make_burp_xml(items):
    """Build minimal Burp Suite XML from a list of item dicts.

    Each dict supports keys:
        url          (str)  default "http://example.com"
        method       (str)  default "GET"
        request      (str)  raw request string; base64-encoded when request_b64=True
        response     (str)  raw response string; base64-encoded when response_b64=True
        request_b64  (bool) default False — write request as base64
        response_b64 (bool) default False — write response as base64
    """
    parts = ['<?xml version="1.0"?><items>']
    for item in items:
        req = item.get("request", "GET / HTTP/1.1")
        res = item.get("response", "HTTP/1.1 200 OK")
        req_b64 = item.get("request_b64", False)
        res_b64 = item.get("response_b64", False)
        req_attr = ' base64="true"' if req_b64 else ''
        res_attr = ' base64="true"' if res_b64 else ''
        if req_b64:
            req = base64.b64encode(req.encode()).decode()
        if res_b64:
            res = base64.b64encode(res.encode()).decode()
        parts.append(
            f'<item>'
            f'<url>{item.get("url", "http://example.com")}</url>'
            f'<method>{item.get("method", "GET")}</method>'
            f'<request{req_attr}>{req}</request>'
            f'<response{res_attr}>{res}</response>'
            f'</item>'
        )
    parts.append('</items>')
    return '\n'.join(parts)


# ── TestParseBurpXML ──────────────────────────────────────────────────────────

class TestParseBurpXML:
    """Unit tests for parse_burp_xml()."""

    def test_parse_n_items_returns_n_dicts(self, tmp_py_file):
        """XML with N items → list of exactly N dicts, each with required keys.

        Validates: Requirement 7.1
        """
        items_data = [
            {"url": "http://example.com/a", "method": "GET"},
            {"url": "http://example.com/b", "method": "POST"},
            {"url": "http://example.com/c", "method": "PUT"},
        ]
        xml_content = make_burp_xml(items_data)
        path = tmp_py_file(xml_content, suffix=".xml")

        result = parse_burp_xml(str(path))

        assert len(result) == 3
        for entry in result:
            assert "url" in entry
            assert "method" in entry
            assert "request" in entry
            assert "response" in entry

    def test_parse_base64_decodes_correctly(self, tmp_py_file):
        """Request with base64="true" is decoded back to the original string.

        Validates: Requirement 7.2
        """
        original_request = "GET /secret HTTP/1.1"
        xml_content = make_burp_xml([
            {"request": original_request, "request_b64": True}
        ])
        path = tmp_py_file(xml_content, suffix=".xml")

        result = parse_burp_xml(str(path))

        assert len(result) == 1
        assert result[0]["request"] == original_request

    def test_parse_invalid_utf8_base64_uses_replace(self, tmp_py_file):
        """Base64-encoded bytes with invalid UTF-8 are decoded with replacement chars.

        No exception should be raised; the result should contain a string.

        Validates: Requirement 7.3
        """
        # b'\xff\xfe' is not valid UTF-8
        invalid_utf8_b64 = base64.b64encode(b'\xff\xfe').decode()
        xml_content = (
            '<?xml version="1.0"?><items>'
            '<item>'
            '<url>http://example.com</url>'
            '<method>GET</method>'
            f'<request base64="true">{invalid_utf8_b64}</request>'
            '<response>HTTP/1.1 200 OK</response>'
            '</item>'
            '</items>'
        )
        path = tmp_py_file(xml_content, suffix=".xml")

        # Should not raise
        result = parse_burp_xml(str(path))

        assert len(result) == 1
        assert isinstance(result[0]["request"], str)

    def test_parse_missing_request_tag_returns_empty_string(self, tmp_py_file):
        """Items without a <request> element yield an empty string for 'request'.

        Validates: Requirement 7.4
        """
        xml_content = (
            '<?xml version="1.0"?><items>'
            '<item>'
            '<url>http://example.com</url>'
            '<method>GET</method>'
            '<response>HTTP/1.1 200 OK</response>'
            '</item>'
            '</items>'
        )
        path = tmp_py_file(xml_content, suffix=".xml")

        result = parse_burp_xml(str(path))

        assert len(result) == 1
        assert result[0]["request"] == ""

    def test_parse_nonexistent_file_raises(self):
        """Calling parse_burp_xml on a non-existent path raises an exception.

        ET.parse raises FileNotFoundError (or OSError) for missing files.

        Validates: Requirement 7.5
        """
        with pytest.raises(Exception):
            parse_burp_xml("/nonexistent/path/to/file.xml")
