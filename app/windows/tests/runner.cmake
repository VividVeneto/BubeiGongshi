# Opt-in native integration test: actual Flutter engine and production host.
option(FML_RUNNER_TESTS "Build WIN-01 native integration tests" OFF)
if(FML_RUNNER_TESTS)
  add_executable(win01_runner_test
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/runner_test.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/runner/flutter_window.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/runner/win32_window.cpp"
    "${FLUTTER_MANAGED_DIR}/generated_plugin_registrant.cc")
  apply_standard_settings(win01_runner_test)
  target_include_directories(win01_runner_test PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
  target_link_libraries(win01_runner_test PRIVATE flutter flutter_wrapper_app flutter_wrapper_plugin dwmapi comctl32)
  set_target_properties(win01_runner_test PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/runner/$<CONFIG>")
endif()
