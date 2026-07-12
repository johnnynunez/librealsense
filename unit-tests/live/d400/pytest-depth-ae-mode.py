# License: Apache 2.0. See LICENSE file in root directory.
# Copyright(c) 2023 RealSense, Inc. All Rights Reserved.

# RS2_OPTION_DEPTH_AUTO_EXPOSURE_MODE is registered on non-rolling-shutter D400
# devices only. Rolling-shutter SKUs are excluded via CAP_ROLLING_SHUTTER (GVD
# byte 166). Minimum FW: 5.15.0.0 on D455, 5.17.3.20 on the other SKUs.
# See src/ds/d400/d400-device.cpp (search "DEPTH AUTO EXPOSURE MODE").

import pytest
import pyrealsense2 as rs
import pyrsutils as rsutils
from rspy.pytest.device_helpers import require_min_fw_version
import logging
log = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.device_each("D400*"),
]

REGULAR = 0.0
ACCELERATED = 1.0

D455_MIN_FW    = rsutils.version(5, 15, 0, 0)
OTHERS_MIN_FW  = rsutils.version(5, 17, 3, 20)

# Per src/ds/d400/d400-device.cpp:239 — rolling-shutter D400 family, used for the
# positive-absence test below.
ROLLING_SHUTTER_D400_NAMES = ("D400", "D410", "D415", "D405")


@pytest.fixture
def depth_sensor(test_device_wrapped):
    dev, _ = test_device_wrapped
    name = dev.get_info(rs.camera_info.name)
    min_fw = D455_MIN_FW if "D455" in name else OTHERS_MIN_FW
    require_min_fw_version(dev, min_fw, "DEPTH_AUTO_EXPOSURE_MODE")
    depth = dev.first_depth_sensor()
    # Track the SDK's own runtime signal rather than duplicating its exclusion
    # logic — this makes the test tolerant of future SDK-side changes to which
    # SKUs get the option registered.
    if rs.option.auto_exposure_mode not in depth.get_supported_options():
        pytest.skip(f"RS2_OPTION_DEPTH_AUTO_EXPOSURE_MODE not registered on {name}")
    return depth


def test_verify_camera_ae_mode_default_is_regular(depth_sensor):
    assert depth_sensor.get_option(rs.option.auto_exposure_mode) == REGULAR


def test_verify_can_set_when_auto_exposure_on(depth_sensor):
    depth_sensor.set_option(rs.option.enable_auto_exposure, True)
    assert bool(depth_sensor.get_option(rs.option.enable_auto_exposure)) == True
    depth_sensor.set_option(rs.option.auto_exposure_mode, ACCELERATED)
    assert depth_sensor.get_option(rs.option.auto_exposure_mode) == ACCELERATED
    depth_sensor.set_option(rs.option.auto_exposure_mode, REGULAR)
    assert depth_sensor.get_option(rs.option.auto_exposure_mode) == REGULAR


def test_set_during_idle_mode(depth_sensor):
    depth_sensor.set_option(rs.option.enable_auto_exposure, False)
    assert bool(depth_sensor.get_option(rs.option.enable_auto_exposure)) == False
    depth_sensor.set_option(rs.option.auto_exposure_mode, ACCELERATED)
    assert depth_sensor.get_option(rs.option.auto_exposure_mode) == ACCELERATED
    depth_sensor.set_option(rs.option.auto_exposure_mode, REGULAR)
    assert depth_sensor.get_option(rs.option.auto_exposure_mode) == REGULAR


def test_set_during_streaming_mode_not_allowed(depth_sensor):
    # Reset option to REGULAR
    depth_sensor.set_option(rs.option.enable_auto_exposure, False)
    assert bool(depth_sensor.get_option(rs.option.enable_auto_exposure)) == False
    depth_sensor.set_option(rs.option.auto_exposure_mode, REGULAR)
    assert depth_sensor.get_option(rs.option.auto_exposure_mode) == REGULAR
    # Start streaming
    depth_profile = next((p for p in depth_sensor.profiles if p.stream_type() == rs.stream.depth), None)
    if depth_profile is None:
        pytest.skip("Sensor does not expose a depth-stream profile")
    depth_sensor.open(depth_profile)
    depth_sensor.start(lambda x: None)
    try:
        with pytest.raises(Exception):
            depth_sensor.set_option(rs.option.auto_exposure_mode, ACCELERATED)
        assert depth_sensor.get_option(rs.option.auto_exposure_mode) == REGULAR
    finally:
        depth_sensor.stop()
        depth_sensor.close()


def test_option_absent_on_rolling_shutter_sku(test_device_wrapped):
    """Positive verification of the rolling-shutter exclusion.

    The SDK gates registration on `!CAP_ROLLING_SHUTTER` (see d400-device.cpp
    around the DEPTH AUTO EXPOSURE MODE registration). This test asserts the
    option is genuinely absent on any of the D400 RS-family devices — the
    counterpart to the fixture-level skip above.
    """
    dev, _ = test_device_wrapped
    name = dev.get_info(rs.camera_info.name)
    if not any(rs_name in name for rs_name in ROLLING_SHUTTER_D400_NAMES):
        pytest.skip(f"Negative case runs on rolling-shutter D400 SKUs only (device is {name})")
    depth_sensor = dev.first_depth_sensor()
    assert rs.option.auto_exposure_mode not in depth_sensor.get_supported_options(), \
        f"RS2_OPTION_DEPTH_AUTO_EXPOSURE_MODE unexpectedly registered on {name}"
