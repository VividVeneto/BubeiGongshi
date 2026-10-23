/* Test double only. Exercises Dart wire/ownership races, NOT Rust pool acceptance. */
#include <windows.h>
#include <stdlib.h>
#include <string.h>
#include "fmlcore.h"
#define API __declspec(dllexport)
static char response[65536], request_copy[65536];
static int result_status, submit_mode;
static LONG outstanding, frees, bad_free, cancels, unregisters;
static uint64_t next_job;
static FmlCompletion completion;
static void *context;
static HANDLE barrier;
static SRWLOCK lock = SRWLOCK_INIT;
static FmlBuf allocations[512];
static int active[512];
static uint64_t serial;
API void fixture_configure(const char *json, int status, int mode) {
  strcpy_s(response, sizeof(response), json);
  result_status = status;
  submit_mode = mode;
  if (!barrier) barrier = CreateEventW(NULL, TRUE, FALSE, NULL);
  ResetEvent(barrier);
}
API int fixture_metric(int key) {
  if (key == 0) return outstanding;
  if (key == 1) return frees;
  if (key == 2) return bad_free;
  if (key == 3) return cancels;
  if (key == 4) return unregisters;
  return (int)next_job;
}
API const char *fixture_request(void) { return request_copy; }
API void fixture_release(void) { SetEvent(barrier); }
static FmlBuf make_buffer(void) {
  FmlBuf b = {0};
  b.len = strlen(response);
  b.ptr = malloc(b.len);
  if (!b.ptr) abort();
  memcpy(b.ptr, response, b.len);
  AcquireSRWLockExclusive(&lock);
  b.allocation_id = ++serial;
  allocations[b.allocation_id % 512] = b;
  InterlockedIncrement(&outstanding);
  ReleaseSRWLockExclusive(&lock);
  return b;
}
API void fixture_complete(uint64_t id) {
  FmlBuf b = make_buffer();
  active[id % 512] = 0;
  completion(id, b, context);
}
uint32_t fml_abi_version(void) { return 1u << 16; }
FmlBuf fml_capabilities(void) { return make_buffer(); }
int32_t fml_call(const char *op, const uint8_t *req, size_t len, FmlBuf *out) {
  (void)op;
  if (len >= sizeof(request_copy)) return -1;
  memcpy(request_copy, req, len);
  request_copy[len] = 0;
  if (submit_mode != 9) *out = make_buffer();
  return result_status;
}
int32_t fml_submit(const char *op, const uint8_t *req, size_t len, uint64_t *id) {
  (void)op; (void)req; (void)len;
  if (result_status < 0) return result_status;
  *id = ++next_job;
  active[*id % 512] = 1;
  if (submit_mode == 0) fixture_complete(*id);
  return 0;
}
int32_t fml_cancel(uint64_t id) {
  InterlockedIncrement(&cancels);
  if (submit_mode == 2) WaitForSingleObject(barrier, INFINITE);
  if (submit_mode == 3) { fixture_complete(id); return 1; }
  if (!active[id % 512]) return 1;
  active[id % 512] = 0;
  return 0;
}
int32_t fml_register_completion(FmlCompletion cb, void *data) {
  int i;
  if (!cb) InterlockedIncrement(&unregisters);
  if (outstanding) return -6;
  for (i = 0; i < 512; ++i) if (active[i]) return -6;
  completion = cb;
  context = data;
  return 0;
}
int32_t fml_free_buffer(FmlBuf b) {
  int valid;
  AcquireSRWLockExclusive(&lock);
  FmlBuf *stored = &allocations[b.allocation_id % 512];
  valid = stored->ptr == b.ptr && stored->allocation_id == b.allocation_id && stored->len == b.len;
  if (valid) { stored->ptr = NULL; InterlockedDecrement(&outstanding); InterlockedIncrement(&frees); }
  else InterlockedIncrement(&bad_free);
  ReleaseSRWLockExclusive(&lock);
  if (!valid) return -1;
  free(b.ptr);
  return 0;
}
int32_t fml_close_handle(FmlHandle h) { (void)h; abort(); }
