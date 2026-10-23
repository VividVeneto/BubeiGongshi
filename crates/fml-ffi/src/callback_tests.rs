use super::*;
// SAFETY: Unit-only callback follows the same buffer ownership and lifetime protocol.
pub(crate) unsafe extern "C" fn done(id: u64, buf: FmlBuf, user: *mut c_void) {
    crate::jobs::tests::receive(id, buf, user as usize);
}
