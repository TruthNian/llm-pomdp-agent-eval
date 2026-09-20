"""Only executed in the portfolio container. No expected values are present."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import sysconfig
import zlib


def routing(q):
    from werkzeug.exceptions import HTTPException
    from werkzeug.routing import Map, Rule, RequestRedirect
    mapping = Map([Rule(q["route"], endpoint="target", methods=["GET"], merge_slashes=q["override"])],
                  merge_slashes=q["initial"])
    if q["updated"] is not None:
        mapping.merge_slashes = q["updated"]
    try:
        endpoint, values = mapping.bind("example.test").match(q["path"], method=q["method"])
        return {"status": 200, "endpoint": endpoint, "values": values}
    except RequestRedirect as exc:
        return {"status": exc.code, "location": exc.new_url}
    except HTTPException as exc:
        return {"status": exc.code}


def preinit(q):
    import attrs
    if q.get("simple"):
        seen = []
        def hook(self, a, b):
            seen.extend([a, b])
        cls = attrs.make_class("Simple", {"a": attrs.field(converter=int),
                                         "b": attrs.field(default="5", converter=int)},
                               class_body={"__attrs_pre_init__": hook})
        obj = cls("7", "8")
        return {"hook": seen, "values": [obj.a, obj.b], "factory_calls": 0}
    observed, calls = None, []
    def factory():
        calls.append(1)
        return "13"
    def arguments(self, a, b, c, d, e, f):
        nonlocal observed
        observed = ["NOTHING" if v is attrs.NOTHING else v for v in (a, b, c, d, e, f)]
    def self_only(self):
        nonlocal observed
        observed = []
    fields = {
        "_a": attrs.field(alias="a", converter=int),
        "b": attrs.field(default="5", converter=int),
        "c": attrs.field(factory=factory, converter=int),
        "d": attrs.field(kw_only=True, converter=int),
        "e": attrs.field(default="5", kw_only=True, converter=int),
        "f": attrs.field(factory=factory, kw_only=True, converter=int),
    }
    body = {} if q["hook"] == "absent" else {"__attrs_pre_init__": arguments if q["hook"] == "arguments" else self_only}
    cls = attrs.make_class("Example", fields, slots=q["slots"], frozen=q["frozen"], class_body=body)
    if q["mode"] == "omitted":
        obj = cls(a="7", d="10")
    elif q["mode"] == "positional":
        obj = cls("7", "8", "9", d="10", e="11", f="12")
    else:
        obj = cls(a="7", b="8", c="9", d="10", e="11", f="12")
    return {"hook": observed, "values": [getattr(obj, name) for name in fields], "factory_calls": len(calls)}


def reads(q):
    from urllib3.response import HTTPResponse
    if "wire_hex" in q:
        wire = bytes.fromhex(q["wire_hex"])
    else:
        raw = q["payload"].encode()
        if q["encoding"] == "br":
            import brotli
            wire = brotli.compress(raw)
        elif q["encoding"] == "gzip":
            wire = gzip.compress(raw, mtime=0)
        elif q["encoding"] == "deflate":
            wire = zlib.compress(raw)
        else:
            wire = raw
    response = HTTPResponse(io.BytesIO(wire), headers={"content-encoding": q["encoding"]},
                            preload_content=False, decode_content=q["decode"])
    chunks = [hashlib.sha256(response.read(n)).hexdigest() for n in q["parts"]]
    rest = response.read(cache_content=q["cache"])
    cached = hashlib.sha256(response.data).hexdigest() if q["cache"] else None
    return {"chunk_sha256": chunks, "rest_sha256": hashlib.sha256(rest).hexdigest(),
            "rest_bytes": len(rest), "eof": response.read().hex(), "cached_sha256": cached}


def main():
    payload = json.load(sys.stdin)
    root = Path("/work/repo")
    for name, content in payload["files"].items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    # Only the container's pinned dependencies; -S prevents site startup hooks.
    sys.path.extend([sysconfig.get_path("purelib"), sysconfig.get_path("platlib")])
    sys.path.insert(0, str(root / "src"))
    functions = {"werkzeug_routing": routing, "attrs_preinit": preinit, "urllib3_read": reads}
    values = []
    for query in payload["requests"]:
        try:
            values.append(functions[query["task"]](query))
        except Exception as exc:
            values.append({"error": type(exc).__name__})
    print(json.dumps(values, allow_nan=False))


if __name__ == "__main__":
    main()
