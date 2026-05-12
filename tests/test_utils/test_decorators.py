"""Tests for reef_tools.utils.decorators."""

import time

import pytest

from reef_tools.utils.decorators import cache_result, timer


class TestTimer:
    """Tests for the @timer decorator."""

    def test_timer_returns_result(self):
        """Timer should not interfere with the return value."""

        @timer
        def add(a: int, b: int) -> int:
            return a + b

        result = add(3, 4)
        assert result == 7

    def test_timer_preserves_metadata(self):
        """Timer should preserve function name and docstring."""

        @timer
        def my_func() -> str:
            """A docstring."""
            return "ok"

        assert my_func.__name__ == "my_func"
        assert my_func.__doc__ == "A docstring."

    def test_timer_prints_elapsed(self, capsys):
        """Timer should print elapsed time."""

        @timer
        def fast() -> None:
            return None

        fast()
        captured = capsys.readouterr()
        assert "fast took " in captured.out
        assert "s" in captured.out

    def test_timer_with_sleep(self, capsys):
        """Timer should measure real elapsed time."""

        @timer
        def nap(n: float) -> str:
            time.sleep(n)
            return "done"

        result = nap(0.05)
        captured = capsys.readouterr()

        assert result == "done"
        assert "nap took " in captured.out
        # Should be around 0.05s
        line = captured.out.strip()
        elapsed_str = line.split("took ")[1].rstrip("s")
        elapsed = float(elapsed_str)
        assert 0.04 <= elapsed <= 0.15  # generous range for CI


class TestCacheResult:
    """Tests for the @cache_result decorator."""

    def test_cache_result_returns_correct_value(self):
        """Caching should not change the result."""

        call_count = 0

        @cache_result
        def expensive(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        assert expensive(5) == 10
        assert call_count == 1

    def test_cache_result_caches(self):
        """Second call with same args should use cached result."""

        call_count = 0

        @cache_result
        def expensive(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        assert expensive(5) == 10
        assert expensive(5) == 10
        assert call_count == 1  # second call was cached

    def test_cache_result_different_args(self):
        """Different args should not use the cache for different args."""

        call_count = 0

        @cache_result
        def expensive(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        assert expensive(5) == 10
        assert expensive(10) == 20
        assert call_count == 2  # both calls computed

    def test_cache_result_preserves_metadata(self):
        """Cache should preserve function metadata."""

        @cache_result
        def cached_func() -> str:
            """Docstring here."""
            return "ok"

        assert cached_func.__name__ == "cached_func"
        assert cached_func.__doc__ == "Docstring here."

    def test_cache_result_unhashable_args(self):
        """Cache should raise TypeError for unhashable arguments (lru_cache behavior)."""

        @cache_result
        def process(items: list) -> int:
            return len(items)

        with pytest.raises(TypeError):
            process([1, 2, 3])
