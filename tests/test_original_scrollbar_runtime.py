"""Execute the original ESM with controlled React effects and CSSOM/DOM doubles.

No packages are installed, no ports are opened, and every fixture lives in TMPDIR.
These tests exercise lifecycle/ownership, not a browser's layout or React renderer.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "skills/developer-engineering/web-artifacts-builder/scripts/runtime-scrollbar"


@pytest.fixture(scope="module")
def javascript_runtime():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for actual JS behavior tests")
    with tempfile.TemporaryDirectory(prefix="scrollbar-test-", dir=os.environ["TMPDIR"]) as temporary:
        target = Path(temporary)
        for name in ("package.json", "index.js", "index.d.ts", "constants.js", "constants.d.ts", "LICENSE.txt"):
            shutil.copyfile(RUNTIME / name, target / name)
        react = target / "node_modules/react"
        react.mkdir(parents=True)
        (react / "package.json").write_text(
            json.dumps({"name": "react", "type": "module", "exports": "./index.js"}), encoding="utf-8"
        )
        (react / "index.js").write_text(
            "export const effects = [];\n"
            "export function useEffect(effect, dependencies) { effects.push({ effect, dependencies }); }\n"
            "export const useLayoutEffect = useEffect;\n", encoding="utf-8"
        )
        harness = target / "behavior.mjs"
        harness.write_text(HARNESS, encoding="utf-8")
        yield node, harness


CASES = [
    "ssr", "gap", "margin", "padding", "nested", "strict", "resize",
    "zero", "stable", "rtl", "priorities", "external", "attributes",
    "overflow_external", "documents", "style_failure", "stylesheet_external",
    "setup_rollback", "no_dom", "prepositioned", "spacing_shorthand", "exports",
]


@pytest.mark.parametrize("case", CASES)
def test_original_scrollbar_behavior(javascript_runtime, case):
    node, harness = javascript_runtime
    result = subprocess.run(
        [node, str(harness), case], capture_output=True, text=True, timeout=20,
        cwd=harness.parent, env={**os.environ, "NODE_OPTIONS": ""},
    )
    assert result.returncode == 0, f"{case}:\n{result.stdout}\n{result.stderr}"
    assert result.stdout.strip() == f"PASS {case}"


HARNESS = r"""
import assert from 'node:assert/strict';
import { effects } from 'react';
import * as runtime from './index.js';
import { readFileSync } from 'node:fs';

// Minimal CSSOM: preserve declarations and expand overflow longhands on demand.
// Deliberately independent from runtime's journal and compensation calculations.
class Declaration {
  values = new Map();
  fail = null;
  get length() { return this.values.size; }
  item(i) { return [...this.values.keys()][i]; }
  getPropertyValue(name) {
    if (this.values.has(name)) return this.values.get(name)[0];
    if (name === 'overflow') {
      const x = this.values.get('overflow-x')?.[0];
      const y = this.values.get('overflow-y')?.[0];
      return x && y ? (x === y ? x : `${x} ${y}`) : '';
    }
    if (name.startsWith('overflow-') && this.values.has('overflow')) {
      const parts = this.values.get('overflow')[0].split(' ');
      return name === 'overflow-x' ? parts[0] : (parts[1] || parts[0]);
    }
    const [family, edge] = name.split('-');
    if (['margin', 'padding'].includes(family) && edge && this.values.has(family)) {
      const parts = this.values.get(family)[0].split(' ');
      return ({ top: parts[0], right: parts[1] || parts[0],
        bottom: parts[2] || parts[0], left: parts[3] || parts[1] || parts[0] })[edge] || '';
    }
    return '';
  }
  getPropertyPriority(name) {
    if (this.values.has(name)) return this.values.get(name)[1];
    if (name.startsWith('overflow-')) return this.values.get('overflow')?.[1] || '';
    const [family, edge] = name.split('-');
    if (['margin', 'padding'].includes(family) && edge) return this.values.get(family)?.[1] || '';
    if (name === 'overflow') {
      const x = this.values.get('overflow-x');
      const y = this.values.get('overflow-y');
      return x && y && x[1] === y[1] ? x[1] : '';
    }
    return '';
  }
  expandOverflow() {
    if (!this.values.has('overflow')) return;
    const x = [this.getPropertyValue('overflow-x'), this.getPropertyPriority('overflow-x')];
    const y = [this.getPropertyValue('overflow-y'), this.getPropertyPriority('overflow-y')];
    this.values.delete('overflow');
    this.values.set('overflow-x', x);
    this.values.set('overflow-y', y);
  }
  expandSpacing(family) {
    if (!this.values.has(family)) return;
    const pairs = ['top', 'right', 'bottom', 'left'].map((edge) => {
      const key = `${family}-${edge}`;
      return [key, [this.getPropertyValue(key), this.getPropertyPriority(key)]];
    });
    this.values.delete(family);
    for (const [key, pair] of pairs) this.values.set(key, pair);
  }
  setProperty(name, value, priority = '') {
    if (this.fail === name) { this.fail = null; throw new Error('setter failed'); }
    if (!value) { this.removeProperty(name); return; }
    if (name === 'overflow') {
      this.values.delete('overflow-x'); this.values.delete('overflow-y');
    } else if (name.startsWith('overflow-')) this.expandOverflow();
    const [family, edge] = name.split('-');
    if (['margin', 'padding'].includes(family)) {
      if (edge) this.expandSpacing(family);
      else for (const side of ['top', 'right', 'bottom', 'left']) this.values.delete(`${family}-${side}`);
    }
    this.values.set(name, [value, priority]);
  }
  removeProperty(name) {
    if (name === 'overflow') {
      this.values.delete('overflow-x'); this.values.delete('overflow-y');
    } else if (name.startsWith('overflow-')) this.expandOverflow();
    const [family, edge] = name.split('-');
    if (['margin', 'padding'].includes(family)) {
      if (edge) this.expandSpacing(family);
      else for (const side of ['top', 'right', 'bottom', 'left']) this.values.delete(`${family}-${side}`);
    }
    this.values.delete(name);
  }
}

