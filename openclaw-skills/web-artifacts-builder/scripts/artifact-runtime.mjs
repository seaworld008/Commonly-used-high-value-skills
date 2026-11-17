// Local runtime implementation. Scaffold theme adapted from Anthropic's
// Apache-2.0 web-artifacts-builder; component sources stay in the licensed archive.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { collectRuntimeNotices } from './collect-runtime-notices.mjs';

const scripts = path.dirname(fileURLToPath(import.meta.url));
const noticeNames = ['LICENSE.txt', 'THIRD_PARTY_NOTICES.md', 'LICENSE.shadcn.txt'];
const tools = { parcel: '2.16.4', '@parcel/config-default': '2.16.4', 'html-inline': '1.2.0' };
const dependencies = {
  react: '18.3.1', 'react-dom': '18.3.1',
  '@radix-ui/react-accordion': '1.2.2', '@radix-ui/react-aspect-ratio': '1.1.1',
  '@radix-ui/react-avatar': '1.1.2', '@radix-ui/react-checkbox': '1.1.3',
  '@radix-ui/react-collapsible': '1.1.2', '@radix-ui/react-context-menu': '2.2.4',
  '@radix-ui/react-dialog': '1.1.4', '@radix-ui/react-dropdown-menu': '2.1.4',
  '@radix-ui/react-hover-card': '1.1.4', '@radix-ui/react-label': '2.1.1',
  '@radix-ui/react-menubar': '1.1.4', '@radix-ui/react-navigation-menu': '1.2.3',
  '@radix-ui/react-popover': '1.1.4', '@radix-ui/react-progress': '1.1.1',
  '@radix-ui/react-radio-group': '1.2.2', '@radix-ui/react-scroll-area': '1.2.2',
  '@radix-ui/react-select': '2.1.4', '@radix-ui/react-separator': '1.1.1',
  '@radix-ui/react-slider': '1.2.2', '@radix-ui/react-slot': '1.1.1',
  '@radix-ui/react-switch': '1.1.2', '@radix-ui/react-tabs': '1.1.2',
  '@radix-ui/react-toast': '1.2.4', '@radix-ui/react-toggle': '1.1.1',
  '@radix-ui/react-toggle-group': '1.1.1', '@radix-ui/react-tooltip': '1.1.6',
  'class-variance-authority': '0.7.1', clsx: '2.1.1', 'tailwind-merge': '2.6.0',
  'lucide-react': '0.468.0', 'next-themes': '0.4.4', sonner: '1.7.1',
  cmdk: '1.0.4', vaul: '1.1.2', 'embla-carousel-react': '8.5.2',
  'react-day-picker': '9.14.0', 'react-resizable-panels': '2.1.7',
  'date-fns': '3.6.0', 'react-hook-form': '7.54.2',
  '@hookform/resolvers': '3.9.1', zod: '3.24.1',
};
const devDependencies = {
  vite: '8.3.8', typescript: '5.7.3', '@types/node': '22.15.30',
  '@types/react': '18.3.18', '@types/react-dom': '18.3.5',
  tailwindcss: '3.4.17', postcss: '8.4.49', autoprefixer: '10.4.20',
  'tailwindcss-animate': '1.0.7', ...tools,
};

function checkEngine(version) {
  const m = /^v?(\d+)\.(\d+)\.(\d+)$/.exec(version);
  if (!m) throw new Error(`Unsupported Node.js version: ${version}`);
  const [major, minor] = m.slice(1).map(Number);
  if (!(major === 20 && minor >= 19 || major === 22 && minor >= 12 || major > 22)) {
    throw new Error(`Node.js ${version} is unsupported; require ^20.19.0 or >=22.12.0 (Vite 8).`);
  }
}

