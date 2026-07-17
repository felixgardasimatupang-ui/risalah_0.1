"""Tests for risalah/email_utils.py — send_docx_email with mock SMTP."""

import os
from unittest.mock import MagicMock, patch

import pytest

from risalah.email_utils import send_docx_email


class TestSendDocxEmail:
    def test_smtp_not_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            ok, msg = send_docx_email("test@example.com", "Sub", "Body", b"docx data")
        assert not ok
        assert "SMTP not configured" in msg

    def test_send_success(self):
        mock_server = MagicMock()
        mock_server.__enter__.return_value = mock_server
        mock_ctx = MagicMock()

        with (
            patch.dict(
                os.environ,
                {
                    "SMTP_HOST": "smtp.example.com",
                    "SMTP_PORT": "587",
                    "SMTP_USER": "user@example.com",
                    "SMTP_PASS": "secret",
                },
            ),
            patch("risalah.email_utils.smtplib.SMTP", return_value=mock_server),
            patch("risalah.email_utils.ssl.create_default_context", return_value=mock_ctx),
        ):
            ok, msg = send_docx_email(
                "to@example.com",
                "Test Subject",
                "Test body",
                b"fake_docx_bytes",
                filename="laporan.docx",
            )

        assert ok
        assert "Email terkirim" in msg
        mock_server.starttls.assert_called_once_with(context=mock_ctx)
        mock_server.login.assert_called_once_with("user@example.com", "secret")
        mock_server.send_message.assert_called_once()
        sent = mock_server.send_message.call_args[0][0]
        assert sent["To"] == "to@example.com"
        assert sent["Subject"] == "Test Subject"

    def test_smtp_error_returns_false(self):
        with (
            patch.dict(
                os.environ,
                {
                    "SMTP_HOST": "smtp.example.com",
                    "SMTP_PORT": "587",
                    "SMTP_USER": "user",
                    "SMTP_PASS": "pass",
                },
            ),
            patch("risalah.email_utils.smtplib.SMTP", side_effect=ConnectionError("refused")),
        ):
            ok, msg = send_docx_email("to@example.com", "S", "B", b"data")

        assert not ok
        assert "refused" in msg

    def test_from_email_defaults_to_user(self):
        mock_server = MagicMock()
        mock_server.__enter__.return_value = mock_server

        with (
            patch.dict(
                os.environ,
                {
                    "SMTP_HOST": "smtp.example.com",
                    "SMTP_PORT": "587",
                    "SMTP_USER": "sender@example.com",
                    "SMTP_PASS": "x",
                },
            ),
            patch("risalah.email_utils.smtplib.SMTP", return_value=mock_server),
            patch("risalah.email_utils.ssl.create_default_context"),
        ):
            send_docx_email("to@example.com", "S", "B", b"data")

        sent = mock_server.send_message.call_args[0][0]
        assert sent["From"] == "sender@example.com"

    def test_custom_filename_in_attachment(self):
        mock_server = MagicMock()
        mock_server.__enter__.return_value = mock_server

        with (
            patch.dict(
                os.environ,
                {"SMTP_HOST": "smtp.example.com", "SMTP_PORT": "587", "SMTP_USER": "u", "SMTP_PASS": "p"},
            ),
            patch("risalah.email_utils.smtplib.SMTP", return_value=mock_server),
            patch("risalah.email_utils.ssl.create_default_context"),
        ):
            send_docx_email("t@t.com", "S", "B", b"x", filename="rapat.docx")

        sent = mock_server.send_message.call_args[0][0]
        payload = str(sent)
        assert 'filename="rapat.docx"' in payload
