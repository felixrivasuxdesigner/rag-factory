"""
Rate Limiting Framework for RAG Factory

Provides configurable, per-source rate limiting to comply with API limits
and prevent service blocking. Supports multiple strategies:
- Requests per day/hour/minute
- Minimum delay between requests
- Burst allowance
- Automatic backoff on 429 responses

Designed to be connector-agnostic and easily configurable per data source.
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RateLimitConfig:
    """Configuration for rate limiting parameters."""

    def __init__(
        self,
        requests_per_day: Optional[int] = None,
        requests_per_hour: Optional[int] = None,
        requests_per_minute: Optional[int] = None,
        min_delay_between_requests: float = 0.0,
        burst_limit: int = 1,
        retry_after_429: bool = True,
        backoff_factor: float = 2.0
    ):
        """
        Initialize rate limit configuration.

        Args:
            requests_per_day: Maximum requests allowed per day
            requests_per_hour: Maximum requests allowed per hour
            requests_per_minute: Maximum requests allowed per minute
            min_delay_between_requests: Minimum seconds to wait between requests
            burst_limit: Number of requests allowed in quick succession
            retry_after_429: Whether to automatically retry after 429 response
            backoff_factor: Multiplier for exponential backoff (default 2.0)
        """
        self.requests_per_day = requests_per_day
        self.requests_per_hour = requests_per_hour
        self.requests_per_minute = requests_per_minute
        self.min_delay = min_delay_between_requests
        self.burst_limit = burst_limit
        self.retry_after_429 = retry_after_429
        self.backoff_factor = backoff_factor

    @classmethod
    def from_dict(cls, config: Dict) -> 'RateLimitConfig':
        """Create config from dictionary."""
        return cls(
            requests_per_day=config.get('requests_per_day'),
            requests_per_hour=config.get('requests_per_hour'),
            requests_per_minute=config.get('requests_per_minute'),
            min_delay_between_requests=config.get('min_delay', 0.0),
            burst_limit=config.get('burst_limit', 1),
            retry_after_429=config.get('retry_after_429', True),
            backoff_factor=config.get('backoff_factor', 2.0)
        )

    def to_dict(self) -> Dict:
        """Convert config to dictionary."""
        return {
            'requests_per_day': self.requests_per_day,
            'requests_per_hour': self.requests_per_hour,
            'requests_per_minute': self.requests_per_minute,
            'min_delay': self.min_delay,
            'burst_limit': self.burst_limit,
            'retry_after_429': self.retry_after_429,
            'backoff_factor': self.backoff_factor
        }


class RateLimiter:
    """
    Intelligent rate limiter that enforces API limits and prevents blocking.

    Tracks request timestamps and ensures compliance with configured limits.
    """

    def __init__(self, config: RateLimitConfig, source_name: str = "unknown"):
        """
        Initialize rate limiter.

        Args:
            config: Rate limit configuration
            source_name: Name of the source (for logging)
        """
        self.config = config
        self.source_name = source_name

        # Track request timestamps
        self.request_history: deque = deque()
        self.last_request_time: Optional[float] = None

        # Backoff state
        self.consecutive_429s = 0
        self.current_backoff_delay = 0.0

        logger.info(f"Initialized RateLimiter for '{source_name}' with config: {config.to_dict()}")

    def wait_if_needed(self) -> float:
        """
        Wait if necessary to comply with rate limits.

        Returns:
            float: Number of seconds waited
        """
        wait_time = self._calculate_wait_time()

        if wait_time > 0:
            logger.info(
                f"[{self.source_name}] Rate limit: waiting {wait_time:.2f}s "
                f"before next request"
            )
            time.sleep(wait_time)

        return wait_time

    def _calculate_wait_time(self) -> float:
        """
        Calculate how long to wait before next request.

        Returns:
            float: Seconds to wait (0 if can proceed immediately)
        """
        now = time.time()
        wait_times = []

        # 1. Check minimum delay between requests
        if self.last_request_time and self.config.min_delay > 0:
            elapsed = now - self.last_request_time
            if elapsed < self.config.min_delay:
                wait_times.append(self.config.min_delay - elapsed)

        # 2. Check requests per minute
        if self.config.requests_per_minute:
            wait = self._check_time_window(60, self.config.requests_per_minute)
            if wait > 0:
                wait_times.append(wait)

        # 3. Check requests per hour
        if self.config.requests_per_hour:
            wait = self._check_time_window(3600, self.config.requests_per_hour)
            if wait > 0:
                wait_times.append(wait)

        # 4. Check requests per day
        if self.config.requests_per_day:
            wait = self._check_time_window(86400, self.config.requests_per_day)
            if wait > 0:
                wait_times.append(wait)

        # 5. Apply backoff if we've been hitting 429s
        if self.current_backoff_delay > 0:
            wait_times.append(self.current_backoff_delay)

        return max(wait_times) if wait_times else 0.0

    def _check_time_window(self, window_seconds: int, max_requests: int) -> float:
        """
        Check if we're within limits for a time window.

        Args:
            window_seconds: Time window in seconds (60, 3600, 86400)
            max_requests: Maximum requests allowed in window

        Returns:
            float: Seconds to wait (0 if within limits)
        """
        now = time.time()
        window_start = now - window_seconds

        # Remove old requests outside window
        while self.request_history and self.request_history[0] < window_start:
            self.request_history.popleft()

        # Check if we're at the limit
        if len(self.request_history) >= max_requests:
            # Need to wait until oldest request falls outside window
            oldest_request = self.request_history[0]
            wait_until = oldest_request + window_seconds
            wait_time = max(0, wait_until - now)

            if wait_time > 0:
                logger.warning(
                    f"[{self.source_name}] Reached limit: {max_requests} requests "
                    f"per {window_seconds}s window"
                )

            return wait_time

        return 0.0

    def record_request(self):
        """Record that a request was made."""
        now = time.time()
        self.request_history.append(now)
        self.last_request_time = now

    def record_success(self):
        """Record that a request completed successfully (reset backoff)."""
        if self.consecutive_429s > 0:
            logger.info(
                f"[{self.source_name}] Request successful, "
                f"resetting backoff (was {self.consecutive_429s} consecutive 429s)"
            )
            self.consecutive_429s = 0
            self.current_backoff_delay = 0.0

    def record_429_response(self, retry_after: Optional[int] = None):
        """
        Record that we received a 429 (Too Many Requests) response.

        Args:
            retry_after: Value from Retry-After header (seconds)
        """
        self.consecutive_429s += 1

        if retry_after:
            # Use server-provided retry-after
            self.current_backoff_delay = float(retry_after)
            logger.warning(
                f"[{self.source_name}] Got 429 response. "
                f"Server says retry after {retry_after}s"
            )
        else:
            # Exponential backoff: 2^n seconds
            self.current_backoff_delay = (
                self.config.backoff_factor ** self.consecutive_429s
            )
            logger.warning(
                f"[{self.source_name}] Got 429 response #{self.consecutive_429s}. "
                f"Backing off for {self.current_backoff_delay:.1f}s"
            )

    def get_stats(self) -> Dict:
        """
        Get current rate limiter statistics.

        Returns:
            Dict with request counts and state
        """
        now = time.time()

        # Count requests in different windows
        minute_ago = now - 60
        hour_ago = now - 3600
        day_ago = now - 86400

        requests_last_minute = sum(1 for t in self.request_history if t > minute_ago)
        requests_last_hour = sum(1 for t in self.request_history if t > hour_ago)
        requests_last_day = sum(1 for t in self.request_history if t > day_ago)

        return {
            'source': self.source_name,
            'total_requests_tracked': len(self.request_history),
            'requests_last_minute': requests_last_minute,
            'requests_last_hour': requests_last_hour,
            'requests_last_day': requests_last_day,
            'consecutive_429s': self.consecutive_429s,
            'current_backoff_delay': self.current_backoff_delay,
            'last_request_time': self.last_request_time
        }


# Preset configurations for common APIs
PRESET_CONFIGS = {
    'chile_bcn_conservative': RateLimitConfig(
        requests_per_day=100,
        requests_per_hour=20,
        min_delay_between_requests=3.0,
        burst_limit=1
    ),
    'chile_bcn_moderate': RateLimitConfig(
        requests_per_day=400,
        requests_per_hour=50,
        min_delay_between_requests=2.0,
        burst_limit=3
    ),
    'congress_api_demo': RateLimitConfig(
        requests_per_day=5000,
        requests_per_hour=500,
        min_delay_between_requests=1.0,
        burst_limit=5
    ),
    'congress_api_registered': RateLimitConfig(
        requests_per_day=10000,
        requests_per_hour=1000,
        min_delay_between_requests=0.5,
        burst_limit=10
    ),
    'generous': RateLimitConfig(
        requests_per_day=10000,
        min_delay_between_requests=0.1,
        burst_limit=10
    ),
    'conservative': RateLimitConfig(
        requests_per_day=100,
        requests_per_hour=20,
        min_delay_between_requests=5.0,
        burst_limit=1
    )
}


def get_preset_config(preset_name: str) -> RateLimitConfig:
    """Get a preset rate limit configuration by name."""
    if preset_name not in PRESET_CONFIGS:
        raise ValueError(
            f"Unknown preset '{preset_name}'. "
            f"Available: {list(PRESET_CONFIGS.keys())}"
        )
    return PRESET_CONFIGS[preset_name]


if __name__ == '__main__':
    """Test the rate limiter"""
    print("=" * 70)
    print("Testing Rate Limiter")
    print("=" * 70)

    # Test 1: Conservative config (100/day, 3s delay)
    print("\n1. Testing conservative config (100/day, 3s min delay):")
    config = PRESET_CONFIGS['conservative']
    limiter = RateLimiter(config, "test_source")

    print("   Making 5 rapid requests...")
    for i in range(5):
        wait_time = limiter.wait_if_needed()
        print(f"   Request {i+1}: waited {wait_time:.2f}s")
        limiter.record_request()

    # Test 2: 429 handling
    print("\n2. Testing 429 backoff:")
    limiter.record_429_response()
    wait_time = limiter.wait_if_needed()
    print(f"   After 1st 429: will wait {wait_time:.2f}s")

    limiter.record_429_response()
    wait_time = limiter.wait_if_needed()
    print(f"   After 2nd 429: will wait {wait_time:.2f}s")

    # Test 3: Stats
    print("\n3. Statistics:")
    stats = limiter.get_stats()
    for key, value in stats.items():
        if key != 'last_request_time':
            print(f"   {key}: {value}")

    print("\n" + "=" * 70)
    print("✅ Rate limiter tests completed!")
