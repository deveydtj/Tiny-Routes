from __future__ import annotations


class LevelNamingService:
    def name_for_level_number(self, level_number: int) -> str:
        return f"Level {level_number:03d}"
