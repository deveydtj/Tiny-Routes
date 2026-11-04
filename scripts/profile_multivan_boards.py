#!/usr/bin/env python3
"""Record Instruments traces of both multi-van boards on a device (MW-10).

Builds the internal configuration, installs it, then for each board launches the
prototype in autoplay (see TinyRoutes/Prototype/MultiVanAutoplay.swift) so it plays
one level on a loop with no touches, and records each template against it. The
device must be unlocked and connected by cable (Instruments doesn't see a device
that only `devicectl` reaches over the network). The app keeps it awake while
autoplay runs. Instruments launches the app itself, because it can't attach to a
process `devicectl` started; trim the first `--warmup` seconds when reading a trace.

    scripts/profile_multivan_boards.py --device "Jake iPad Pro"
    scripts/profile_multivan_boards.py --device <udid> --seconds 600 --template "Power Profiler"

With `--meter`, nothing needs a cable: each board plays for `--seconds` while the
app's own performance meter (MultiVanPerformanceMeter.swift) records frames,
thermal state and battery, then `devicectl` copies its file back over Wi-Fi and
this prints a summary. Unplug the device for battery numbers.

    scripts/profile_multivan_boards.py --device <udid> --meter --seconds 600
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
import time
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ID = "com.tinyroutes.app"
METER_FILE = "Documents/multi_van_performance.jsonl"


def run(command: list[str]) -> None:
    print("==> " + " ".join(command), flush=True)
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def destination(device: str) -> str:
    """xcodebuild wants a UDID as `id=` and anything else as a name."""
    is_udid = re.fullmatch(r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{16}|[0-9A-Fa-f-]{36}", device) is not None
    return f"id={device}" if is_udid else f"platform=iOS,name={device}"


def autoplay_argument(level: str, board: str) -> str:
    solution = REPO_ROOT / f"TinyRoutesTests/Resources/PrototypeSolutions/{level}.solution.json"
    script = json.loads(solution.read_text())
    script.update(levelID=level, board=board)
    return json.dumps(script, separators=(",", ":"))


def launch(device: str, argument: str) -> int:
    """Starts autoplay over the network and returns the app's process ID."""
    with tempfile.TemporaryDirectory() as folder:
        result = Path(folder) / "launch.json"
        run(["xcrun", "devicectl", "device", "process", "launch", "--device", device, "--terminate-existing",
             "--json-output", str(result), BUNDLE_ID, "--", "-MultiVanAutoplay", argument])
        return json.loads(result.read_text())["result"]["process"]["processIdentifier"]


def summarise(path: Path, warmup: float) -> str:
    """One line per board, phase and clock, plus the thermal and battery story."""
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    start = min((row["uptime"] for row in rows), default=0)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    lines = []
    for row in rows:
        if row["recordType"] == "frames" and row["uptime"] - start >= warmup:
            groups[(row["label"], row["source"])].append(row)
    for (label, source), group in sorted(groups.items()):
        seconds = sum(row["seconds"] for row in group)
        frames = sum(row["frames"] for row in group)
        hitches = sum(row["hitches"] for row in group)
        worst_p95 = max(row["p95Milliseconds"] for row in group)
        lines.append(f"  {label:<16} {source:<9} {frames / seconds if seconds else 0:5.1f} fps  "
                     f"{hitches:4d} hitches in {seconds:5.0f} s  worst p95 {worst_p95:5.1f} ms")
    devices = [row for row in rows if row["recordType"] == "device"]
    if devices:
        states = " → ".join(dict.fromkeys(row["thermalState"] for row in devices))
        first, last = devices[0], devices[-1]
        minutes = (last["uptime"] - first["uptime"]) / 60
        lines.append(f"  thermal {states}; battery {first['batteryLevel']:.0%} → {last['batteryLevel']:.0%} "
                     f"over {minutes:.1f} min ({last['batteryState']})")
    return "\n".join(lines)


def measure(args: argparse.Namespace, boards: list[str], output: Path) -> None:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    pid = None
    for board in boards:
        pid = launch(args.device, autoplay_argument(args.level, board))
        time.sleep(args.seconds + args.warmup)
        path = output / f"{stamp}-{args.level}-{board}-meter.jsonl"
        copy = ["xcrun", "devicectl", "device", "copy", "from", "--device", args.device, "--domain-type",
                "appDataContainer", "--domain-identifier", BUNDLE_ID, "--source", METER_FILE, "--destination", str(path)]
        # Wi-Fi transfers sometimes drop mid-file; the app keeps writing, so try again.
        for attempt in range(4):
            try:
                run(copy)
                break
            except subprocess.CalledProcessError:
                if attempt == 3:
                    raise
                time.sleep(5)
        print(f"{board} ({path.name}):\n{summarise(path, args.warmup)}", flush=True)
    if pid is not None:
        run(["xcrun", "devicectl", "device", "process", "terminate", "--device", args.device, "--pid", str(pid)])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--device", required=True, help="Device name or UDID, as `xcrun devicectl list devices` shows it.")
    parser.add_argument("--level", default="level_012", help="Level to loop (default: level_012, the busiest board).")
    parser.add_argument("--board", action="append", choices=["diorama", "flat"],
                        help="Board to record; repeat for both (default: both).")
    parser.add_argument("--template", action="append",
                        help='Instruments template; repeat for several (default: "Game Performance").')
    parser.add_argument("--seconds", type=int, default=60, help="Length of each recording.")
    parser.add_argument("--warmup", type=int, default=10,
                        help="Extra seconds recorded at the start for launch, to leave out of the reading.")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / ".local/profiles",
                        help="Folder for the traces and the build.")
    parser.add_argument("--meter", action="store_true",
                        help="Measure with the in-app meter over Wi-Fi instead of Instruments.")
    parser.add_argument("--skip-build", action="store_true", help="Install the last build in the output folder without rebuilding.")
    args = parser.parse_args(argv)
    boards = args.board or ["diorama", "flat"]
    templates = args.template or ["Game Performance"]
    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    derived = output / "DerivedData"
    app = derived / "Build/Products/InternalTestFlight-iphoneos/TinyRoutes.app"
    if not args.skip_build:
        run(["xcodebuild", "build", "-project", "TinyRoutes.xcodeproj", "-scheme", "MultiVanInternal",
             "-configuration", "InternalTestFlight", "-destination", destination(args.device),
             "-derivedDataPath", str(derived), "-allowProvisioningUpdates", "-quiet"])
    # Instruments launches by path, which only resolves to this exact build installed.
    run(["xcrun", "devicectl", "device", "install", "app", "--device", args.device, str(app)])
    if args.meter:
        measure(args, boards, output)
        return 0

    stamp = time.strftime("%Y%m%d-%H%M%S")
    for template in templates:
        for board in boards:
            trace = output / f"{stamp}-{args.level}-{board}-{template.replace(' ', '_')}.trace"
            run(["xcrun", "xctrace", "record", "--device", args.device, "--template", template,
                 "--time-limit", f"{args.seconds + args.warmup}s", "--output", str(trace), "--no-prompt",
                 "--launch", "--", str(app), "-MultiVanAutoplay", autoplay_argument(args.level, board)])
            print(f"Recorded {trace}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
