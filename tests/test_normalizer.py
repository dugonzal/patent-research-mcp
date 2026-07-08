"""Tests for text normalizer."""


from patent_research_mcp.normalizer import (
    clean_whitespace,
    find_shared_concepts,
    normalize_list,
    normalize_term,
)


class TestNormalizeTerm:
    def test_synonym_mapping(self):
        assert normalize_term("WorkItem") == "work_item"
        assert normalize_term("work item") == "work_item"
        assert normalize_term("task") == "work_item"
        assert normalize_term("issue") == "work_item"
        assert normalize_term("ticket") == "work_item"
        assert normalize_term("approval") == "work_item"
        assert normalize_term("alert") == "work_item"

    def test_known_terms(self):
        assert normalize_term("business_object") == "business_object"
        assert normalize_term("workflow") == "workflow"
        assert normalize_term("rule") == "rule"
        assert normalize_term("permission") == "permission"
        assert normalize_term("audit_trail") == "audit_trail"

    def test_unknown_passthrough(self):
        assert normalize_term("custom_entity") == "custom_entity"
        assert normalize_term("Custom Entity") == "custom_entity"


class TestNormalizeList:
    def test_deduplication(self):
        result = normalize_list(["WorkItem", "task", "issue", "ticket"])
        assert result == ["work_item"]  # all synonyms

    def test_mixed(self):
        result = normalize_list(["WorkItem", "User", "Task", "Order"])
        assert "work_item" in result
        assert "user" in result
        assert "order" in result
        assert len(result) == 3  # WorkItem+Task deduped


class TestFindSharedConcepts:
    def test_shared_across_lists(self):
        a = ["WorkItem", "User", "Order"]
        b = ["Task", "User", "Invoice"]
        c = ["Issue", "User", "Product"]
        shared = find_shared_concepts([a, b, c])
        assert "work_item" in shared  # all three normalized
        assert "user" in shared
        assert len(shared) == 2

    def test_no_shared(self):
        a = ["Order", "Product"]
        b = ["Invoice", "Payment"]
        shared = find_shared_concepts([a, b])
        assert shared == []

    def test_single_list(self):
        shared = find_shared_concepts([["A", "B", "C"]])
        assert shared == ["a", "b", "c"]


class TestCleanWhitespace:
    def test_extra_spaces(self):
        assert clean_whitespace("Hello    World") == "Hello World"

    def test_newlines(self):
        assert clean_whitespace("Line1\n\nLine2\nLine3") == "Line1 Line2 Line3"

    def test_empty(self):
        assert clean_whitespace("") == ""
