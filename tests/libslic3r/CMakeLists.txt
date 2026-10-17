get_filename_component(_TEST_NAME ${CMAKE_CURRENT_LIST_DIR} NAME)

add_executable(${_TEST_NAME}_tests 
	${_TEST_NAME}_tests.cpp
	test_3mf.cpp
	test_aabbindirect.cpp
	test_clipper_offset.cpp
	test_clipper_utils.cpp
	test_config.cpp
	test_elephant_foot_compensation.cpp
	test_geometry.cpp
	test_placeholder_parser.cpp
	test_polygon.cpp
	test_mutable_polygon.cpp
	test_mutable_priority_queue.cpp
	test_stl.cpp
	test_meshboolean.cpp
	test_marchingsquares.cpp
	test_timeutils.cpp
	test_voronoi.cpp
    test_optimizers.cpp
    test_png_io.cpp
    test_timeutils.cpp
    test_indexed_triangle_set.cpp
    test_debounce.cpp
    ../libnest2d/printer_parts.cpp
	)

if (TARGET OpenVDB::openvdb)
    target_sources(${_TEST_NAME}_tests PRIVATE test_hollowing.cpp)
endif()
    
target_link_libraries(${_TEST_NAME}_tests test_common libslic3r)
# The current 3MF path also uses host utilities from libslic3r_gui.
if (TARGET libslic3r_gui)
# Focused native configuration/3MF regressions without unrelated SLA test APIs.
add_executable(printfins_integration_tests
    libslic3r_tests.cpp
    test_config.cpp
    test_3mf.cpp
    ../printfins/native-options-group.cpp
)
target_link_libraries(printfins_integration_tests test_common libslic3r_gui)
target_include_directories(printfins_integration_tests PRIVATE "$<TARGET_PROPERTY:libslic3r_gui,INCLUDE_DIRECTORIES>")
if (MSVC)
    target_link_options(printfins_integration_tests PRIVATE /DEBUG:FULL /OPT:REF /OPT:ICF)
endif()
if (WIN32)
    target_link_libraries(printfins_integration_tests bcrypt)
endif()
set_property(TARGET printfins_integration_tests PROPERTY FOLDER "tests")
endif()
set_property(TARGET ${_TEST_NAME}_tests PROPERTY FOLDER "tests")

if (WIN32)
    # bambustudio_copy_dlls now requires 4 args (target, config, postfix,
    # output_dlls); legacy 1-arg call sites in tests/* predate that signature
    # change.  Test executables link libslic3r and do not need the heavyweight
    # OCCT / GMP / MPFR / FFmpeg DLL bundle, so skip the copy step here.
    # Run tests with PATH pointing at deps build dir if extra DLLs are needed.
    # bambustudio_copy_dlls(${_TEST_NAME}_tests <config> <postfix> <out>)
endif()

# catch_discover_tests(${_TEST_NAME}_tests TEST_PREFIX "${_TEST_NAME}: ")
add_test(${_TEST_NAME}_tests ${_TEST_NAME}_tests ${CATCH_EXTRA_ARGS})