function environment({ gutter = 20, left = false, stable = false, failure = '' } = {}) {
  const listeners = new Set();
  const nodes = [];
  const attributes = new Map();
  const body = {
    style: new Declaration(),
    getAttribute: (key) => attributes.has(key) ? attributes.get(key) : null,
    setAttribute: (key, value) => attributes.set(key, String(value)),
    removeAttribute: (key) => attributes.delete(key),
  };
  const base = {
    'margin-left': '8px', 'margin-top': '8px', 'margin-right': '8px',
    'padding-left': '3px', 'padding-top': '4px', 'padding-right': '5px',
    'position': 'static', 'overflow': 'visible', 'overflow-x': 'visible', 'overflow-y': 'visible',
  };
  const importantRules = new Map();
  const root = { get clientWidth() {
    const hidden = view.getComputedStyle(body).getPropertyValue('overflow-y') === 'hidden';
    return view.innerWidth - (hidden && !stable ? 0 : env.gutter);
  }, get clientLeft() {
    return 2 + (left && root.clientWidth < view.innerWidth ? env.gutter : 0);
  } };
  const view = {
    innerWidth: 1000,
    getComputedStyle(element) {
      return { getPropertyValue(name) {
        if (element === root) return name === 'border-left-width' ? '2px' : '';
        const own = element.style.getPropertyValue(name);
        const priority = element.style.getPropertyPriority(name);
        return priority !== 'important' && importantRules.has(name)
          ? importantRules.get(name) : (own || base[name] || '');
      } };
    },
    addEventListener(name, callback) { assert.equal(name, 'resize'); listeners.add(callback); },
    removeEventListener(name, callback) { assert.equal(name, 'resize'); listeners.delete(callback); },
  };
  const head = { appendChild(node) {
    if (failure === 'append') throw new Error('append failed');
    nodes.push(node);
  } };
  const doc = {
    body, documentElement: root, defaultView: view, head,
    createElement(tag) {
      assert.equal(tag, 'style');
      if (failure === 'create') throw new Error('create failed');
      return { textContent: '', remove() {
        const i = nodes.indexOf(this); if (i !== -1) nodes.splice(i, 1);
      } };
    },
  };
  const env = { doc, body, view, base, attributes, nodes, listeners, importantRules, gutter,
    resize() { for (const callback of [...listeners]) callback(); },
  };
  return env;
}

function mount(env, props) {
  globalThis.document = env.doc;
  assert.equal(runtime.RemoveScrollBar(props), null);
  const { effect } = effects.pop();
  assert.ok(effect);
  const cleanup = effect();
  return cleanup || (() => {});
}
const value = (env, name) => env.body.style.getPropertyValue(name);
const priority = (env, name) => env.body.style.getPropertyPriority(name);
function clean(env) {
  assert.equal(env.nodes.length, 0);
  assert.equal(env.listeners.size, 0);
  assert.equal(env.body.style.length, 0);
  assert.equal(env.attributes.size, 0);
}

