"""Tests for risalah/utils.py — retry, run_parallel, cache_check, make_cache_key."""

import json
import os
import time

import pytest

from risalah.utils import cache_check, make_cache_key, retry, run_parallel


class TestRetry:
    def test_retry_success_first_try(self):
        call_count = 0

        @retry(max_attempts=3, delay=0)
        def ok():
            nonlocal call_count
            call_count += 1
            return "done"

        assert ok() == "done"
        assert call_count == 1

    def test_retry_success_after_retries(self):
        call_count = 0

        @retry(max_attempts=3, delay=0)
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "ok"

        assert flaky() == "ok"
        assert call_count == 3

    def test_retry_fails_after_exhausted(self):
        call_count = 0

        @retry(max_attempts=3, delay=0)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("always")

        with pytest.raises(ValueError, match="always"):
            always_fail()
        assert call_count == 3

    def test_retry_custom_exceptions(self):
        @retry(max_attempts=2, delay=0, exceptions=(TypeError,))
        def raises_value_error():
            raise ValueError("wrong exception")

        with pytest.raises(ValueError):
            raises_value_error()


class TestRunParallel:
    def test_parallel_returns_both_results(self):
        def a():
            time.sleep(0.05)
            return "A"

        def b():
            time.sleep(0.05)
            return "B"

        ra, rb = run_parallel(a, b, timeout=5)
        assert ra == "A"
        assert rb == "B"

    def test_parallel_first_exception(self):
        def a():
            raise ValueError("A fail")

        def b():
            return "B"

        with pytest.raises(ValueError, match="A fail"):
            run_parallel(a, b, timeout=5)


class TestCacheCheck:
    def test_cache_miss_creates_file(self, tmp_path):
        calls = []

        def loader():
            calls.append(1)
            return {"data": "fresh"}

        result = cache_check(str(tmp_path), "test_key", loader)
        assert result == {"data": "fresh"}
        assert len(calls) == 1
        assert os.path.exists(os.path.join(tmp_path, "cache_test_key.json"))

    def test_cache_hit_skips_loader(self, tmp_path):
        cache_path = os.path.join(tmp_path, "cache_test_key.json")
        with open(cache_path, "w") as f:
            json.dump({"data": "cached"}, f)

        calls = []

        def loader():
            calls.append(1)
            return {"data": "fresh"}

        result = cache_check(str(tmp_path), "test_key", loader)
        assert result == {"data": "cached"}
        assert len(calls) == 0

    def test_cache_overwrite(self, tmp_path):
        cache_path = os.path.join(tmp_path, "cache_test_key.json")
        with open(cache_path, "w") as f:
            json.dump({"data": "old"}, f)

        def loader():
            return {"data": "new"}

        result = cache_check(str(tmp_path), "test_key", loader, overwrite=True)
        assert result == {"data": "new"}


class TestMakeCacheKey:
    def test_consistent_hash(self):
        assert make_cache_key("a", "b") == make_cache_key("a", "b")

    def test_different_inputs(self):
        assert make_cache_key("a") != make_cache_key("b")

    def test_includes_all_parts(self):
        k1 = make_cache_key("x", "y")
        k2 = make_cache_key("x")
        assert k1 != k2
