from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.paths import find_repo_root


SCRIPT = find_repo_root() / "Tools" / "LevelGenerator" / "analyze_level_corpus.py"


def test_analyzer_fails_cleanly_when_sidecar_is_missing(tmp_path: Path) -> None:
    levels = tmp_path / "levels"
    solutions = tmp_path / "solutions"
    levels.mkdir()
    solutions.mkdir()
    (levels / "level_001.json").write_text('{"id":"level_001"}\n', encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--levels-dir", str(levels), "--solutions-dir", str(solutions),
         "--json-output", str(tmp_path / "out.json"), "--markdown-output", str(tmp_path / "out.md")],
        capture_output=True, text=True,
    )

    assert result.returncode == 1
    assert "Missing solution sidecar for level_001" in result.stderr


def test_production_analyzer_output_is_deterministic(tmp_path: Path) -> None:
    root = find_repo_root()
    command = [sys.executable, str(SCRIPT),
        "--json-output", str(tmp_path / "first.json"), "--markdown-output", str(tmp_path / "first.md")]
    subprocess.run(command, cwd=root, check=True)
    command[3] = str(tmp_path / "second.json")
    command[5] = str(tmp_path / "second.md")
    subprocess.run(command, cwd=root, check=True)

    assert (tmp_path / "first.json").read_bytes() == (tmp_path / "second.json").read_bytes()
    assert (tmp_path / "first.md").read_bytes() == (tmp_path / "second.md").read_bytes()
    payload = json.loads((tmp_path / "first.json").read_text(encoding="utf-8"))
    assert payload["analysis"]["levelCount"] > 0
    assert all("allTapsAtZero" in level for level in payload["levels"])
