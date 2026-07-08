"""Tests for JSON file storage."""


from patent_research_mcp.schemas import (
    Architecture,
    ArchitectureCard,
    ClaimsFirewall,
    Enterprise360,
    PatternCard,
    Problem,
)
from patent_research_mcp.store import (
    list_patterns,
    load_architecture_card,
    load_claims_firewall,
    load_pattern,
    load_raw_text,
    load_sections,
    raw_exists,
    save_architecture_card,
    save_claims_firewall,
    save_export,
    save_pattern,
    save_raw_html,
    save_raw_text,
    save_sections,
)


def test_raw_html_text(tmp_path):
    """Test storing raw patent data."""
    # Override home for testing
    import patent_research_mcp.store as store

    original_home = store._home
    store._home = lambda: tmp_path / "data"

    try:
        save_raw_html("US0000000A0", "<html>test</html>")
        save_raw_text("US0000000A0", "Test patent text")

        assert raw_exists("US0000000A0")
        assert load_raw_text("US0000000A0") == "Test patent text"
    finally:
        store._home = original_home


def test_sections_storage(tmp_path):
    """Test sections JSON storage."""
    import patent_research_mcp.store as store

    original_home = store._home
    store._home = lambda: tmp_path / "data"

    try:
        data = {
            "publication_number": "US1",
            "title": "Test Patent",
            "abstract": "An abstract",
            "claims": "Claim 1...",
        }
        save_sections("US1", data)
        loaded = load_sections("US1")
        assert loaded is not None
        assert loaded["title"] == "Test Patent"
        assert loaded["abstract"] == "An abstract"
    finally:
        store._home = original_home


def test_architecture_card_storage(tmp_path):
    """Test ArchitectureCard save/load roundtrip."""
    import patent_research_mcp.store as store

    original_home = store._home
    store._home = lambda: tmp_path / "data"

    try:
        card = ArchitectureCard(
            publication_number="US1",
            title="Test",
            domain="DM",
            problem=Problem(
                business_problem="BP",
                technical_problem="TP",
                why_it_matters_for_enterprise_360="WIM",
            ),
            architecture=Architecture(),
            enterprise_360=Enterprise360(),
        )
        save_architecture_card(card)
        loaded = load_architecture_card("US1")
        assert loaded is not None
        assert loaded.title == "Test"
        assert loaded.publication_number == "US1"
    finally:
        store._home = original_home


def test_claims_firewall_storage(tmp_path):
    """Test ClaimsFirewall save/load."""
    import patent_research_mcp.store as store

    original_home = store._home
    store._home = lambda: tmp_path / "data"

    try:
        fw = ClaimsFirewall(
            publication_number="US1",
            original_direction="Event-driven",
            risk_level="low",
        )
        save_claims_firewall(fw)
        loaded = load_claims_firewall("US1")
        assert loaded is not None
        assert loaded.original_direction == "Event-driven"
    finally:
        store._home = original_home


def test_pattern_storage(tmp_path):
    """Test PatternCard save/load/list."""
    import patent_research_mcp.store as store

    original_home = store._home
    store._home = lambda: tmp_path / "data"

    try:
        p = PatternCard(
            name="Unified Inbox",
            slug="unified_inbox",
            domain="Workflow",
            description="A unified inbox",
            source_patents=["US1"],
            core_entities=["WorkItem"],
            reusable_principle="Aggregate tasks",
            suggested_module="workhub",
            risk_level="low",
        )
        save_pattern(p)
        loaded = load_pattern("unified_inbox")
        assert loaded is not None
        assert loaded.name == "Unified Inbox"

        patterns = list_patterns()
        assert len(patterns) == 1
    finally:
        store._home = original_home


def test_export_storage(tmp_path):
    """Test Markdown export storage."""
    import patent_research_mcp.store as store

    original_home = store._home
    store._home = lambda: tmp_path / "data"

    try:
        path = save_export("test.md", "# Test Export")
        assert path.endswith("test.md")
        export_file = tmp_path / "data" / "exports" / "test.md"
        assert export_file.read_text() == "# Test Export"
    finally:
        store._home = original_home