function run(command, args, cwd, options = {}) {
  // Arguments remain data, including user paths; never invoke a shell.
  const result = spawnSync(command, args, { cwd, stdio: 'inherit', ...options });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${command} failed (${result.signal || result.status}).`);
}

function json(file, value) {
  fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n', { flag: 'wx' });
}

function htmlEscape(value) {
  return value.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}

function targetIsEmpty(target) {
  try {
    const info = fs.lstatSync(target);
    if (!info.isDirectory() || info.isSymbolicLink() || fs.readdirSync(target).length) {
      throw new Error(`Refusing to overwrite existing target: ${target}`);
    }
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
}

// Only these fixed, regular notice files are read. No traversal of node_modules,
// package symlinks, or arbitrary project paths is used to collect licenses.
function notices(root) {
  return noticeNames.map(name => {
    const file = path.join(root, name);
    const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
    try {
      const info = fs.fstatSync(fd);
      if (!info.isFile() || info.size === 0 || info.size > 1024 * 1024) {
        throw new Error(`Notice must be a nonempty regular file, at most 1 MiB: ${name}`);
      }
      const buffer = Buffer.alloc(1024 * 1024 + 1);
      let length = 0, count;
      while (length < buffer.length && (count = fs.readSync(fd, buffer, length, buffer.length - length, null))) length += count;
      if (!length || length > 1024 * 1024) throw new Error(`Notice exceeds size limit: ${name}`);
      return { name, encoding: 'base64', content: buffer.subarray(0, length).toString('base64') };
    } finally { fs.closeSync(fd); }
  });
}

function scaffold(stage, title) {
  fs.mkdirSync(path.join(stage, 'src'));
  const write = (name, text) => fs.writeFileSync(path.join(stage, name), text, { flag: 'wx' });
  // The npm identifier is deliberately independent of the directory/display name.
  json(path.join(stage, 'package.json'), {
    name: 'web-artifact', version: '0.0.0', private: true, type: 'module',
    engines: { node: '^20.19.0 || >=22.12.0' },
    scripts: { dev: 'vite', typecheck: 'tsc --noEmit', build: 'tsc --noEmit && vite build', preview: 'vite preview' },
    browserslist: ['last 2 Chrome versions', 'last 2 Firefox versions', 'last 2 Safari versions'],
    dependencies, devDependencies,
  });
  write('pnpm-workspace.yaml', `packages:\n  - '.'\noverrides:\n  react-remove-scroll-bar: file:.artifact-runtime/scrollbar\n`);
  write('index.html', `<!doctype html>\n<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>${htmlEscape(title)}</title></head><body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body></html>\n`);
  write('src/main.tsx', `import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App';\nimport './index.css';\nReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);\n`);
  write('src/App.tsx', `import { Button } from '@/components/ui/button';\nexport default function App() { return <main className="min-h-screen p-8"><h1 className="mb-4 text-3xl font-bold">Ready to create</h1><Button onClick={() => window.alert('Hello!')}>Try a component</Button></main>; }\n`);
  json(path.join(stage, 'tsconfig.json'), { compilerOptions: {
    target: 'ES2022', lib: ['ES2022', 'DOM', 'DOM.Iterable'], module: 'ESNext',
    moduleResolution: 'Bundler', jsx: 'react-jsx', strict: true,
    skipLibCheck: true, esModuleInterop: true, allowSyntheticDefaultImports: true,
    resolveJsonModule: true, isolatedModules: true, noEmit: true,
    baseUrl: '.', paths: { '@/*': ['./src/*'] }, types: ['vite/client', 'node'],
  }, include: ['src', 'vite.config.ts'] });
  // Vite's built-in TSX transform needs no floating template or React plugin.
  write('vite.config.ts', `import { defineConfig } from 'vite';\nimport { fileURLToPath } from 'node:url';\nexport default defineConfig({ resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } } });\n`);
  json(path.join(stage, '.postcssrc.json'), { plugins: { tailwindcss: {}, autoprefixer: {} } });
  const colorNames = ['border', 'input', 'ring', 'background', 'foreground'];
  const pairedColors = ['primary', 'secondary', 'destructive', 'muted', 'accent', 'popover', 'card'];
  const colors = Object.fromEntries(colorNames.map(name => [name, `hsl(var(--${name}))`]));
  for (const name of pairedColors) colors[name] = { DEFAULT: `hsl(var(--${name}))`, foreground: `hsl(var(--${name}-foreground))` };
  write('tailwind.config.cjs', `module.exports = ${JSON.stringify({
    darkMode: ['class'], content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
    theme: { extend: { colors, borderRadius: { lg: 'var(--radius)', md: 'calc(var(--radius) - 2px)', sm: 'calc(var(--radius) - 4px)' },
      keyframes: { 'accordion-down': { from: { height: '0' }, to: { height: 'var(--radix-accordion-content-height)' } }, 'accordion-up': { from: { height: 'var(--radix-accordion-content-height)' }, to: { height: '0' } } },
      animation: { 'accordion-down': 'accordion-down 0.2s ease-out', 'accordion-up': 'accordion-up 0.2s ease-out' },
    } },
  }, null, 2).replace(/\n}$/, ',\n  plugins: [require("tailwindcss-animate")]\n}')}\n`);
  write('src/index.css', `@tailwind base;\n@tailwind components;\n@tailwind utilities;\n@layer base {\n:root {\n--background: 0 0% 100%; --foreground: 0 0% 3.9%;\n--card: 0 0% 100%; --card-foreground: 0 0% 3.9%;\n--popover: 0 0% 100%; --popover-foreground: 0 0% 3.9%;\n--primary: 0 0% 9%; --primary-foreground: 0 0% 98%;\n--secondary: 0 0% 96.1%; --secondary-foreground: 0 0% 9%;\n--muted: 0 0% 96.1%; --muted-foreground: 0 0% 45.1%;\n--accent: 0 0% 96.1%; --accent-foreground: 0 0% 9%;\n--destructive: 0 84.2% 60.2%; --destructive-foreground: 0 0% 98%;\n--border: 0 0% 89.8%; --input: 0 0% 89.8%; --ring: 0 0% 3.9%; --radius: 0.5rem;\n}\n.dark {\n--background: 0 0% 3.9%; --foreground: 0 0% 98%;\n--card: 0 0% 3.9%; --card-foreground: 0 0% 98%;\n--popover: 0 0% 3.9%; --popover-foreground: 0 0% 98%;\n--primary: 0 0% 98%; --primary-foreground: 0 0% 9%;\n--secondary: 0 0% 14.9%; --secondary-foreground: 0 0% 98%;\n--muted: 0 0% 14.9%; --muted-foreground: 0 0% 63.9%;\n--accent: 0 0% 14.9%; --accent-foreground: 0 0% 98%;\n--destructive: 0 62.8% 30.6%; --destructive-foreground: 0 0% 98%;\n--border: 0 0% 14.9%; --input: 0 0% 14.9%; --ring: 0 0% 83.1%;\n}\n* { @apply border-border; }\nbody { @apply bg-background text-foreground; }\n}\n`);
  json(path.join(stage, 'components.json'), {
    $schema: 'https://ui.shadcn.com/schema.json', style: 'default', rsc: false, tsx: true,
    tailwind: { config: 'tailwind.config.cjs', css: 'src/index.css', baseColor: 'slate', cssVariables: true, prefix: '' },
    aliases: { components: '@/components', utils: '@/lib/utils', ui: '@/components/ui', lib: '@/lib', hooks: '@/hooks' },
  });
}

