def test_generator_can_import_shared_core() -> None:
    import tiny_routes_core

    assert tiny_routes_core.__version__

