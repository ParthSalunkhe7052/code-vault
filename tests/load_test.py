"""
Load Testing Script for CodeVault API
Tests performance under concurrent load.
"""

import asyncio
import time
import statistics
import argparse
from typing import Optional

import httpx


class LoadTester:
    """Load testing utility for CodeVault API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.results = []

    async def _make_request(
        self,
        client: httpx.AsyncClient,
        endpoint: str,
        method: str = "GET",
        data: Optional[dict] = None,
    ):
        """Make a single request and measure response time."""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()

        try:
            if method == "GET":
                response = await client.get(url)
            elif method == "POST":
                response = await client.post(url, json=data)
            else:
                return {
                    "endpoint": endpoint,
                    "status": 0,
                    "response_time": 0,
                    "success": False,
                    "error": f"Unsupported method: {method}",
                }

            await response.aread()
            status = response.status_code
            elapsed = time.time() - start_time
            return {
                "endpoint": endpoint,
                "status": status,
                "response_time": elapsed,
                "success": 200 <= status < 300,
            }
        except Exception as e:
            elapsed = time.time() - start_time
            return {
                "endpoint": endpoint,
                "status": 0,
                "response_time": elapsed,
                "success": False,
                "error": str(e),
            }

    async def make_request(
        self, endpoint: str, method: str = "GET", data: Optional[dict] = None
    ):
        """Make a single request and measure response time."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await self._make_request(client, endpoint, method, data)

    async def run_concurrent_requests(
        self, endpoint: str, count: int, method: str = "GET", data: dict = None
    ):
        """Run multiple concurrent requests."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            tasks = [
                self._make_request(client, endpoint, method, data)
                for _ in range(count)
            ]
            return await asyncio.gather(*tasks)

    def print_results(self, results: list, test_name: str):
        """Print test results."""
        print(f"\n{'=' * 60}")
        print(f"Results: {test_name}")
        print(f"{'=' * 60}")

        if not results:
            print("No results to display")
            return

        response_times = [r["response_time"] for r in results]
        successes = sum(1 for r in results if r["success"])
        failures = len(results) - successes

        print(f"Total Requests: {len(results)}")
        print(f"Successful: {successes} ({100 * successes / len(results):.1f}%)")
        print(f"Failed: {failures} ({100 * failures / len(results):.1f}%)")
        print()
        print(f"Response Times (seconds):")
        print(f"  Min: {min(response_times):.3f}s")
        print(f"  Max: {max(response_times):.3f}s")
        print(f"  Mean: {statistics.mean(response_times):.3f}s")
        print(f"  Median: {statistics.median(response_times):.3f}s")

        if len(response_times) > 1:
            print(f"  Std Dev: {statistics.stdev(response_times):.3f}s")

        # Percentiles
        sorted_times = sorted(response_times)
        p95_idx = int(len(sorted_times) * 0.95)
        p99_idx = int(len(sorted_times) * 0.99)
        print(
            f"  95th percentile: {sorted_times[min(p95_idx, len(sorted_times) - 1)]:.3f}s"
        )
        print(
            f"  99th percentile: {sorted_times[min(p99_idx, len(sorted_times) - 1)]:.3f}s"
        )

        # Error breakdown
        error_codes = {}
        for r in results:
            if not r["success"]:
                code = r.get("status", "Unknown")
                error_codes[code] = error_codes.get(code, 0) + 1

        if error_codes:
            print(f"\nError Breakdown:")
            for code, count in error_codes.items():
                print(f"  Status {code}: {count} requests")

    async def test_health_endpoint(self, concurrency: int = 100):
        """Test health check endpoint under load."""
        print(f"\nTesting health endpoint with {concurrency} concurrent requests...")
        results = await self.run_concurrent_requests("/api/v1/health", concurrency)
        self.print_results(results, f"Health Check - {concurrency} concurrent")
        return results

    async def test_login_endpoint(self, concurrency: int = 50):
        """Test login endpoint under load."""
        print(f"\nTesting login endpoint with {concurrency} concurrent requests...")

        # Generate unique emails for each request
        async with httpx.AsyncClient(timeout=10.0) as client:
            async def make_login_request(i):
                return await self._make_request(
                    client,
                    "/api/v1/auth/login",
                    "POST",
                    {"email": f"loadtest{i}@example.com", "password": "wrongpassword"},
                )

            tasks = [make_login_request(i) for i in range(concurrency)]
            results = await asyncio.gather(*tasks)
        self.print_results(results, f"Login - {concurrency} concurrent")
        return results

    async def test_database_load(self, concurrency: int = 100, iterations: int = 5):
        """Test database connection pool under load."""
        print(
            f"\nTesting database load: {concurrency} concurrent x {iterations} iterations..."
        )

        all_results = []
        for i in range(iterations):
            print(f"  Iteration {i + 1}/{iterations}...")
            results = await self.run_concurrent_requests("/api/v1/health", concurrency)
            all_results.extend(results)
            await asyncio.sleep(1)  # Brief pause between iterations

        self.print_results(
            all_results, f"Database Load Test - {concurrency * iterations} total"
        )
        return all_results

    async def run_full_suite(self):
        """Run full load testing suite."""
        print("=" * 60)
        print("CODEVAULT LOAD TESTING SUITE")
        print("=" * 60)
        print(f"Target URL: {self.base_url}")
        print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Test 1: Health endpoint (lightweight)
        await self.test_health_endpoint(concurrency=100)

        # Test 2: Login endpoint (rate limiting test)
        await self.test_login_endpoint(concurrency=50)

        # Test 3: Sustained database load
        await self.test_database_load(concurrency=50, iterations=3)

        print("\n" + "=" * 60)
        print("Load testing completed!")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="CodeVault Load Testing")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=100,
        help="Number of concurrent requests (default: 100)",
    )
    parser.add_argument(
        "--test",
        choices=["health", "login", "database", "all"],
        default="all",
        help="Which test to run (default: all)",
    )

    args = parser.parse_args()

    tester = LoadTester(args.url)

    if args.test == "all":
        asyncio.run(tester.run_full_suite())
    elif args.test == "health":
        asyncio.run(tester.test_health_endpoint(args.concurrency))
    elif args.test == "login":
        asyncio.run(tester.test_login_endpoint(args.concurrency))
    elif args.test == "database":
        asyncio.run(tester.test_database_load(args.concurrency, iterations=3))


if __name__ == "__main__":
    main()
