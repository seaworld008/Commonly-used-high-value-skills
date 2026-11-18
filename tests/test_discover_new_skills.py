import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "discover_new_skills.py"


def load_module():
    spec = importlib.util.spec_from_file_location("discover_new_skills", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DiscoverNewSkillsTests(unittest.TestCase):
    def test_load_retired_skill_names_reads_hard_retirement_denylist(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = Path(tmpdir) / "portfolio-policy.json"
            policy.write_text(
                json.dumps(
                    {
                        "retired_skills": [
                            {"name": "legacy-helper", "replacement": "current-helper"},
                            {"name": "duplicate-helper"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                {"legacy-helper", "duplicate-helper"},
                module.load_retired_skill_names(policy),
            )

    def test_build_report_includes_source_health_and_errors(self):
        module = load_module()

        report = module.build_discovery_report(
            local_skill_count=10,
            all_discoveries=[
                module.make_discovery(
                    source_key="github",
                    name="alpha",
                    source="GitHub",
                    url="https://github.com/example/alpha",
                    repo_stars=1,
                    description="Alpha",
                )
            ],
            unique_discoveries=[
                module.make_discovery(
                    source_key="github",
                    name="alpha",
                    source="GitHub",
                    url="https://github.com/example/alpha",
                    repo_stars=1,
                    description="Alpha",
                )
            ],
            source_health={
                "github": {
                    "status": "degraded",
                    "errors": [{"kind": "unauthorized", "message": "401"}],
                    "queries": 2,
                    "results": 1,
                },
                "skills_sh": {
                    "status": "healthy",
                    "errors": [],
                    "queries": 1,
                    "results": 0,
                },
                "clawhub": {
                    "status": "healthy",
                    "errors": [],
                    "queries": 1,
                    "results": 0,
                },
            },
        )

        self.assertEqual(10, report["local_skill_count"])
        self.assertIn("generated_at", report)
        self.assertTrue(report["generated_at"].endswith("Z"))
        self.assertIn("source_health", report)
        self.assertEqual("degraded", report["source_health"]["github"]["status"])
        self.assertEqual("unauthorized", report["errors"][0]["kind"])
        self.assertEqual(1, report["source_health"]["github"]["emitted"])
        self.assertEqual(1, report["source_health"]["github"]["unique_emitted"])
        self.assertEqual(1, report["raw_discovered"])

    def test_classify_fetch_error_recognizes_http_statuses(self):
        module = load_module()

        unauthorized = module.classify_fetch_error(401, "Unauthorized")
        rate_limited = module.classify_fetch_error(429, "Too Many Requests")
        not_found = module.classify_fetch_error(404, "Not Found")

        self.assertEqual("unauthorized", unauthorized["kind"])
        self.assertEqual("rate_limited", rate_limited["kind"])
        self.assertEqual("not_found", not_found["kind"])

    def _http_error(self, module, code, headers):
        import email.message

        message = email.message.Message()
        for key, value in headers.items():
            message[key] = value
        return module.urllib.error.HTTPError("https://api.github.com/x", code, "limited", message, None)

    def test_fetch_url_waits_and_retries_rate_limited_responses(self):
        module = load_module()
        health = module.new_source_health()
        waits = []
        responses = [
            self._http_error(module, 429, {"Retry-After": "7"}),
            self._http_error(module, 403, {"X-RateLimit-Remaining": "0"}),
        ]

        class Body:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                return b"ok"

        def fake_urlopen(request, timeout):
            if responses:
                raise responses.pop(0)
            return Body()

        module.sleep = waits.append
        module.urllib.request.urlopen = fake_urlopen
        try:
            content = module.fetch_url("https://api.github.com/x", source_key="github", source_health=health)
        finally:
            import urllib.request

            module.urllib.request.urlopen = urllib.request.urlopen

        self.assertEqual("ok", content)
        self.assertEqual([7.0, module.RATE_LIMIT_DEFAULT_DELAY], waits)
        self.assertEqual([], health["github"]["errors"])

    def test_rate_limit_delay_reads_http_date_retry_after(self):
        from email.utils import formatdate

        module = load_module()
        module.time = lambda: 1_000_000.0

        dated = self._http_error(module, 429, {"Retry-After": formatdate(1_000_040.0, usegmt=True)})
        invalid = self._http_error(module, 429, {"Retry-After": "soon"})

        self.assertEqual(40.0, module.rate_limit_delay(dated))
        asctime = self._http_error(module, 429, {"Retry-After": "Mon Jan 12 13:47:20 1970"})
        self.assertEqual(40.0, module.rate_limit_delay(asctime))
        self.assertEqual(module.RATE_LIMIT_DEFAULT_DELAY, module.rate_limit_delay(invalid))

    def test_fetch_url_bounds_rate_limit_waits_and_skips_other_errors(self):
        module = load_module()
        waits = []
        module.sleep = waits.append

        def always_limited(request, timeout):
            raise self._http_error(module, 429, {"Retry-After": "600"})

        def forbidden(request, timeout):
            raise self._http_error(module, 403, {})

        import urllib.request

        original = urllib.request.urlopen
        try:
            module.urllib.request.urlopen = always_limited
            health = module.new_source_health()
            self.assertIsNone(
                module.fetch_url("https://api.github.com/x", source_key="github", source_health=health)
            )
            self.assertEqual([module.RATE_LIMIT_MAX_DELAY] * module.RATE_LIMIT_RETRIES, waits)
            self.assertEqual("rate_limited", health["github"]["errors"][0]["kind"])

            waits.clear()
            module.RATE_LIMIT_WAIT_BUDGET = module._rate_limit_waited + module.RATE_LIMIT_MAX_DELAY
            health = module.new_source_health()
            self.assertIsNone(
                module.fetch_url("https://api.github.com/x", source_key="github", source_health=health)
            )
            self.assertEqual([module.RATE_LIMIT_MAX_DELAY], waits)

            waits.clear()
            module.urllib.request.urlopen = forbidden
            health = module.new_source_health()
            self.assertIsNone(
                module.fetch_url("https://api.github.com/x", source_key="github", source_health=health)
            )
            self.assertEqual([], waits)
            self.assertEqual("forbidden", health["github"]["errors"][0]["kind"])
        finally:
            module.urllib.request.urlopen = original


if __name__ == "__main__":
    unittest.main()
