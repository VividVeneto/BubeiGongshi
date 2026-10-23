# fml-ffi / CORE-03 phase 1

This crate owns the eight C entry points in contracts/include/fmlcore.h. It is an
ABI foundation, not the async runtime or a business-operation implementation.
Production OPS is deliberately empty. Missing operations return FFI_UNKNOWN_OP;
no queue, worker, job or completion is fabricated. submit validates its envelope,
then returns -1 without a registered completion or -2 with one; cancel returns -4.
An idle register replaces the process-wide callback/user pointer, including null
unregister, and returns 0. It never calls that callback in this phase.

## Build and run

Use the workspace locked Rust toolchain. Set FML_BUILD_GIT to the real 40-hex HEAD
when building release/CI artifacts; build.rs accepts unknown only as a local
unbound build marker, never a fake commit. App version comes from the workspace;
target comes from Cargo TARGET (not the machine executing the build script).

Run cargo test -p fml-ffi and cargo test -p fml-ffi --features test_ops,abi_major_bump.
Run python crates/fml-ffi/tests/build_matrix.py on Windows with MSVC installed to
build/load normal, test_ops, bumped and release DLLs, validate capabilities,
exercise actual C compilation/link/execution, and prove both release feature
combinations fail at the intended compile_error. Outputs go to build/ffi-matrix.
The shared tests/fixtures/unknown.json and errors-v1 fixture are byte-level host
vectors. Android host/device execution remains pending, not inferred from Windows.

## Ownership, threads and errors

Callers provide readable NUL-terminated UTF-8 op names, valid request bytes and
aligned writable output pointers. Null and >16 MiB inputs are rejected; an
arbitrary non-null invalid pointer cannot be validated portably and violates the
C API safety precondition. Output buffers are immutable core-owned byte slices,
not NUL-terminated. Free exactly once using the original ptr/len/allocation_id.
The registry checks the entire triple before releasing memory; stale/forged
triples return -1 without dereferencing them. Allocation ids never wrap/reuse.
Callers synchronize access to an individual buffer against free. Concurrent
independent calls/allocations are supported; handler implementations must be
Send + Sync. Never pass an input aliased with the output buffer descriptor.

All exported entry points catch Rust unwinding. Process abort/OOM abort and invalid
foreign pointers are not unwind exceptions and are outside this guarantee. A null
output is possible if a recoverable allocation failure/panic prevents a buffer.
Statuses are 0 success, 1 domain error, -1 bad arguments, -2 unknown/mismatched op,
-3 DTO mismatch, -4 stale handle, -5 panic and -6 busy; error metadata comes from
fml-error, not a parallel registry. Responses contain exactly one ok/error. Error
trace propagation fills only zero trace ids and the outer trace equals the final
error trace, preserving a domain-supplied nonzero id.

The private DTO_MAJOR=1 drives request top-level v, response v, OpCtx.dto and caps.
body.v and manifest.version are not protocol selectors. Budget capability and
OpCtx.budget_ms use the same exact BUDGET_OPS allowlist; other operations ignore it.
The handler, not this dispatcher, implements domain timeouts.

## Trace and handles

Fallback traces use a lazy std RandomState-derived process prefix and atomic
sequence, not a cryptographic or globally-unique guarantee. RandomState may use
OS entropy; this is FFI infrastructure, not a no-I/O domain crate. Fixed-prefix
packing tests are deterministic. The panic recovery prefix is independent of the
lazy initializer. Traces are nonzero lowercase 32-hex; sequence uniqueness is
bounded by wrap (after wrap only nonzero is promised).

HandleActor guards leases and the accepting/closing/retired transition. Native
close marks closing and retirement occurs after the last existing lease drains;
new leases fail, repeated close is busy, retired/stale generation is stale. Store
close uses the same gate and explicit retire. No production handle producer is
present yet: private unit fixtures test scope/identity/lifetime without fake.open
or any extra C export. Slot reuse/generation exhaustion, async jobs/cancellation,
callback draining and Store close integration belong to phases 2/3.

The test_ops feature and unit tests contain isolated fake handlers; abi_major_bump
reports 2.0 from both version and capabilities while the public header stays 1.0.
Both features are forbidden whenever debug_assertions is false. Downstream CORE-41
owns CI configuration; this crate supplies reproducible commands and fixtures only.
