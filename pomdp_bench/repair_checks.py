"""Behavior inputs and an evaluator-owned oracle; never import candidate code."""
from .generator import digest

CHECK_VERSION = "packaging-requirement-state/1"


def checks():
    examples = [
        ("foo>=1.0", "foo", [], ">=1.0", None, None, None),
        ("bar>=2.0a1", "bar", [], ">=2.0a1", None, None, True),
        ('Requests[security]>=2.0; python_version < "4"', "Requests", ["security"], ">=2.0",
         None, 'python_version < "4"', None),
        ("pkg @ https://example.invalid/pkg.whl", "pkg", [], "", "https://example.invalid/pkg.whl", None, None),
    ]
    result = []
    for text, name, extras, specifier, url, marker, autodetected in examples:
        for operation in ("pickle", "copy", "deepcopy", "legacy_dict", "legacy_string"):
            for flag in (None, True, False) if operation != "legacy_string" else (None,):
                for protocol in range(6) if operation == "pickle" else (None,):
                    query = {"operation": operation, "requirement": text, "prereleases": flag, "protocol": protocol}
                    expected = {"text": text, "name": name, "extras": extras, "specifier": specifier, "url": url,
                                "marker": marker, "raw_prereleases": flag,
                                "prereleases": autodetected if flag is None else flag}
                    result.append({"input": query, "expected": expected})
    for value in (None, 42, True, [], {}, "", "foo["):
        # Empty dictionaries were historically accepted; exclude that legacy format.
        if value == {}:
            continue
        result.append({"input": {"operation": "invalid_state", "state": value},
                       "expected": {"error": "TypeError"}})
    return result


def selected_checks(group):
    rows = checks()
    if group == "reproduction":
        return [next(r for r in rows if r["input"] == {
            "operation": "pickle", "requirement": "foo>=1.0", "prereleases": True, "protocol": 5})]
    if group == "all":
        return rows
    raise ValueError("Unknown repair check group")


def assess(group, response):
    expected = [r["expected"] for r in selected_checks(group)]
    if response.get("status") != "completed":
        return {"passed": False, "checks": len(expected), "matched": 0,
                "execution_status": response["status"], "failures": []}
    values = response.get("values")
    if not isinstance(values, list) or len(values) != len(expected):
        return {"passed": False, "checks": len(expected), "matched": 0,
                "execution_status": "invalid_response", "failures": []}
    failures = [i for i, (a, b) in enumerate(zip(values, expected)) if digest(a) != digest(b)]
    # Feedback is actionable behavior, never a privileged patch or grader source.
    return {"passed": not failures, "checks": len(expected), "matched": len(expected) - len(failures),
            "execution_status": "completed",
            "failures": [{"input": selected_checks(group)[i]["input"], "expected": expected[i], "actual": values[i]}
                         for i in failures[:3]]}
