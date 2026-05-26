#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.map_import.map_graph_simplifier import MapGraphSimplifier
from app.map_import.osm_seed_importer import OSMSeedImporter


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import an OpenStreetMap seed graph for Tiny Routes generation.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--place", help="Place name to import, such as 'Imperial, Missouri, USA'.")
    source.add_argument("--bbox", nargs=4, type=float, metavar=("NORTH", "SOUTH", "EAST", "WEST"))
    parser.add_argument("--output", type=Path, required=True, help="Explicit output path for the simplified seed JSON.")
    parser.add_argument("--cache-dir", type=Path, default=None, help="Optional cache directory for the raw imported graph.")
    parser.add_argument("--network-type", default="drive", help="OSMnx network type. Default: drive.")
    parser.add_argument("--max-nodes", type=int, default=12, help="Maximum simplified nodes to keep.")
    parser.add_argument("--seed", type=int, default=0, help="Deterministic node-selection seed.")
    args = parser.parse_args(argv)

    importer = OSMSeedImporter()
    if args.place:
        raw_graph = importer.import_place(args.place, network_type=args.network_type)
        source_label = args.place
    else:
        north, south, east, west = args.bbox
        raw_graph = importer.import_bbox(north, south, east, west, network_type=args.network_type)
        source_label = f"bbox:{north},{south},{east},{west}"

    simplified = MapGraphSimplifier().simplify(raw_graph, max_nodes=args.max_nodes, seed=args.seed)
    payload = {
        "source": source_label,
        "rawNodeCount": len(raw_graph.nodes),
        "rawEdgeCount": len(raw_graph.edges),
        "simplifiedGraph": simplified.to_dict(),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.cache_dir is not None:
        args.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = args.cache_dir / f"{args.output.stem}.raw.json"
        cache_path.write_text(json.dumps(raw_graph.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Wrote map seed: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
