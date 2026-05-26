from __future__ import annotations

from html import escape
from pathlib import Path


class PreviewImageService:
    def write_preview(self, generated_level, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{generated_level.level_id}.svg"
        path.write_text(self._svg(generated_level), encoding="utf-8")
        generated_level.preview_path = path
        return path

    def _svg(self, generated_level) -> str:
        level = generated_level.level_document
        nodes = level.graph.nodes
        width = 420
        height = 320
        margin = 30
        xs = [node.x for node in nodes] or [0]
        ys = [node.y for node in nodes] or [0]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 1e-9)
        span_y = max(max_y - min_y, 1e-9)

        def point(node_id: str) -> tuple[float, float]:
            node = node_by_id[node_id]
            x = margin + ((node.x - min_x) / span_x * (width - (2 * margin)))
            y = height - (margin + ((node.y - min_y) / span_y * (height - (2 * margin))))
            return x, y

        node_by_id = {node.id: node for node in nodes}
        tap_order = {
            action.tapNodeID: index + 1
            for index, action in enumerate(sorted(generated_level.solution.actions, key=lambda action: action.timeSeconds))
        }
        lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#f8fafc"/>',
            f'<text x="16" y="22" font-family="Arial" font-size="14" fill="#0f172a">{escape(level.id)}</text>',
        ]
        has_four_way_switch = any(len(node.outgoingEdgeIDs) == 4 for node in nodes)
        if has_four_way_switch:
            lines.append('<text x="16" y="42" font-family="Arial" font-size="11" fill="#9a3412">4-way switch</text>')
        for edge in level.graph.edges:
            if edge.fromNodeID not in node_by_id or edge.toNodeID not in node_by_id:
                continue
            x1, y1 = point(edge.fromNodeID)
            x2, y2 = point(edge.toNodeID)
            lines.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#64748b" stroke-width="3"/>')
        for node in nodes:
            x, y = point(node.id)
            fill = "#94a3b8"
            if node.id == level.startNodeID:
                fill = "#22c55e"
            elif node.id == level.packageNodeID:
                fill = "#f59e0b"
            elif node.id == level.destinationNodeID:
                fill = "#ef4444"
            elif len(node.outgoingEdgeIDs) == 4:
                fill = "#f97316"
            elif len(node.outgoingEdgeIDs) > 1:
                fill = "#3b82f6"
            lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="{fill}" stroke="#0f172a" stroke-width="1"/>')
            label = tap_order.get(node.id, node.id)
            lines.append(
                f'<text x="{x + 10:.1f}" y="{y - 10:.1f}" font-family="Arial" font-size="11" fill="#0f172a">'
                f'{escape(str(label))}</text>'
            )
        lines.append("</svg>")
        return "\n".join(lines) + "\n"
