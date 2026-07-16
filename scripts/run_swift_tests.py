#!/usr/bin/env python3
"""Run the TinyRoutes Xcode test scheme with the CI-supported destination."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


DEFAULT_DESTINATION = "platform=iOS Simulator,name=iPhone 16 Pro,OS=18.5"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination",
        default=os.environ.get("TINY_ROUTES_XCODE_DESTINATION", DEFAULT_DESTINATION),
        help="xcodebuild destination (defaults to the simulator pinned in Swift CI).",
    )
    parser.add_argument(
        "--result-bundle",
        type=Path,
        help="Optional path for the Xcode result bundle.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    command = [
        "xcodebuild",
        "test",
        "-project",
        "TinyRoutes.xcodeproj",
        "-scheme",
        "TinyRoutes",
        "-destination",
        args.destination,
        "CODE_SIGNING_ALLOWED=NO",
    ]
    if args.result_bundle is not None:
        result_bundle = args.result_bundle.expanduser().resolve()
        result_bundle.parent.mkdir(parents=True, exist_ok=True)
        command.extend(["-resultBundlePath", str(result_bundle)])

    print("==> " + " ".join(command), flush=True)
    return subprocess.run(command, cwd=repo_root, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
