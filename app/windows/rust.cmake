function(fml_configure_core)
include("${FLUTTER_MANAGED_DIR}/ephemeral/generated_config.cmake")
# WIN-01: no Rust test features, static CRT, fail the native build on Cargo error.
if(NOT CMAKE_SIZEOF_VOID_P EQUAL 8 OR NOT FLUTTER_TARGET_PLATFORM STREQUAL "windows-x64")
  message(FATAL_ERROR "WIN-01 supports windows-x64 only")
endif()
set(FML_CARGO_DIR "${CMAKE_BINARY_DIR}/rust")
set(FML_DLL "${FML_CARGO_DIR}/x86_64-pc-windows-msvc/release/fmlcore.dll")
add_custom_target(fml_core_build
  COMMAND ${CMAKE_COMMAND} -E env ${FLUTTER_TOOL_ENVIRONMENT}
    "${FLUTTER_ROOT}/bin/cache/dart-sdk/bin/dart.exe"
    "${CMAKE_CURRENT_SOURCE_DIR}/build_core.dart" "${FML_CARGO_DIR}"
  BYPRODUCTS "${FML_DLL}"
  VERBATIM
)
add_dependencies(${BINARY_NAME} fml_core_build)
install(FILES "${FML_DLL}" DESTINATION "${CMAKE_INSTALL_PREFIX}" COMPONENT Runtime)
# PDBs remain in build output for symbol archival, not Runtime installation.
endfunction()
fml_configure_core()
