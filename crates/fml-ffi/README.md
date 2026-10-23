# fml-ffi / CORE-03 phases 1–2

This crate owns the eight unchanged C entry points in contracts/include/fmlcore.h
and a process-lifetime native worker pool. Production OPS remains deliberately
empty until business owner cards register real operations; no fake store.open or
public handle producer exists. Debug test_ops supplies isolated Submit fixtures.

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

## Asynchronous ownership and cancellation

submit copies the C name/request before returning; preparation shares call's
mode, scope, handle, DTO and body consistency checks. A prepared request owns its
actor lease until execution/cancellation finishes. Admission is nonblocking with
MAX_INFLIGHT_JOBS=64 (queued + executing), using min(4, available CPUs) workers.
Job IDs increase, never reuse/wrap; exhaustion returns busy. Completed jobs retain
only delivery metadata until both callback return and buffer free, then become
unknown (-4). The callback can race submit's return: consumers must handle an
early completion by job ID. There is no timer callback or fake success job.

Callbacks execute on worker threads without queue/actor/buffer locks. A live job
pins its registered function/user_data through delivery. Register/replace/null
unregister returns -6 for any queued/running/emitting job or unfreed callback
buffer; a failed attempt leaves the old registration intact. Only a successful
unregister allows freeing callback/user_data. Do not unload this process-lifetime
DLL. Each committed job invokes exactly one callback; the receiver frees its
buffer once even if its own logical job has already been discarded. Recoverable
allocation failure delivers the null/zero triple, which must not be freed.

cancel and the completion checkpoint are serialized. Before commit, cancel
signals the handler and waits on a condition variable (releasing the global
lock) until request/body/result/lease resources are really gone, then returns 0
and no callback can follow. Queued work is removed immediately. After commit,
cancel returns 1, including reentrant self-cancel in a callback; the buffer still
must be freed. Fully reclaimed/unknown IDs return -4. Noncooperative handlers may
never finish: no arbitrary timeout, forced kill or premature 0 is promised.
Dart's main isolate must not synchronously call this potentially blocking cancel;
stage 3 owns background-isolate cancellation and listener drainage.

Native close never calls blocking cancel. Under the same commit lock it rejects
committed delivery resources (-6), marks the actor closing, signals running jobs,
and discards queued requests. Last lease release retires it. A racing prepared
submission is rechecked under that lock before admission. StoreClose uses the
same gate with explicit owner-driven retire; store.close/account.close_profile
control requests do not hold a business lease or cancel themselves. Real Store
integration, Android and Dart lifecycle acceptance remain deferred.

Test Submit ops: fake.async (Device echo), fake.wait (Device cooperative delay,
body.wait_ms defaults to 1000, capped at 5000), fake.async_error,
fake.async_traced, fake.async_panic, fake.async_invalid, fake.async_profile.
The profile fixture requires a private Rust test actor; it does not create one
through the public ABI. Existing Sync ops and BUDGET_OPS are unchanged.

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
or any extra C export. Retired actors are removed from the strong registry.
Fixture slots increase independently of registry length, never reuse identities,
and refuse allocation at the 48-bit slot boundary (generation stays 1). Real
Store/key teardown remains its owner card's responsibility, not an FFI claim.

The test_ops feature and unit tests contain isolated fake handlers; abi_major_bump
reports 2.0 from both version and capabilities while the public header stays 1.0.
Both features are forbidden whenever debug_assertions is false. Downstream CORE-41
owns CI configuration; this crate supplies reproducible commands and fixtures only.