const cases = {
  ssr() {
    assert.deepEqual(runtime.getGapWidth(), { left: 0, top: 0, right: 0, gap: 0 });
    assert.equal(runtime.RemoveScrollBar(), null);
    assert.equal(effects.pop().effect(), undefined);
  },
  gap() {
    const env = environment(); globalThis.document = env.doc;
    assert.deepEqual(runtime.getGapWidth(), { left: 8, top: 8, right: 8, gap: 20 });
    assert.deepEqual(runtime.getGapWidth('padding'), { left: 3, top: 4, right: 5, gap: 20 });
    env.base['margin-left'] = '-2.5px'; env.base['margin-top'] = 'auto';
    env.view.innerWidth = 990.5; env.gutter = 12.5;
    assert.deepEqual(runtime.getGapWidth(), { left: -2.5, top: 0, right: 8, gap: 12.5 });
    env.gutter = -4; assert.equal(runtime.getGapWidth().gap, 0);
  },
  margin() {
    const env = environment(); const stop = mount(env);
    assert.equal(value(env, 'overflow'), 'hidden');
    assert.equal(value(env, 'margin-right'), '28px');
    assert.equal(value(env, 'margin-left'), '');
    assert.equal(value(env, 'position'), 'relative');
    assert.equal(value(env, runtime.removedBarSizeVariable), '20px');
    assert.equal(env.attributes.get('data-scroll-locked'), '1');
    assert.equal(env.listeners.size, 1); assert.equal(env.nodes.length, 1);
    assert.match(env.nodes[0].textContent, /right:var\(--removed-body-scroll-bar-size,0px\) !important/);
    assert.match(env.nodes[0].textContent, /width:calc\(100% - var\(--removed-body-scroll-bar-size,0px\)\)/);
    for (const name of [runtime.zeroRightClassName, runtime.fullWidthClassName, runtime.noScrollbarsClassName]) {
      assert.ok(env.nodes[0].textContent.includes(`body[data-hvs-scrollbar-compensation="${env.attributes.get('data-hvs-scrollbar-compensation')}"] .${name}`));
    }
    stop(); stop(); clean(env);
  },
  padding() {
    const env = environment(); const stop = mount(env, { gapMode: 'padding', noRelative: true, noImportant: true });
    assert.equal(value(env, 'padding-right'), '25px');
    assert.equal(value(env, 'margin-right'), '');
    assert.equal(value(env, 'position'), '');
    assert.equal(priority(env, 'padding-right'), '');
    assert.ok(!env.nodes[0].textContent.includes('!important'));
    stop(); clean(env);
  },
  nested() {
    const env = environment(); const first = mount(env);
    const second = mount(env, { gapMode: 'padding', noImportant: true, noRelative: true });
    assert.equal(env.nodes.length, 1); assert.equal(env.listeners.size, 1);
    assert.equal(value(env, 'margin-right'), '28px');
    assert.equal(value(env, 'padding-right'), '');
    assert.equal(env.attributes.get('data-scroll-locked'), '2');
    first();
    assert.equal(value(env, 'overflow'), 'hidden');
    assert.equal(value(env, 'margin-right'), '');
    assert.equal(value(env, 'padding-right'), '25px');
    assert.equal(value(env, 'position'), '');
    assert.equal(priority(env, 'overflow'), '');
    assert.equal(env.attributes.get('data-scroll-locked'), '1');
    second(); clean(env);
    const a = mount(env); const b = mount(env, { gapMode: 'padding' });
    b(); assert.equal(value(env, 'margin-right'), '28px'); a(); clean(env);
  },
  strict() {
    const env = environment(); globalThis.document = env.doc;
    runtime.RemoveScrollBar(); const { effect } = effects.pop();
    for (let i = 0; i < 30; i++) {
      const stop = effect(); assert.equal(value(env, 'margin-right'), '28px');
      stop(); stop(); clean(env);
    }
  },
  resize() {
    const env = environment(); const stop = mount(env);
    for (const gutter of [20, 17, 0, 25, 25]) {
      env.gutter = gutter; env.view.innerWidth += 5; env.resize();
      assert.equal(value(env, 'margin-right'), gutter ? `${8 + gutter}px` : '');
      assert.equal(value(env, runtime.removedBarSizeVariable), `${gutter}px`);
      assert.equal(env.nodes.length, 1); assert.equal(env.listeners.size, 1);
    }
    stop(); clean(env);
  },
  zero() {
    const env = environment({ gutter: 0 }); const stop = mount(env);
    assert.equal(value(env, 'margin-right'), '');
    assert.equal(value(env, runtime.removedBarSizeVariable), '0px');
    assert.equal(value(env, 'overflow'), 'hidden'); stop(); clean(env);
  },
  stable() {
    const env = environment({ stable: true }); const stop = mount(env);
    assert.equal(value(env, runtime.removedBarSizeVariable), '0px');
    assert.equal(value(env, 'margin-right'), ''); stop(); clean(env);
  },
  rtl() {
    const env = environment({ left: true }); const stop = mount(env, { gapMode: 'padding' });
    assert.equal(value(env, 'padding-left'), '23px');
    assert.equal(value(env, 'padding-right'), '');
    assert.match(env.nodes[0].textContent, /left:var\(/); stop(); clean(env);
    const right = environment(); const end = mount(right);
    assert.match(right.nodes[0].textContent, /right:var\(/); end(); clean(right);
  },
  priorities() {
    const env = environment(); const style = env.body.style;
    style.setProperty('overflow', 'auto scroll', 'important');
    style.setProperty('margin-right', '11.5px', 'important');
    style.setProperty('position', 'static', 'important');
    style.setProperty(runtime.removedBarSizeVariable, '9px', 'important');
    style.setProperty('color', 'red', 'important');
    const before = [...style.values]; const stop = mount(env);
    assert.equal(value(env, 'margin-right'), '31.5px');
    assert.equal(priority(env, 'margin-right'), 'important');
    assert.equal(value(env, 'color'), 'red'); stop();
    assert.deepEqual(new Map(style.values), new Map(before));
    const other = environment(); other.importantRules.set('overflow-y', 'scroll');
    const end = mount(other, { noImportant: true });
    assert.equal(value(other, runtime.removedBarSizeVariable), '0px'); end(); clean(other);
  },
  external() {
    const env = environment(); const stop = mount(env);
    env.body.style.setProperty('margin-right', '41px', 'important');
    env.body.style.setProperty('color', 'blue');
    env.body.style.setProperty('position', 'absolute');
    env.body.style.setProperty(runtime.removedBarSizeVariable, '7px');
    env.resize(); env.gutter = 30; env.resize(); stop();
    assert.equal(value(env, 'margin-right'), '41px');
    assert.equal(priority(env, 'margin-right'), 'important');
    assert.equal(value(env, 'position'), 'absolute');
    assert.equal(value(env, 'color'), 'blue');
    assert.equal(value(env, runtime.removedBarSizeVariable), '7px');
    assert.equal(value(env, 'overflow'), '');
    assert.equal(env.nodes.length, 0); assert.equal(env.listeners.size, 0);
    // An external priority-only change is also external ownership.
    const other = environment(); const end = mount(other);
    other.body.style.setProperty('margin-right', '28px', '');
    end(); assert.equal(value(other, 'margin-right'), '28px');
    assert.equal(priority(other, 'margin-right'), '');
  },
  attributes() {
    for (const original of ['', 'owner-state', '4']) {
      const env = environment(); env.attributes.set('data-scroll-locked', original);
      env.attributes.set('data-hvs-scrollbar-compensation', 'user-scope');
      const stop = mount(env);
      assert.equal(env.attributes.get('data-scroll-locked'), original === '4' ? '5' : '1');
      stop(); assert.equal(env.attributes.get('data-scroll-locked'), original);
      assert.equal(env.attributes.get('data-hvs-scrollbar-compensation'), 'user-scope');
    }
    const env = environment(); const stop = mount(env);
    env.attributes.set('data-scroll-locked', 'external');
    env.attributes.set('data-hvs-scrollbar-compensation', 'external-scope');
    env.resize(); stop();
    assert.equal(env.attributes.get('data-scroll-locked'), 'external');
    assert.equal(env.attributes.get('data-hvs-scrollbar-compensation'), 'external-scope');
  },
  overflow_external() {
    const env = environment(); env.body.style.setProperty('overflow', 'auto scroll', 'important');
    const stop = mount(env);
    env.body.style.setProperty('overflow-y', 'visible', 'important');
    env.resize(); stop();
    assert.equal(value(env, 'overflow-x'), 'auto');
    assert.equal(priority(env, 'overflow-x'), 'important');
    assert.equal(value(env, 'overflow-y'), 'visible');
    assert.equal(priority(env, 'overflow-y'), 'important');
    const other = environment(); const end = mount(other);
    other.body.style.setProperty('overflow', 'clip', ''); end();
    assert.equal(value(other, 'overflow'), 'clip');
  },
  documents() {
    const first = environment(); const second = environment({ gutter: 12 });
    const a = mount(first); const b = mount(second);
    assert.equal(value(first, 'margin-right'), '28px');
    assert.equal(value(second, 'margin-right'), '20px');
    a(); clean(first); assert.equal(value(second, 'overflow'), 'hidden');
    second.gutter = 19; second.resize(); assert.equal(value(second, 'margin-right'), '27px');
    b(); clean(second);
  },
  style_failure() {
    for (const failure of ['create', 'append']) {
      const env = environment({ failure });
      assert.throws(() => mount(env), new RegExp(`${failure} failed`)); clean(env);
    }
  },
  stylesheet_external() {
    const env = environment(); const stop = mount(env);
    env.nodes[0].textContent = '/* externally replaced */';
    env.resize(); assert.equal(env.nodes[0].textContent, '/* externally replaced */');
    stop(); assert.equal(env.nodes.length, 0); assert.equal(env.listeners.size, 0);
    assert.equal(env.body.style.length, 0); assert.equal(env.attributes.size, 0);
  },
  setup_rollback() {
    const env = environment(); env.body.style.fail = 'position';
    assert.throws(() => mount(env), /setter failed/); clean(env);
    const stop = mount(env); stop(); clean(env);
  },
  no_dom() {
    for (const missing of ['body', 'documentElement', 'defaultView']) {
      const env = environment(); env.doc[missing] = null; const stop = mount(env); stop();
      assert.equal(env.nodes.length, 0); assert.equal(env.listeners.size, 0);
      assert.deepEqual(runtime.getGapWidth(), { left: 0, top: 0, right: 0, gap: 0 });
    }
  },
  prepositioned() {
    const env = environment(); env.body.style.setProperty('position', 'fixed', 'important');
    const stop = mount(env); assert.equal(value(env, 'position'), 'fixed');
    stop(); assert.equal(value(env, 'position'), 'fixed'); assert.equal(priority(env, 'position'), 'important');
  },
  spacing_shorthand() {
    for (const gapMode of ['margin', 'padding']) {
      const env = environment(); const style = env.body.style;
      style.setProperty(gapMode, '4px 10px 6px 8px', 'important');
      const before = new Map(style.values); const stop = mount(env, { gapMode });
      assert.equal(value(env, `${gapMode}-right`), '30px');
      stop(); assert.deepEqual(style.values, before);
      const end = mount(env, { gapMode });
      style.setProperty(`${gapMode}-left`, '35px');
      env.resize(); assert.equal(value(env, `${gapMode}-right`), '30px');
      env.resize(); assert.equal(value(env, `${gapMode}-right`), '30px');
      end();
      assert.equal(value(env, `${gapMode}-left`), '35px');
      assert.equal(value(env, `${gapMode}-right`), '10px');
      assert.equal(priority(env, `${gapMode}-right`), 'important');
      assert.equal(value(env, `${gapMode}-top`), '4px');
      assert.equal(value(env, `${gapMode}-bottom`), '6px');
    }
  },
  exports() {
    assert.deepEqual(Object.keys(runtime).sort(), [
      'RemoveScrollBar', 'getGapWidth', 'zeroRightClassName', 'fullWidthClassName',
      'noScrollbarsClassName', 'removedBarSizeVariable',
    ].sort());
    const pkg = JSON.parse(readFileSync(new URL('./package.json', import.meta.url)));
    assert.equal(pkg.name, '@high-value-skills/scrollbar-compensation');
    assert.equal(pkg.version, '1.0.0'); assert.equal(pkg.license, 'MIT');
    assert.equal(pkg.type, 'module');
    assert.deepEqual(pkg.exports['.'], { types: './index.d.ts', import: './index.js' });
    assert.deepEqual(pkg.peerDependencies, { react: '^18.3.1 || ^19.0.0' });
    assert.equal(pkg.dependencies, undefined);
    const license = readFileSync(new URL('./LICENSE.txt', import.meta.url), 'utf8');
    assert.ok(license.includes('Permission is hereby granted, free of charge'));
    assert.ok(license.includes('SOFTWARE.'));
  },
};
const selected = process.argv[2];
cases[selected]();
console.log(`PASS ${selected}`);
"""


def test_original_constant_subpath_works_with_package_exports_and_legacy_file(javascript_runtime):
    node, harness = javascript_runtime
    program = "import assert from 'node:assert/strict'; import * as constants from '@high-value-skills/scrollbar-compensation/constants'; import * as file from './constants.js'; assert.deepEqual(Object.keys(constants).sort(), ['fullWidthClassName','noScrollbarsClassName','removedBarSizeVariable','zeroRightClassName'].sort()); assert.deepEqual(constants,file);"
    result = subprocess.run([node, "--input-type=module", "-e", program], cwd=harness.parent, text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
