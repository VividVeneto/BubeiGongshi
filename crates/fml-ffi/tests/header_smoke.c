#include "fmlcore.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void done(uint64_t job, FmlBuf buf, void *user) { (void)job; (void)buf; (void)user; assert(0); }
int main(void) {
    const uint8_t req[] = "{\"v\":1,\"trace_id\":\"11111111111111111111111111111111\",\"body\":{}}";
    FmlBuf buf = fml_capabilities();
    assert(fml_abi_version() == ((FML_ABI_MAJOR << 16) | FML_ABI_MINOR));
    assert(buf.ptr && buf.len && buf.allocation_id);
    assert(fml_free_buffer(buf) == 0); assert(fml_free_buffer(buf) == -1);
    assert(fml_call("missing",req,sizeof(req)-1,&buf) == -2);
    assert(fml_free_buffer(buf) == 0);
    assert(fml_register_completion(done,NULL) == 0);
    uint64_t job = 99;
    assert(fml_submit("missing",req,sizeof(req)-1,&job) == -2 && job == 0);
    assert(fml_cancel(job) == -4);
    assert(fml_close_handle(0) == -4);
    assert(fml_register_completion(NULL,NULL) == 0);
    puts("pure-C eight-symbol compile/link/run PASS"); return 0;
}
