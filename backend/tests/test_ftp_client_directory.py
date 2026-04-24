"""Tests for FTP client remote directory path handling."""

from app.clients.ftp_client import CNCFtpClient


def test_directory_parts_root():
    assert CNCFtpClient._directory_parts("/") == []


def test_directory_parts_nested_path():
    assert CNCFtpClient._directory_parts("/PROGRAM/JOB1") == ["PROGRAM", "JOB1"]


def test_directory_parts_normalizes_empty_segments():
    assert CNCFtpClient._directory_parts("//PROGRAM///JOB1/") == ["PROGRAM", "JOB1"]
