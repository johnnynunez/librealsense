// License: Apache 2.0. See LICENSE file in root directory.
// Copyright(c) 2026 RealSense, Inc. All Rights Reserved.

#include "../catch.h"
#include <librealsense2/rs.hpp>
#include <librealsense2/hpp/rs_internal.hpp>

using namespace rs2;

// video_stream_profile::operator== must additionally compare width and height,
// unlike the base stream_profile::operator== (which only compares index/type/format/fps).
// A software device is used so the test needs no connected hardware.

TEST_CASE( "video_stream_profile operator==", "[software-device]" )
{
    rs2_intrinsics intrinsics{};

    auto dev = std::make_shared< software_device >();
    auto sensor = dev->add_sensor( "software_sensor" );

    // Two profiles that share index/type/format/fps but differ in resolution:
    // equal as base stream_profiles, but must NOT be equal as video_stream_profiles.
    sensor.add_video_stream( { RS2_STREAM_DEPTH, 0, 0, 1280, 720, 30, 2, RS2_FORMAT_Z16, intrinsics } );
    sensor.add_video_stream( { RS2_STREAM_DEPTH, 0, 0,  640, 480, 30, 2, RS2_FORMAT_Z16, intrinsics } );
    // A third profile identical to the first in every attribute (a distinct object).
    sensor.add_video_stream( { RS2_STREAM_DEPTH, 0, 0, 1280, 720, 30, 2, RS2_FORMAT_Z16, intrinsics } );

    std::vector< stream_profile > stream_profiles;
    REQUIRE_NOTHROW( stream_profiles = sensor.get_stream_profiles() );
    REQUIRE( stream_profiles.size() == 3 );

    video_stream_profile hd     = stream_profiles[0].as< video_stream_profile >();
    video_stream_profile vga    = stream_profiles[1].as< video_stream_profile >();
    video_stream_profile hd_dup = stream_profiles[2].as< video_stream_profile >();

    // Capture results in named bools: video_stream_profile is implicitly convertible to
    // bool, so comparing the profiles inline makes Catch print a misleading "1 == 1".
    bool base_equal = static_cast< stream_profile & >( hd ) == static_cast< stream_profile & >( vga );
    bool video_equal_diff_resolution = ( hd == vga );
    bool video_equal_same_attributes = ( hd == hd_dup );

    // Same index/type/format/fps -> the base stream_profile comparison treats them as equal
    REQUIRE( base_equal );

    // ... but different width/height -> the video_stream_profile comparison must differ
    REQUIRE_FALSE( video_equal_diff_resolution );

    // Identical attributes including resolution -> video_stream_profile comparison must match
    REQUIRE( video_equal_same_attributes );
}
