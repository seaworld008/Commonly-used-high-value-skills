"""Windows bundle commands must use Node, not a shell or a .cmd executable."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "bin/npm-command.js"


def node(body):
    return subprocess.run(["node", "-e", body], cwd=ROOT, capture_output=True, text=True)


def test_windows_npm_uses_verified_cli_entrypoint_without_shell():
    result = node(f"""
    const {{ npmInvocation }} = require({json.dumps(str(MODULE))});
    const p = require('path');
    const r = npmInvocation('npx', {{platform:'win32', execPath:p.join('/safe path','node'),
      env:{{npm_execpath:p.join('/npm root','bin','npm-cli.js')}},
      exists:x=>x===p.join('/npm root','bin','npx-cli.js')}});
    console.log(JSON.stringify(r));
    """)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["command"].endswith("node")
    assert data["args"][0].endswith("npx-cli.js")
    assert "npm root" in data["args"][0]


def test_windows_missing_cli_is_an_error_not_shell_fallback():
    result = node(f"""
    const {{ npmInvocation }} = require({json.dumps(str(MODULE))});
    npmInvocation('npm', {{platform:'win32', execPath:'/missing/node', env:{{}}, exists:()=>false}});
    """)
    assert result.returncode != 0
    assert "npm CLI entry point" in result.stderr


def test_native_npm_version_smoke_does_not_install_anything():
    result = node(f"""
    const {{ npmInvocation }} = require({json.dumps(str(MODULE))});
    const r = npmInvocation('npm');
    const child = require('child_process').spawnSync(r.command, [...r.args, '--version'], {{shell:false, encoding:'utf8'}});
    if (child.error) throw child.error;
    process.stdout.write(child.stdout || '');
    process.exit(child.status === null ? 1 : child.status);
    """)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()[0].isdigit()
