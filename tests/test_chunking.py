from backend.ingestion.chunking import split


def test_xv6_function_boundaries_and_lines():
    source = "uint64\nwalkaddr(pagetable_t p, uint64 va)\n{\n  return 0;\n}\n\nvoid\nuvmunmap(void)\n{\n}\n"
    chunks = list(split(source, "kernel/vm.c"))
    assert [loc["function"] for _, loc in chunks] == ["walkaddr", "uvmunmap"]
    for body, loc in chunks:
        assert body == "\n".join(
            source.splitlines()[loc["start_line"] - 1 : loc["end_line"]]
        )


def test_long_function_is_fully_covered():
    source = "void\nlarge(void)\n{\n" + "  action();\n" * 200 + "}\n"
    chunks = list(split(source, "kernel/a.c"))
    assert len(chunks) > 1
    assert all(loc["function"] == "large" for _, loc in chunks)
    assert sum(len(body.splitlines()) for body, _ in chunks) == len(source.splitlines())
