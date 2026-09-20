"""Expected behavior derived from each public contract, never candidate imports."""
import hashlib

# Fixed wire bytes from the validated Python 3.13 run; gzip OS headers vary by host.
RAW_WIRE = (
    ('1f8b08000000000002ff4bcbcf4f4a2c4a4aac0200aa27781a09000000', '789c4bcbcf4f4a2c4a4aac0200127b03b7'),
    ('1f8b08000000000002ffedc6490100200800b0ac7820da3f8041d85e8b31d7ce53f7859999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999959fb7d88a491ee409c0000', '789cedc6490100200800b0ac7820da3f8041d85e8b31d7ce53f7859999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999959fb7de175f6f4'),
    ('1f8b08000000000002ffedcc572202000000d0b3244413211132334221241a28195112eaf4ced0ff7b07788189e0e4d4746866361c89c6e289b9f985e4e2d2726a25bdba9659dfd8cc6e6defeceeede70e0e8f8ef327a76785e2f9c565e9eafaa67c5bb9bbafd6ea8d87c7a766ebb9fdf2faf6def9f8ecf6befadf839fdfbfe12860369bcd66b3d96c369bcd66b3d96c369bcd66b3d96c369bcd66b3d96c369bcd66b3d96c369bcd66b3d96c369bcd66b3d96c369bcd66b3d96c369bcd66b3d96c369bcde631e67f34ff966b204e0000', '789cedcc572202000000d0b3244413211132334221241a28195112eaf4ced0ff7b07788189e0e4d4746866361c89c6e289b9f985e4e2d2726a25bdba9659dfd8cc6e6defeceeede70e0e8f8ef327a76785e2f9c565e9eafaa67c5bb9bbafd6ea8d87c7a766ebb9fdf2faf6def9f8ecf6befadf839fdfbfe12860369bcd66b3d96c369bcd66b3d96c369bcd66b3d96c369bcd66b3d96c369bcd66b3d96c369bcd66b3d96c369bcd66b3d96c369bcd66b3d96c369bcd66b3d96c369bcde631e67f93e3a54e'),
)


def routing():
    rows = []
    for initial in (True, False):
        for updated in (None, True, False):
            active = initial if updated is None else updated
            for override in (None, True, False):
                # Rules bind before the Map setting is updated.
                rule_merge = initial if override is None else override
                for route, good, repeated, values in (
                    ("/api/path", "/api/path", "/api//path", {}),
                    ("/api/<int:code>", "/api/42", "/api//42", {"code": 42}),
                    ("/download/<path:item>", "/download/one//two", "/download//one//two", {"item": "one//two"}),
                ):
                    for path in (good, repeated, "/not-found"):
                        query = {"task": "werkzeug_routing", "initial": initial, "updated": updated,
                                 "override": override, "route": route, "path": path, "method": "GET"}
                        if path == good:
                            expected = {"status": 200, "endpoint": "target", "values": values}
                        elif path == repeated and active and rule_merge:
                            expected = {"status": 308, "location": "http://example.test" + good.replace("//", "/")}
                        else:
                            expected = {"status": 404}
                        rows.append({"input": query, "expected": expected})
    for route, path, method, override, expected in (
        ("/api/path", "/api/path", "POST", None, {"status": 405}),
        ("/api/path/", "/api/path", "GET", None, {"status": 308, "location": "http://example.test/api/path/"}),
        ("/literal//path", "/literal//path", "GET", False, {"status": 200, "endpoint": "target", "values": {}}),
        ("/literal//path", "/literal/path", "GET", False, {"status": 404}),
    ):
        rows.append({"input": {"task": "werkzeug_routing", "initial": True, "updated": None,
                              "override": override, "route": route, "path": path, "method": method},
                     "expected": expected})
    return rows


def preinit():
    rows = [{"input": {"task": "attrs_preinit", "simple": True},
             "expected": {"hook": ["7", "8"], "values": [7, 8], "factory_calls": 0}}]
    for slots in (True, False):
        for frozen in (True, False):
            for mode in ("supplied", "omitted", "positional"):
                for hook in ("arguments", "self", "absent"):
                    supplied = mode != "omitted"
                    raw = ["7", "8", "9", "10", "11", "12"] if supplied else ["7", "5", "NOTHING", "10", "5", "NOTHING"]
                    values = [7, 8, 9, 10, 11, 12] if supplied else [7, 5, 13, 10, 5, 13]
                    expected = {"hook": raw if hook == "arguments" else ([] if hook == "self" else None),
                                "values": values, "factory_calls": 0 if supplied else 2}
                    rows.append({"input": {"task": "attrs_preinit", "slots": slots, "frozen": frozen,
                                           "mode": mode, "hook": hook}, "expected": expected})
    return rows


def reads():
    rows = []
    # Highly compressible and varied bodies exercise real decoder buffering.
    for payload_index, payload in enumerate(("foobarbaz", "abcdefghij" * 4000, "".join(chr(33 + i % 90) for i in range(20000)))):
        raw = payload.encode()
        for encoding in ("br", "gzip", "deflate", "identity"):
            for parts in ([3], [0, 1, 7, 512], [512, 1024], [], [len(raw) + 1]):
                for cache in (False, True):
                    position, chunks = 0, []
                    for n in parts:
                        chunk = raw[position:position + n]
                        position += len(chunk)
                        chunks.append(hashlib.sha256(chunk).hexdigest())
                    rest = raw[position:]
                    expected = {"chunk_sha256": chunks, "rest_sha256": hashlib.sha256(rest).hexdigest(),
                                "rest_bytes": len(rest), "eof": "", "cached_sha256":
                                hashlib.sha256(rest).hexdigest() if cache else None}
                    rows.append({"input": {"task": "urllib3_read", "payload": payload, "encoding": encoding,
                                           "parts": parts, "cache": cache, "decode": True}, "expected": expected})
        # Raw mode must keep compressed bytes intact; no decoder private-state injection.
        for encoding, wire_hex in zip(("gzip", "deflate"), RAW_WIRE[payload_index]):
            body = bytes.fromhex(wire_hex)
            rows.append({"input": {"task": "urllib3_read", "wire_hex": body.hex(), "encoding": encoding,
                                   "parts": [3], "cache": False, "decode": False},
                         "expected": {"chunk_sha256": [hashlib.sha256(body[:3]).hexdigest()],
                                      "rest_sha256": hashlib.sha256(body[3:]).hexdigest(),
                                      "rest_bytes": len(body) - 3, "eof": "", "cached_sha256": None}})
    return rows


def selected(task, group):
    rows = {"werkzeug_routing": routing, "attrs_preinit": preinit, "urllib3_read": reads}[task]()
    if group == "all":
        return rows
    if group != "reproduction":
        raise ValueError("Unknown repair check group")
    if task == "werkzeug_routing":
        return [next(r for r in rows if r["input"]["initial"] and r["input"]["updated"] is False
                     and r["input"]["override"] is None and r["input"]["path"] == "/api//path")]
    if task == "urllib3_read":
        return [next(r for r in rows if r["input"].get("encoding") == "br"
                     and len(r["input"].get("payload", "")) == 20000
                     and r["input"]["parts"] == [512, 1024] and not r["input"]["cache"])]
    return rows[:1]
