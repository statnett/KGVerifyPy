import pytest

from src.kgverifypy.gui import all_namespaces_match, format_namespace_matrix


# Unit tests all_namespaces_match
def test_all_namespaces_match() -> None:
    report = []
    assert all_namespaces_match(report) is True

    report = [
        {"uri": "http://example.org/ns1", "missing": []},
        {"uri": "http://example.org/ns2", "missing": []}
    ]
    assert all_namespaces_match(report) is True

    report_with_missing = [
        {"uri": "http://example.org/ns1", "missing": []},
        {"uri": "http://example.org/ns2", "missing": ["graph1"]}
    ]
    assert all_namespaces_match(report_with_missing) is False

# Unit tests format_namespace_matrix
def test_format_namespace_matrix_basic():
    report = [
        {
            "uri": "ns1",
            "missing": True,
            "presence": {"g1": "p1"}
        },
        {
            "uri": "ns2",
            "missing": True,
            "presence": {}
        },
    ]
    graph_names = ["g1", "g2"]

    result = format_namespace_matrix(report, graph_names)

    expected = (
        "Namespace |     G1     |     G2    \n"
        "-----------------------------------\n"
        "ns1 |    ✔ p1    |     ✘     \n"
        "ns2 |     ✘      |     ✘     "
    )

    assert result == expected


def test_format_namespace_matrix_notmissing():
    report = [
        {
            "uri": "ns1",
            "missing": ["g2"],
            "presence": {"g1": "p1"}
        },
        {
            "uri": "ns2",
            "missing": [],
            "presence": {}
        },
    ]
    graph_names = ["g1", "g2"]

    result = format_namespace_matrix(report, graph_names)

    expected = (
        "Namespace |     G1     |     G2    \n"
        "-----------------------------------\n"
        "ns1 |    ✔ p1    |     ✘     "
    )

    assert result == expected


def test_format_namespace_matrix_emptyreport():
    assert format_namespace_matrix([], ["g1"]) == "Namespace |     G1    \n----------------------"

def test_format_namespace_matrix_nomissingrows():
    report = [{"uri": "ns", "missing": False, "presence": {}}]
    result = format_namespace_matrix(report, ["g1"])
    assert "ns" not in result


if __name__ == "__main__":
    pytest.main()