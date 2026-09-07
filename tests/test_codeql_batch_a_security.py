import json
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_VALIDATION = REPO_ROOT / ".github" / "workflows" / "repo-validation.yml"
PROVENANCE_CI = REPO_ROOT / ".github" / "workflows" / "skills-provenance-ci.yml"
CHANGELOG_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "changelog.yml"
HARVEST_REPORT = (
    REPO_ROOT
    / "skills"
    / "engineering-workflow-automation"
    / "harvest"
    / "scripts"
    / "generate-report.js"
)
HARVEST_TEMPLATE = (
    REPO_ROOT
    / "skills"
    / "engineering-workflow-automation"
    / "harvest"
    / "templates"
    / "client-report.html"
)
ALGORITHMIC_ART_VIEWER = (
    REPO_ROOT
    / "skills"
    / "growth-operations-xiaohongshu"
    / "algorithmic-art"
    / "templates"
    / "viewer.html"
)
CREATE_PULL_REQUEST_V8_COMMIT = "5f6978faf089d4d20b00c7766989d076bb2fc7f1"
P5_1_7_0_SHA384 = (
    "sha384-Mhzoc5EVkjFUVtIW2M3h8BgXtFlUsUpu9lTCThPrV7+"
    "k6MN6vTi079rew0LkvgFb"
)


class ScriptTagParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.scripts.append(dict(attrs))


class CodeQLBatchASecurityTests(unittest.TestCase):
    def test_read_only_workflows_declare_top_level_contents_permission(self):
        for workflow_path in (REPO_VALIDATION, PROVENANCE_CI):
            with self.subTest(workflow=workflow_path.name):
                workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
                self.assertEqual({"contents": "read"}, workflow.get("permissions"))

    def test_changelog_third_party_action_is_pinned_to_full_commit(self):
        workflow = yaml.safe_load(CHANGELOG_WORKFLOW.read_text(encoding="utf-8"))
        steps = workflow["jobs"]["refresh-changelog"]["steps"]
        create_pr = next(
            step
            for step in steps
            if str(step.get("uses", "")).startswith(
                "peter-evans/create-pull-request@"
            )
        )
        self.assertEqual(
            f"peter-evans/create-pull-request@{CREATE_PULL_REQUEST_V8_COMMIT}",
            create_pr["uses"],
        )
        checkout = next(
            step
            for step in steps
            if str(step.get("uses", "")).startswith("actions/checkout@")
        )
        self.assertFalse(checkout["with"]["persist-credentials"])

    def test_harvest_passes_untrusted_filters_as_gh_argv(self):
        repo_value = "owner/repo; touch /tmp/must-not-run"
        author_value = "alice && echo injected"
        node_source = f"""
const report = require({json.dumps(str(HARVEST_REPORT))});
const args = report.buildPrListArgs(
  {{
    days: 7,
    repo: {json.dumps(repo_value)},
    author: {json.dumps(author_value)}
  }}
);
process.stdout.write(JSON.stringify(args));
"""
        result = subprocess.run(
            ["node", "-e", node_source],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        args = json.loads(result.stdout)
        self.assertIn(repo_value, args)
        self.assertIn(author_value, args)
        self.assertEqual(repo_value, args[args.index("-R") + 1])
        self.assertEqual(author_value, args[args.index("--author") + 1])

        source = HARVEST_REPORT.read_text(encoding="utf-8")
        self.assertNotIn("execSync", source)
        self.assertIn("execFileSync", source)
        self.assertIn("shell: false", source)

    def test_harvest_numeric_array_replacement_is_linear_and_bounded(self):
        node_source = f"""
const assert = require("node:assert/strict");
const report = require({json.dumps(str(HARVEST_REPORT))});
const valid = "dailyChart data: [1, 2.5, 3]\\nCategory data:\\t[4]";
assert.equal(
  report.replaceNumericDataArrays(valid, () => "data: [9]"),
  "dailyChart data: [9]\\nCategory data: [9]"
);
const adversarial = "data:[" + "1".repeat(60000) + "x";
assert.equal(
  report.replaceNumericDataArrays(adversarial, () => "must-not-replace"),
  adversarial
);
const rendered = report.generateHTML(
  {{
    meta: {{
      projectName: "project",
      author: "author",
      startDateFormatted: "start",
      endDateFormatted: "end",
      generatedAtFormatted: "generated"
    }},
    summary: {{
      totalTasks: 1,
      totalHours: "2.0",
      totalAdditions: "+3",
      completionRate: "100%"
    }},
    charts: {{
      daily: {{ labels: ["D"], data: [8.5] }},
      category: {{ labels: ["C"], data: [2] }}
    }}
  }},
  {json.dumps(str(HARVEST_TEMPLATE))}
);
assert.match(rendered, /dailyChart[\\s\\S]*?data: \\[8\\.5\\]/);
assert.match(rendered, /categoryChart[\\s\\S]*?data: \\[2\\]/);
"""
        subprocess.run(
            ["node", "-e", node_source],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )

    def test_algorithmic_art_p5_script_has_verified_sri(self):
        parser = ScriptTagParser()
        parser.feed(ALGORITHMIC_ART_VIEWER.read_text(encoding="utf-8"))
        p5_script = next(
            script
            for script in parser.scripts
            if script.get("src", "").endswith("/p5.js/1.7.0/p5.min.js")
        )
        self.assertEqual(P5_1_7_0_SHA384, p5_script.get("integrity"))
        self.assertEqual("anonymous", p5_script.get("crossorigin"))
        self.assertEqual("no-referrer", p5_script.get("referrerpolicy"))


if __name__ == "__main__":
    unittest.main()
