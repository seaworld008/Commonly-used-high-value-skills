"""Transient transport failures must not masquerade as missing upstreams."""
import io
import json
import urllib.error
from unittest.mock import patch

import pytest

from scripts.github_artifact_provider import GitHubArtifactProvider, GitHubUnavailable


URL = "https://api.github.com/repos/example/skills/commits/main"


def response(value):
    return io.BytesIO(json.dumps(value).encode())


def test_transient_read_retries_then_caches_only_success():
    with (
        patch("urllib.request.urlopen", side_effect=[
            urllib.error.URLError("temporary connection reset"),
            response({"sha": "a" * 40}),
        ]) as request,
        patch("scripts.github_artifact_provider.time.sleep") as sleep,
    ):
        provider = GitHubArtifactProvider()
        assert provider._get_json(URL) == {"sha": "a" * 40}
        assert provider._get_json(URL) == {"sha": "a" * 40}
        assert request.call_count == 2
        sleep.assert_called_once_with(0.5)


@pytest.mark.parametrize("code", [401, 403, 404, 422])
def test_permanent_http_errors_are_not_retried(code):
    error = urllib.error.HTTPError(URL, code, "denied", {}, None)
    with (
        patch("urllib.request.urlopen", side_effect=error) as request,
        patch("scripts.github_artifact_provider.time.sleep") as sleep,
    ):
        with pytest.raises(GitHubUnavailable, match=f"HTTP {code}"):
            GitHubArtifactProvider()._get_json(URL)
        assert request.call_count == 1
        sleep.assert_not_called()


@pytest.mark.parametrize("code", [429, 500, 502, 503, 504])
def test_retry_budget_is_bounded(code):
    error = urllib.error.HTTPError(URL, code, "temporary", {}, None)
    with (
        patch("urllib.request.urlopen", side_effect=error) as request,
        patch("scripts.github_artifact_provider.time.sleep") as sleep,
    ):
        provider = GitHubArtifactProvider()
        with pytest.raises(GitHubUnavailable, match=f"HTTP {code}"):
            provider._get_json(URL)
        assert request.call_count == 3
        assert sleep.call_count == 2
        assert URL not in provider._json_cache


def test_long_retry_after_is_reported_without_early_retry():
    error = urllib.error.HTTPError(URL, 429, "wait", {"Retry-After": "60"}, None)
    with (
        patch("urllib.request.urlopen", side_effect=error) as request,
        patch("scripts.github_artifact_provider.time.sleep") as sleep,
    ):
        with pytest.raises(GitHubUnavailable, match="HTTP 429"):
            GitHubArtifactProvider()._get_json(URL)
        assert request.call_count == 1
        sleep.assert_not_called()


def test_malformed_json_is_not_retried_or_cached():
    with (
        patch("urllib.request.urlopen", return_value=io.BytesIO(b"invalid")) as request,
        patch("scripts.github_artifact_provider.time.sleep") as sleep,
    ):
        provider = GitHubArtifactProvider()
        with pytest.raises(GitHubUnavailable):
            provider._get_json(URL)
        assert request.call_count == 1
        sleep.assert_not_called()
        assert URL not in provider._json_cache
