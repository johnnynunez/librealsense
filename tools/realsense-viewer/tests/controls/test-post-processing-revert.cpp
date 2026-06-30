// License: Apache 2.0. See LICENSE file in root directory.
// Copyright(c) 2026 RealSense, Inc. All Rights Reserved.

#include "viewer-test-helpers.h"

#include <string>


// Regression test for RSDEV-12488 / RSDEV-12502: a post-processing filter control set to a
// non-default value must keep that value in the UI. PR #15029 made UI option writes
// asynchronous; software filters (decimation, rotation, ...) emit no on_options_changed echo,
// so the control model's cached value was never refreshed after the write. Once the ~2 s
// user-request mask expired the control snapped back to its previous (config-restored) value
// even though the effect was applied (e.g. decimation magnitude -> output decimated by 5 but
// the slider showing 2).
//
// The cached value->as_float is exactly what the slider displays after the mask expires, and it
// is independent of the mask timing — so we assert on it directly rather than racing the 2 s mask
// (and we avoid re-reading through the UI, which would re-activate the slider and reset the mask).
VIEWER_TEST( "controls", "post_processing_value_persists" )
{
    auto & model = test.find_first_device_or_exit();

    bool tested = false;
    for( auto && sub : model.subdevices )
    {
        // Decimation (a software post-processing filter) lives on the depth sensor
        auto pb = test.find_post_processing_filter( sub, RS2_OPTION_FILTER_MAGNITUDE );
        if( !pb )
            continue;
        rs2::option_model * om = pb->get_option_model( RS2_OPTION_FILTER_MAGNITUDE );

        test.click_stream_toggle_on( model, sub );
        test.sleep( 2.0f );

        test.expand_sensor_panel( model, sub );
        test.expand_post_processing( model, sub );
        test.enable_post_processing( model, sub );
        test.enable_post_processing_filter( model, sub, pb );
        test.expand_post_processing_filter( model, sub, pb );

        // The viewer persists filter options to the config file, so the start value varies between
        // runs — pick a target that differs from it so a revert would be observable.
        const float cur = pb->get_block()->get_option( RS2_OPTION_FILTER_MAGNITUDE );
        const std::string target = ( cur >= 4.f ) ? "2" : "6";
        const float target_f = std::stof( target );

        test.set_post_processing_value( model, sub, pb, RS2_OPTION_FILTER_MAGNITUDE, target );

        // The write is async — wait until the filter actually applied the new value.
        IM_CHECK( test.wait_until( 20, 0.25f, [&] {
            return pb->get_block()->get_option( RS2_OPTION_FILTER_MAGNITUDE ) == target_f;
        } ) );

        // The control model's cached value must track the applied value (this is what the slider
        // shows once the user-request mask expires). Before the fix it stayed at the stale snapshot
        // and the control reverted. Allow a few frames for draw_option to drain the write
        // completion and refresh the cached value.
        IM_CHECK( test.wait_until( 20, 0.25f, [&] {
            return om->value->as_float == target_f;
        } ) );

        test.click_stream_toggle_off( model, sub );
        test.sleep( 1.0f );
        tested = true;
        break;
    }

    // No depth/decimation device present — nothing to validate, but don't fail the suite
    if( !tested )
        IM_CHECK( true );
}
