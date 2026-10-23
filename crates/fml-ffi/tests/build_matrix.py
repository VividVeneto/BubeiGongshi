"""Windows host ABI evidence; stdlib only. Not Android/release-device acceptance."""
import ctypes as c
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import queue
import threading

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "build" / "ffi-matrix"
OUT.mkdir(parents=True, exist_ok=True)
SHA = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
ENV = dict(os.environ, FML_BUILD_GIT=SHA)
RESULTS = {"git": SHA, "host_only": True, "cases": []}


def run(label, args, expected=0, contains=None):
    proc = subprocess.run(args, cwd=ROOT, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (OUT / (label + ".log")).write_bytes(proc.stdout)
    assert (proc.returncode == 0) == (expected == 0), (label, proc.returncode)
    if contains:
        assert contains.encode("utf-8") in proc.stdout, label
    RESULTS["cases"].append({"case": label, "exit": proc.returncode, "expected_failure": expected != 0})
    return proc.stdout


class Buf(c.Structure):
    _fields_ = [("ptr", c.c_void_p), ("len", c.c_size_t), ("allocation_id", c.c_uint64)]


def load(path):
    lib = c.CDLL(str(path))
    lib.fml_abi_version.restype = c.c_uint32
    lib.fml_capabilities.restype = Buf
    lib.fml_free_buffer.argtypes = [Buf]
    lib.fml_call.argtypes = [c.c_char_p, c.c_char_p, c.c_size_t, c.POINTER(Buf)]
    lib.fml_submit.argtypes = [c.c_char_p, c.c_char_p, c.c_size_t, c.POINTER(c.c_uint64)]
    lib.fml_cancel.argtypes = [c.c_uint64]
    lib.fml_close_handle.argtypes = [c.c_uint64]
    lib.fml_register_completion.argtypes = [c.c_void_p, c.c_void_p]
    return lib


def take(lib, buf):
    assert buf.ptr and buf.allocation_id
    data = c.string_at(buf.ptr, buf.len)
    assert lib.fml_free_buffer(buf) == 0
    return json.loads(data)


def call(lib, op, req):
    data = json.dumps(req).encode()
    buf = Buf()
    status = lib.fml_call(op.encode(), data, len(data), c.byref(buf))
    return status, take(lib, buf)


libs = {}
for mode, features, release in [("normal", None, False), ("bump", "abi_major_bump", False),
                                ("test_ops", "test_ops", False), ("release", None, True)]:
    target = OUT / mode
    args = ["cargo", "build", "-p", "fml-ffi", "--locked", "--target-dir", str(target)]
    if features:
        args += ["--features", features]
    if release:
        args += ["--release"]
    run(mode, args)
    dll = target / ("release" if release else "debug") / "fmlcore.dll"
    lib = load(dll)
    libs[mode] = lib
    caps = take(lib, lib.fml_capabilities())
    (OUT / (mode + "-capabilities.json")).write_text(json.dumps(caps, indent=2), encoding="utf-8")
    major = 2 if mode == "bump" else 1
    assert lib.fml_abi_version() == major << 16
    assert caps["abi"] == str(major) + ".0"
    assert caps["build"]["app"] == "0.1.0"
    assert caps["build"]["git"] == SHA
    assert caps["build"]["target"] == "x86_64-pc-windows-msvc"
    assert caps["build"]["test_build"] == (mode in ("bump", "test_ops"))
    assert bool(caps["ops"]) == (mode == "test_ops")
    assert all(row["dto"] == 1 for row in caps["ops"])
    assert "fake.open" not in [row["op"] for row in caps["ops"]]
    RESULTS["cases"].append({"case": mode + "-dynamic-caps", "passed": True})

# Real library mismatch against unchanged header ABI: a positive acceptance would be wrong.
assert libs["normal"].fml_abi_version() >> 16 == 1
assert libs["bump"].fml_abi_version() >> 16 != 1
RESULTS["cases"].append({"case": "real-bump-rejected-by-header-major", "passed": True})
for feature in ("test_ops", "abi_major_bump"):
    run("reject-release-" + feature,
        ["cargo", "build", "-p", "fml-ffi", "--locked", "--release", "--features", feature,
         "--target-dir", str(OUT / ("reject-" + feature))], expected=1,
        contains=feature + " is forbidden in non-debug builds")

lib = libs["test_ops"]
trace = "1234567890abcdef1234567890abcdef"
req = {"v": 1, "trace_id": trace, "body": {"v": 987}}
status, reply = call(lib, "fake.echo", req)
assert status == 0 and reply["v"] == 1 and reply["ok"]["dto"] == 1
assert call(lib, "fake.echo", dict(req, v=2))[0] == -3
for op in ("engine.parse", "calc.evaluate", "grade.answer"):
    status, reply = call(lib, op, dict(req, budget_ms=1))
    assert status == 1 and reply["error"]["code"] == "EVAL_TIMEOUT"
    assert reply["error"]["trace_id"] == reply["trace_id"] == trace
status, reply = call(lib, "fake.echo", dict(req, budget_ms=1))
assert status == 0 and reply["ok"]["budget_ms"] is None
samples = []
for i in range(1100):
    start = time.perf_counter_ns()
    assert call(lib, "fake.echo", req)[0] == 0
    elapsed = (time.perf_counter_ns() - start) / 1_000_000
    if i >= 100:
        samples.append(elapsed)
RESULTS["local_latency"] = {"warmup": 100, "samples": 1000, "p95_ms": sorted(samples)[949],
                            "includes": "Python JSON + ctypes + FFI + free; debug desktop host only"}

# Exercise the real worker -> C callback path, not a Python mock of native work.
received = queue.Queue()
callback_errors = []
main_thread = threading.get_ident()
Completion = c.CFUNCTYPE(None, c.c_uint64, Buf, c.c_void_p)


@Completion
def completed(job, buf, user):
    try:
        assert user == 17 and threading.get_ident() != main_thread
        assert lib.fml_cancel(job) == 1
        assert lib.fml_register_completion(None, None) == -6
        received.put((job, buf, json.loads(c.string_at(buf.ptr, buf.len))))
    except Exception as error:
        callback_errors.append(repr(error))


assert lib.fml_register_completion(c.cast(completed, c.c_void_p), c.c_void_p(17)) == 0
expected = {}
for op in ("fake.async", "fake.async_error", "fake.async_traced", "fake.async_panic", "fake.async_invalid"):
    for _ in range(8):
        payload = json.dumps(req).encode()
        job = c.c_uint64()
        assert lib.fml_submit(op.encode(), payload, len(payload), c.byref(job)) == 0
        assert job.value not in expected
        expected[job.value] = op
seen = set()
for _ in expected:
    job, buf, reply = received.get(timeout=10)
    assert job not in seen and job in expected
    seen.add(job)
    op = expected[job]
    assert reply["v"] == 1
    assert reply["trace_id"] == ("07" * 16 if op == "fake.async_traced" else trace)
    if op != "fake.async":
        assert reply["trace_id"] == reply["error"]["trace_id"]
    assert lib.fml_register_completion(None, None) == -6
    assert lib.fml_free_buffer(buf) == 0
    assert lib.fml_free_buffer(buf) == -1
assert not callback_errors, callback_errors
# The last Python callback can have returned while Rust is still releasing its lease.
# Retry the documented busy state; the deadline diagnoses a leak, not wins a race.
deadline = time.monotonic() + 10
while lib.fml_register_completion(None, None) == -6:
    assert time.monotonic() < deadline, "native callback resources did not drain"
assert received.empty()
assert lib.fml_register_completion(c.cast(completed, c.c_void_p), c.c_void_p(17)) == 0
payload = json.dumps(dict(req, body={"wait_ms": 5000})).encode()
job = c.c_uint64()
assert lib.fml_submit(b"fake.wait", payload, len(payload), c.byref(job)) == 0
status = lib.fml_cancel(job)
if status == 0:
    assert received.empty()
else:
    assert status == 1
    delivered, buf, _ = received.get(timeout=10)
    assert delivered == job.value and lib.fml_free_buffer(buf) == 0
deadline = time.monotonic() + 10
while lib.fml_register_completion(None, None) == -6:
    assert time.monotonic() < deadline
assert lib.fml_cancel(job) == -4
RESULTS["cases"].append({"case": "native-async-callback-reentry-trace-ownership", "passed": True, "completions": len(seen)})
RESULTS["cases"].append({"case": "native-cooperative-cancel", "passed": True, "status": status})

# Compile/link/run a genuine C translation unit against the normal DLL import library.
if sys.platform == "win32":
    vswhere = Path(os.environ["ProgramFiles(x86)"]) / "Microsoft Visual Studio/Installer/vswhere.exe"
    install = subprocess.check_output([str(vswhere), "-latest", "-property", "installationPath", "-utf8"], text=True, encoding="utf-8").strip()
    vcvars = Path(install) / "VC/Auxiliary/Build/vcvarsall.bat"
    debug = OUT / "normal/debug"
    exe = debug / "header_smoke.exe"
    # Native compiler diagnostics are retained as raw bytes, never guessed/decoded.
    command = ('call "' + str(vcvars) + '" x64 >nul && cl /nologo /TC /W4 /WX /std:c11 /I"'
               + str(ROOT / "contracts/include") + '" "' + str(ROOT / "crates/fml-ffi/tests/header_smoke.c")
               + '" /Fo"' + str(debug / "header_smoke.obj") + '" /Fe"' + str(exe) + '" /link "'
               + str(debug / "fmlcore.dll.lib") + '" && "' + str(exe) + '"')
    run("pure-c", 'cmd.exe /d /s /c "' + command + '"', contains="pure-C eight-symbol compile/link/run PASS")
    negative = OUT / "wrong_signature.c"
    negative.write_text('#include "fmlcore.h"\nint main(void) { return fml_call(); }\n', encoding="utf-8")
    negative_command = ('call "' + str(vcvars) + '" x64 >nul && cl /nologo /TC /W4 /WX /c /I"'
                        + str(ROOT / "contracts/include") + '" "' + str(negative) + '" /Fo"'
                        + str(OUT / "wrong_signature.obj") + '"')
    run("pure-c-reject-signature", 'cmd.exe /d /s /c "' + negative_command + '"', expected=1, contains="error C")
    exports_command = 'call "' + str(vcvars) + '" x64 >nul && dumpbin /nologo /exports "' + str(debug / "fmlcore.dll") + '"'
    exports = run("exports", 'cmd.exe /d /s /c "' + exports_command + '"')
    import re
    symbols = set(re.findall(rb"\b(fml_[a-z_]+)\b", exports))
    assert symbols == {s.encode() for s in ("fml_abi_version", "fml_capabilities", "fml_call", "fml_submit",
                                          "fml_cancel", "fml_register_completion", "fml_free_buffer", "fml_close_handle")}
else:
    raise RuntimeError("This harness requires Windows; Android must run the same fixtures separately")
(OUT / "results.json").write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")
print(json.dumps(RESULTS, indent=2))