function init(name) {
  const target = path.resolve(name);
  targetIsEmpty(target);
  const sourceNotices = notices(path.dirname(scripts));
  const archive = path.join(scripts, 'shadcn-components.tar.gz');
  if (!fs.statSync(archive).isFile()) throw new Error('Missing shadcn-components.tar.gz.');
  const stage = fs.mkdtempSync(path.join(path.dirname(target), '.artifact-init-'));
  try {
    scaffold(stage, path.basename(target));
    // Original project-local compatibility module, with its full MIT notice.
    // file: dependencies are materialized inside pnpm's node_modules store.
    fs.mkdirSync(path.join(stage, '.artifact-runtime'));
    fs.cpSync(path.join(scripts, 'runtime-scrollbar'), path.join(stage, '.artifact-runtime/scrollbar'), { recursive: true, errorOnExist: true, force: false });
    for (const item of sourceNotices) fs.writeFileSync(path.join(stage, item.name), Buffer.from(item.content, 'base64'), { flag: 'wx' });
    run('tar', ['-xzf', archive, '-C', path.join(stage, 'src'), 'components', 'lib', 'hooks'], stage);
    // Baseline archive: 43 UI modules + lib/utils.ts + hooks/use-toast.ts.
    if (fs.readdirSync(path.join(stage, 'src/components/ui')).filter(n => n.endsWith('.tsx')).length !== 43 ||
        !fs.statSync(path.join(stage, 'src/lib/utils.ts')).isFile() ||
        !fs.statSync(path.join(stage, 'src/hooks/use-toast.ts')).isFile()) {
      throw new Error('Expected all 45 bundled shadcn component/support source files.');
    }
    // All required native runtimes ship platform packages; no dependency lifecycle scripts are needed.
    fs.copyFileSync(path.join(scripts, 'template-pnpm-lock.yaml'), path.join(stage, 'pnpm-lock.yaml'), fs.constants.COPYFILE_EXCL);
    run('pnpm', ['install', '--frozen-lockfile', '--ignore-scripts'], stage);
    targetIsEmpty(target);
    fs.renameSync(stage, target);
    console.log(`Created ${target} with all 45 component/support source files. Run pnpm typecheck and pnpm build in that directory.`);
  } finally { fs.rmSync(stage, { recursive: true, force: true }); }
}

