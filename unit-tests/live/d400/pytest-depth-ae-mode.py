# License: Apache 2.0. See LICENSE file in root directory.
# Copyright(c) 2023 RealSense, Inc. All Rights Reserved.

# RS2_OPTION_DEPTH_AUTO_EXPOSURE_MODE registration:
#   D455:                       FW >= 5.15.0.0
#   All other D400s except D415: FW >= 5.17.3.20 (RSDSO-21571 widening)
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


@pytest.fixture
def depth_sensor(test_device_wrapped):
    dev, _ = test_device_wrapped
    name = dev.get_info(rs.camera_info.name)
    if "D415" in name:
        pytest.skip(f"AE mode is not supported on D415 family ({name})")
    min_fw = D455_MIN_FW if "D455" in name else OTHERS_MIN_FW
    require_min_fw_version(dev, min_fw, "DEPTH_AUTO_EXPOSURE_MODE")
    return dev.first_depth_sensor()


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


def test_option_absent_on_d415(test_device_wrapped):
    """Positive verification of the D415 exclusion: option must NOT be registered.

    Runs alongside the D400* parametrization but only asserts on D415 devices;
    other SKUs skip. This is the counterpart to the fixture-level D415 skip in
    the tests above — those confirm the option works where it's supposed to,
    this one confirms it's absent where it isn't.
    """
    dev, _ = test_device_wrapped
    name = dev.get_info(rs.camera_info.name)
    if "D415" not in name:
        pytest.skip(f"Negative case runs on D415 only (device is {name})")
    depth_sensor = dev.first_depth_sensor()
    assert rs.option.auto_exposure_mode not in depth_sensor.get_supported_options(), \
        f"RS2_OPTION_DEPTH_AUTO_EXPOSURE_MODE unexpectedly registered on {name}"
