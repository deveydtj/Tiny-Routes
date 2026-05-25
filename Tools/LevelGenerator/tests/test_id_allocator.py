from __future__ import annotations

from app.id_allocator import IDAllocator


def test_node_id_allocation_prevents_duplicates() -> None:
    allocator = IDAllocator()

    assert allocator.reserve_node_id("Switch A") == "switch_a"
    assert allocator.reserve_node_id("Switch A") == "switch_a_2"


def test_edge_id_allocation_prevents_duplicates() -> None:
    allocator = IDAllocator()

    assert allocator.reserve_edge_id("start", "package") == "e_start_package"
    assert allocator.reserve_edge_id("start", "package") == "e_start_package_2"


def test_safe_ids_handle_punctuation_and_numbers() -> None:
    allocator = IDAllocator()

    assert allocator.reserve_node_id("  12 Main St.! ") == "id_12_main_st"
