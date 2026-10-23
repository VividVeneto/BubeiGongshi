#ifndef BUBEIGONGSHI_FMLCORE_H
#define BUBEIGONGSHI_FMLCORE_H

#define FML_ABI_MAJOR 1
#define FML_ABI_MINOR 0
#define FML_STATUS_KIND_COUNT 8

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    uint64_t len;
    uint8_t *ptr;
} FmlBuf;

typedef void (*FmlWriteFn)(const uint8_t *bytes, FmlBuf *out);

typedef struct FmlContext FmlContext;

uint32_t fml_abi_version(void);
FmlStatus fml_context_create(FmlContext **out);

#ifdef __cplusplus
}
#endif

#endif
