"""Tests for the two pieces of real logic: the UFW log parser and the
per-IP burst rate limiter."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ufw_watcher import parse_block_line, RateLimiter, GeoCache  # noqa: E402


class TestUfwParser:
    def test_parses_a_real_block_line(self):
        # Real UFW order: SRC ... PROTO ... DPT (PROTO before DPT).
        line = (
            "Jun 23 10:00:00 host kernel: [12345.6] [UFW BLOCK] IN=eth0 OUT= "
            "MAC=... SRC=203.0.113.7 DST=10.0.0.1 LEN=40 TTL=52 ID=1 "
            "PROTO=TCP SPT=54321 DPT=22 WINDOW=1024 SYN"
        )
        assert parse_block_line(line) == ("203.0.113.7", "22", "TCP")

    def test_udp_field_order_independent(self):
        line = "[UFW BLOCK] SRC=198.51.100.42 DST=x PROTO=UDP DPT=53"
        assert parse_block_line(line) == ("198.51.100.42", "53", "UDP")

    def test_non_block_line_ignored(self):
        assert parse_block_line("Jun 23 some unrelated kernel message") is None
        assert parse_block_line("[UFW ALLOW] SRC=1.2.3.4 DPT=80 PROTO=TCP") is None


class TestRateLimiter:
    def test_one_per_window_default(self):
        rl = RateLimiter(window_seconds=60, max_attempts=1)
        assert rl.allow("1.1.1.1", now=1000) is True
        assert rl.allow("1.1.1.1", now=1030) is False   # within window
        assert rl.allow("1.1.1.1", now=1061) is True    # window elapsed

    def test_burst_allows_up_to_max(self):
        rl = RateLimiter(window_seconds=60, max_attempts=3)
        assert rl.allow("2.2.2.2", now=0) is True
        assert rl.allow("2.2.2.2", now=1) is True
        assert rl.allow("2.2.2.2", now=2) is True
        assert rl.allow("2.2.2.2", now=3) is False      # 4th in window suppressed
        assert rl.allow("2.2.2.2", now=61) is True       # oldest aged out

    def test_distinct_ips_independent(self):
        rl = RateLimiter(window_seconds=60, max_attempts=1)
        assert rl.allow("3.3.3.3", now=0) is True
        assert rl.allow("4.4.4.4", now=0) is True

    def test_memory_is_bounded_by_sweep(self):
        rl = RateLimiter(window_seconds=10, max_attempts=1)
        # Many one-off IPs early on.
        for i in range(1000):
            rl.allow(f"10.0.0.{i}", now=0)
        assert len(rl) == 1000
        # A later call past the window triggers the sweep, evicting expired IPs.
        rl.allow("10.1.1.1", now=100)
        assert len(rl) == 1


class TestGeoCache:
    def test_disabled_returns_unknown_without_network(self):
        geo = GeoCache(enabled=False)
        assert geo.country_for("8.8.8.8") == "Unknown"

    def test_cache_hit_avoids_relookup(self):
        geo = GeoCache(enabled=True, ttl_seconds=3600)
        geo._cache["9.9.9.9"] = (1000.0, "Testland")
        # Within TTL -> served from cache, no network call.
        assert geo.country_for("9.9.9.9", now=1500) == "Testland"
