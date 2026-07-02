# Exercises the pytest-timeout + pytest-retry interaction. Run under
# --retries=1 --timeout=3.
#
# pytest-timeout arms its per-item timer in `pytest_runtest_protocol`, whose
# yield covers setup + all call attempts + teardown. pytest-retry re-invokes
# `pytest_runtest_call` from inside `pytest_runtest_makereport`, still under
# that outer yield, so without a reset each retry shares the original --timeout
# budget with the failed first attempt.
#
# This test consumes ~2s per attempt on a 3s budget. Without the conftest
# reset, attempt 2 has ~1s of budget left after attempt 1 and gets killed
# mid-sleep with a `+++ Timeout +++` banner (os._exit(1) → whole subprocess
# dies). With the reset, each attempt gets a fresh 3s and the test passes on
# attempt 2.
import time

_attempt = 0


def test_timeout_resets_between_retry_attempts():
    global _attempt
    _attempt += 1
    time.sleep(2.0)
    if _attempt == 1:
        assert False, "intentional first-attempt failure"