function readHtml(file) {
  const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
  try { return readHtmlDescriptor(fd).html; }
  finally { fs.closeSync(fd); }
}

function sameFileState(a, b) {
  return ['dev', 'ino', 'mode', 'nlink', 'size', 'mtimeNs', 'ctimeNs'].every(key => a[key] === b[key]);
}

function readHtmlDescriptor(fd) {
  const info = fs.fstatSync(fd, { bigint: true });
  if (!info.isFile() || info.size === 0n || info.size > 128n * 1024n * 1024n) {
    throw new Error('Build/inline output must be a nonempty regular HTML file (at most 128 MiB).');
  }
  // One extra byte detects growth without an unbounded read. Explicit positions
  // also work after html-inline has advanced the shared descriptor's cursor.
  const buffer = Buffer.alloc(Number(info.size) + 1);
  let length = 0;
  while (length < buffer.length) {
    const count = fs.readSync(fd, buffer, length, Math.min(64 * 1024, buffer.length - length), length);
    if (!count) break;
    length += count;
  }
  if (BigInt(length) !== info.size || !sameFileState(info, fs.fstatSync(fd, { bigint: true }))) {
    throw new Error('HTML output changed during read.');
  }
  return { html: buffer.subarray(0, length).toString('utf8'), info };
}

function rewriteHtmlDescriptor(fd, html) {
  const data = Buffer.from(html);
  let offset = 0;
  while (offset < data.length) {
    const count = fs.writeSync(fd, data, offset, data.length - offset, offset);
    if (count <= 0) throw new Error('Unable to finish writing HTML output.');
    offset += count;
  }
  fs.ftruncateSync(fd, data.length);
  fs.fsyncSync(fd);
}

