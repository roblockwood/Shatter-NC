"""Tests for local upload candidate collection nested folder behavior."""

from types import SimpleNamespace

from app.services.ftp_sync_service import FtpSyncService


def _make_base_config(tmp_path, control_type: str):
    return SimpleNamespace(
        source_folder=str(tmp_path),
        remote_folder="/PROGRAM",
        include_pattern="*.NC",
        exclude_patterns="",
        control_type=control_type,
        strict_brother_naming=True,
        require_onumber_filename=True,
    )


def test_collect_candidates_c00_rejects_nested_directories(tmp_path):
    service = FtpSyncService(websocket_manager=None)
    nested = tmp_path / "SUB" / "O2000.NC"
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("O2000\n")

    config = _make_base_config(tmp_path, "C00")
    files, excluded = service._collect_candidate_files(config, relative_paths=None)

    assert files == []
    assert len(excluded) == 1
    assert excluded[0][0] == "SUB/O2000.NC"
    assert excluded[0][3] == "nested_directories_not_supported"


def test_collect_candidates_d00_allows_two_levels_rejects_deeper(tmp_path):
    service = FtpSyncService(websocket_manager=None)

    allowed = tmp_path / "A" / "B" / "O2000.NC"
    allowed.parent.mkdir(parents=True, exist_ok=True)
    allowed.write_text("O2000\n")

    too_deep = tmp_path / "A" / "B" / "C" / "O2001.NC"
    too_deep.parent.mkdir(parents=True, exist_ok=True)
    too_deep.write_text("O2001\n")

    config = _make_base_config(tmp_path, "D00")
    files, excluded = service._collect_candidate_files(config, relative_paths=None)

    rel_files = {row[0] for row in files}
    assert "A/B/O2000.NC" in rel_files

    excluded_by_reason = {row[0]: row[3] for row in excluded}
    assert excluded_by_reason.get("A/B/C/O2001.NC") == "nested_directories_not_supported"
