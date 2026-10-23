use super::*;
#[test]
fn idle_registration_and_no_phantom_jobs() {
    let req = br#"{"v":1,"trace_id":"11111111111111111111111111111111","body":{}}"#;
    let mut id = 99;
    assert_eq!(fml_register_completion(None, std::ptr::null_mut()), 0);
    // SAFETY: Static valid C name/request and writable aligned id.
    unsafe {
        assert_eq!(
            fml_submit(c"fake.echo".as_ptr(), req.as_ptr(), req.len(), &mut id),
            -1
        );
        assert_eq!(id, 0);
        assert_eq!(
            fml_register_completion(Some(test_callback), 17usize as *mut c_void),
            0
        );
        assert_eq!(registered_user_data(), Some(17));
        assert_eq!(
            fml_submit(c"fake.echo".as_ptr(), req.as_ptr(), req.len(), &mut id),
            -2
        );
        assert_eq!(id, 0);
        assert_eq!(
            fml_submit(c"missing".as_ptr(), req.as_ptr(), req.len(), &mut id),
            -2
        );
        assert_eq!(
            fml_submit(c"missing".as_ptr(), b"{}".as_ptr(), 2, &mut id),
            -1
        );
        assert_eq!(
            fml_submit(
                c"missing".as_ptr(),
                req.as_ptr(),
                req.len(),
                std::ptr::null_mut()
            ),
            -1
        );
        assert_eq!(
            fml_submit(c"missing".as_ptr(), std::ptr::null(), 0, &mut id),
            -1
        );
        assert_eq!(
            fml_submit(
                c"missing".as_ptr(),
                req.as_ptr(),
                16 * 1024 * 1024 + 1,
                &mut id
            ),
            -1
        );
    }
    assert_eq!(fml_cancel(id), -4);
    assert_eq!(fml_cancel(u64::MAX), -4);
    assert_eq!(
        fml_register_completion(Some(test_callback), 19usize as *mut c_void),
        0
    );
    assert_eq!(registered_user_data(), Some(19));
    assert_eq!(fml_register_completion(None, std::ptr::null_mut()), 0);
    assert_eq!(registered_user_data(), None);
}