// Scan actual HTML tags, skipping comments and raw-text script/style bodies.
// This avoids treating a JS string such as "</template>" as HTML markup.
function validateHtml(html, inlined = false) {
  const tag = /<!--[\s\S]*?-->|<![^>]*>|<\/?([a-z][\w:-]*)\b(?:"[^"]*"|'[^']*'|[^'">])*>/ig;
  let match;
  let root = false, body = false, closedRoot = false, closedBody = false;
  let bodyEnd = -1;
  while ((match = tag.exec(html))) {
    if (!match[1]) continue;
    const name = match[1].toLowerCase();
    const closing = /^<\//.test(match[0]);
    if (name === 'html') closing ? closedRoot = true : root = true;
    if (name === 'body') {
      if (closing) { closedBody = true; bodyEnd = match.index; } else body = true;
    }
    if (inlined && !closing) {
      const attrs = Object.fromEntries([...match[0].matchAll(/\s([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g)]
        .map(a => [a[1].toLowerCase(), a[2] ?? a[3] ?? a[4]]));
      if (attrs.style) checkCss(attrs.style);
      for (const key of ['src', 'srcset', 'poster', 'data']) {
        if (attrs[key] && !/^(?:data:|#)/i.test(attrs[key])) throw new Error(`Uninlined resource: ${name}[${key}]`);
      }
      if (name === 'link' && /(?:stylesheet|icon|preload|modulepreload)/i.test(attrs.rel || '') && attrs.href && !/^data:/i.test(attrs.href)) {
        throw new Error('Uninlined link resource.');
      }
      if (['use', 'image'].includes(name) && [attrs.href, attrs['xlink:href']].some(v => v && !/^(?:data:|#)/i.test(v))) {
        throw new Error('Uninlined SVG resource.');
      }
    }
    if (!closing && ['script', 'style', 'textarea', 'title'].includes(name)) {
      const end = new RegExp(`</${name}\\s*>`, 'ig');
      end.lastIndex = tag.lastIndex;
      const found = end.exec(html);
      if (!found) throw new Error(`Unclosed ${name} element.`);
      if (inlined && name === 'style') checkCss(html.slice(tag.lastIndex, found.index));
      tag.lastIndex = end.lastIndex;
    }
  }
  if (!(root && body && closedRoot && closedBody) || !html.trim()) throw new Error('Incomplete HTML document.');
  return bodyEnd;
}

function checkCss(css) {
  if (/@import\s/i.test(css) || /url\(\s*["']?(?!data:|#)[^\s"')]/i.test(css)) {
    throw new Error('Uninlined CSS resource.');
  }
}

function checkBuildResources(dist, html) {
  let files = 0, bytes = 0;
  const visit = (folder, depth) => {
    if (depth > 16) throw new Error('Build output nesting exceeds limit.');
    for (const entry of fs.readdirSync(folder, { withFileTypes: true })) {
      if (++files > 2048 || entry.isSymbolicLink()) throw new Error('Build output contains too many files or a symlink.');
      const file = path.join(folder, entry.name);
      if (entry.isDirectory()) { visit(file, depth + 1); continue; }
      if (!entry.isFile()) throw new Error('Build output contains a non-regular file.');
      bytes += fs.statSync(file).size;
      if (bytes > 128 * 1024 * 1024) throw new Error('Build output exceeds 128 MiB.');
      if (file === path.join(dist, 'index.html')) continue;
      // This also catches static asset paths embedded in JS (e.g. new URL).
      // Dynamic requests assembled by application code require browser testing.
      const relative = path.relative(dist, file).split(path.sep).join('/');
      if (html.includes(relative) || html.includes(encodeURI(relative))) {
        throw new Error(`Uninlined build resource reference: ${relative}`);
      }
    }
  };
  visit(dist, 0);
}

function runtimePublisherNotices() {
  const file = path.join(scripts, 'runtime-license-notices.json');
  const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
  try {
    const stat = fs.fstatSync(fd);
    if (!stat.isFile() || !stat.size || stat.size > 4 * 1024 * 1024) throw new Error('Invalid reviewed runtime notice manifest.');
    const data = Buffer.alloc(stat.size + 1);
    let length = 0, count;
    while (length < data.length && (count = fs.readSync(fd, data, length, data.length - length, null))) length += count;
    if (length !== stat.size) throw new Error('Runtime notice manifest changed during read.');
    const parsed = JSON.parse(data.subarray(0, length).toString('utf8'));
    if (parsed.schema_version !== 1 || !Array.isArray(parsed.notices)) throw new Error('Invalid runtime notice manifest schema.');
    return parsed.notices;
  } finally { fs.closeSync(fd); }
}

function bundle() {
  const project = process.cwd();
  if (!fs.statSync(path.join(project, 'package.json')).isFile()) throw new Error('Run from a project with package.json.');
  if (!fs.statSync(path.join(project, 'index.html')).isFile()) throw new Error('Missing index.html entry point.');
  const licenseData = notices(project);
  const output = path.join(project, 'bundle.html');
  try {
    if (!fs.lstatSync(output).isFile() || fs.lstatSync(output).isSymbolicLink()) throw new Error('bundle.html must be a regular file or absent.');
  } catch (error) { if (error.code !== 'ENOENT') throw error; }
  const stage = fs.mkdtempSync(path.join(project, '.artifact-build-'));
  try {
    // Project-local dependencies only. No global tool/configuration is changed.
    const absent = Object.entries(tools).filter(([name]) => !fs.existsSync(path.join(project, 'node_modules', name, 'package.json')));
    if (absent.length) run('pnpm', ['add', '--ignore-scripts', '--save-dev', '--save-exact', ...absent.map(([name, version]) => `${name}@${version}`)], project);
    const config = path.join(stage, '.parcelrc');
    json(config, { extends: '@parcel/config-default' });
    const dist = path.join(stage, 'dist');
    run('pnpm', ['exec', 'parcel', 'build', 'index.html', '--dist-dir', dist, '--no-source-maps', '--no-cache', '--no-optimize', '--public-url', './', '--config', config], project);
    validateHtml(readHtml(path.join(dist, 'index.html')));
    const candidate = path.join(stage, 'bundle.html');
    let fd = fs.openSync(candidate, fs.constants.O_RDWR | fs.constants.O_CREAT | fs.constants.O_EXCL |
      fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK, 0o600);
    try {
      run('pnpm', ['exec', 'html-inline', path.join(dist, 'index.html')], project, { stdio: ['ignore', fd, 'inherit'] });
      const initial = readHtmlDescriptor(fd);
      let html = initial.html;
      const bodyEnd = validateHtml(html, true);
      checkBuildResources(dist, html);
      licenseData.push(...collectRuntimeNotices(project, runtimePublisherNotices()));
      // JSON and original bytes are both base64: license text cannot close this
      // inert template, create markup, execute scripts, or add visible product UI.
      const encoded = Buffer.from(JSON.stringify({ version: 1, scope: 'bundled-source-and-runtime-notices', notices: licenseData })).toString('base64');
      html = html.slice(0, bodyEnd) + `<template id="artifact-license-notices" data-encoding="base64-json">${encoded}</template>` + html.slice(bodyEnd);
      if (!sameFileState(initial.info, fs.fstatSync(fd, { bigint: true }))) throw new Error('Inline output changed before rewrite.');
      rewriteHtmlDescriptor(fd, html);
      const verified = readHtmlDescriptor(fd);
      if (verified.html !== html) throw new Error('HTML output changed after rewrite.');
      validateHtml(verified.html, true);
      if (!sameFileState(verified.info, fs.lstatSync(candidate, { bigint: true }))) throw new Error('Candidate path was replaced.');
      // A failed close must abort before publication. Never retry close: an error
      // may have already released the descriptor, allowing its number to be reused.
      const closing = fd;
      fd = undefined;
      fs.closeSync(closing);
      if (!sameFileState(verified.info, fs.lstatSync(candidate, { bigint: true }))) throw new Error('Candidate path was replaced.');
      // Same-filesystem rename is the sole publication step. Previous dist is
      // never touched, including on tool failures, empty output, or write errors.
      // The private stage and identity checks reject observed replacements; they
      // cannot guarantee atomic identity-bound rename against a same-uid attacker.
      fs.renameSync(candidate, output);
      console.log(`Bundle complete: ${output} (${Buffer.byteLength(html)} bytes).`);
    } finally { if (fd !== undefined) fs.closeSync(fd); }
  } finally { fs.rmSync(stage, { recursive: true, force: true }); }
}

try {
  const [mode, version, name] = process.argv.slice(2);
  checkEngine(version);
  if (mode === 'init' && name) init(name);
  else if (mode === 'bundle') bundle();
  else throw new Error('Usage: artifact-runtime.mjs init <node-version> <directory> | bundle <node-version>');
} catch (error) {
  console.error(`Error: ${error.message}`);
  process.exitCode = 1;
}
