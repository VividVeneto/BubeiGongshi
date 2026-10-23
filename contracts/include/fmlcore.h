#ifndef FMLCORE_H
#define FMLCORE_H
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
#define FML_ABI_MAJOR 1
#define FML_ABI_MINOR 0
/* Input pointers must be readable, output pointers writable and aligned.
 * op is NUL-terminated UTF-8; req is immutable UTF-8 JSON, at most 16 MiB.
 * Copy a returned buffer before freeing it exactly once; never edit its fields.
 * NULL is rejected where required. Invalid non-NULL addresses are caller UB. */
typedef struct { uint8_t *ptr; size_t len; uint64_t allocation_id; } FmlBuf;
typedef uint64_t FmlHandle;
typedef void (*FmlCompletion)(uint64_t job_id, FmlBuf result, void *user_data);
uint32_t fml_abi_version(void);
FmlBuf fml_capabilities(void);
int32_t fml_call(const char *op, const uint8_t *req, size_t req_len, FmlBuf *out);
int32_t fml_submit(const char *op, const uint8_t *req, size_t req_len, uint64_t *job_id);
int32_t fml_cancel(uint64_t job_id);
int32_t fml_register_completion(FmlCompletion cb, void *user_data);
int32_t fml_free_buffer(FmlBuf buf);
int32_t fml_close_handle(FmlHandle h);
#ifdef __cplusplus
}
#endif
#endif
