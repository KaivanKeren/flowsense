def test_package_imports():
    import flowsense

    assert flowsense.__name__ == "flowsense"
    assert hasattr(flowsense, "__version__")
