/*
 * MIT License
 * Copyright (c) 2026 seaworld008
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */
import fs from 'node:fs';
import path from 'node:path';
import { TextDecoder } from 'node:util';
import { createHash } from 'node:crypto';

// Original, synchronous implementation: importing this module performs no IO.
export const RUNTIME_NOTICE_LIMITS = Object.freeze({
  depth: 64, packages: 1024, edges: 8192, files: 4096,
  directoryEntries: 4096, noticesPerPackage: 64,
  manifestBytes: 1024 * 1024, fileBytes: 1024 * 1024,
  totalBytes: 32 * 1024 * 1024, pathSteps: 256, symlinks: 40,
});

const compare = (a, b) => a < b ? -1 : a > b ? 1 : 0;
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
// Legacy uppercase npm identifiers are supported; traversal, URL escapes,
// backslashes, control characters and Windows drive/ADS syntax are not.
const segment = '[A-Za-z0-9-][A-Za-z0-9._-]*';
const packageName = new RegExp(`^(?:${segment}|@${segment}/${segment})(?![\\s\\S])`);
const validName = name => typeof name === 'string' && name.length <= 214 &&
  packageName.test(name) && !name.split('/').includes('node_modules');
const versionPattern = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?(?![\s\S])/;
// Exact root filenames only. Explicit dual-license suffixes are common in npm;
// JSON fields (including "SEE LICENSE IN ...") never supply filesystem paths.
const noticePattern = /^(?:licen[cs]e|notice|copying)(?:[-.](?:mit|apache(?:-?2(?:\.0)?)?|bsd(?:-[23]-clause)?|isc))?(?:\.(?:txt|md))?(?![\s\S])/i;

function fail(context, reason) {
  throw new Error(`Runtime notices: ${context}: ${reason}`);
}

function inside(root, file) {
  const relative = path.relative(root, file);
  return relative === '' || (!path.isAbsolute(relative) && relative !== '..' && !relative.startsWith(`..${path.sep}`));
}

function same(a, b) {
  return a.dev === b.dev && a.ino === b.ino && a.mode === b.mode;
}

/**
 * Collect the installed runtime closure without loading any package code.
 * Return [{name: full root filename, package: manifest name, version,
 *          encoding: 'base64', content: original bytes in base64}].
 * Missing optional/peer edges are warnings with distinct codes and also appear
 * in result.diagnostics (a non-enumerable array). Optional overrides required
 * edges, as in npm. The optional second argument accepts digest-checked, exact-version publisher
 * notice records; it is not a license classification or network lookup.
 * Missing required edges and unsafe installed optional/peer
 * packages fail closed. devDependencies are never traversed.
 *
 * This copies complete files, not a license classification or legal review.
 * A nonempty matching file is required; SPDX strings alone are insufficient.
 * No network, NODE_PATH, exports/main resolution, lifecycle scripts, arbitrary
 * license paths or recursive directory scans are used. Only npm and project-
 * local pnpm node_modules layouts are supported; external workspace/store links
 * are rejected. Limits above include manifest reads in the byte/file budgets.
 */
export function collectRuntimeNotices(project, supplementalNotices = []) {
  const limits = RUNTIME_NOTICE_LIMITS;
  let context = 'project';
  try {
    if (typeof project !== 'string' || !project || project.includes('\0')) fail(context, 'invalid project path');
    if (!fs.constants.O_NOFOLLOW || !fs.constants.O_NONBLOCK) fail(context, 'safe file-open flags unavailable');
    const root = fs.realpathSync(path.resolve(project));
    const rootStat = fs.lstatSync(root);
    if (!rootStat.isDirectory() || rootStat.isSymbolicLink()) fail(context, 'project must be a directory');
    let modules = null;
    let modulesStat = null;
    let bytes = 0, files = 0, edges = 0;
    const result = [];
    const diagnostics = [];
    Object.defineProperty(result, 'diagnostics', { value: diagnostics, enumerable: false });

    // Resolve one path component at a time, checking *every* link target before
    // following it. Even an outside link that eventually returns inside fails.
    function walk(file, boundary, boundaryStat, linksAllowed = true) {
      if (!inside(boundary, file)) fail(context, 'path escapes allowed root');
      let pending = path.relative(boundary, file).split(path.sep).filter(Boolean).map(part => ({ part, mustExist: false }));
      let cursor = boundary, links = 0, steps = 0;
      let parents = [{ file: boundary, stat: boundaryStat }];
      const initial = fs.lstatSync(boundary);
      if (!same(initial, boundaryStat) || !initial.isDirectory() || initial.isSymbolicLink()) fail(context, 'root changed');
      let stat = initial;
      while (pending.length) {
        if (++steps > limits.pathSteps) fail(context, 'path step limit exceeded');
        const { part, mustExist } = pending.shift();
        if (part === '.') continue;
        if (part === '..') {
          if (cursor === boundary) fail(context, 'symlink escapes node_modules root');
          // Resolve '..' only AFTER preceding symlinks. path.resolve on the raw
          // link text would erase a symlink/.. pair and misidentify the package.
          const prefix = path.relative(boundary, path.dirname(cursor)).split(path.sep).filter(Boolean);
          pending = [...prefix.map(part => ({ part, mustExist: true })), ...pending];
          cursor = boundary;
          parents = [{ file: boundary, stat: boundaryStat }];
          stat = initial;
          continue;
        }
        cursor = path.join(cursor, part);
        try { stat = fs.lstatSync(cursor); }
        catch (error) {
          if (error.code === 'ENOENT' && mustExist) fail(context, 'dangling package/ancestor symlink');
          throw error;
        }
        if (stat.isSymbolicLink()) {
          if (!linksAllowed) fail(context, 'symlink in file path');
          if (++links > limits.symlinks) fail(context, 'symlink limit exceeded');
          const target = fs.readlinkSync(cursor);
          let prefix;
          if (path.isAbsolute(target)) {
            if (target !== boundary && !target.startsWith(boundary + path.sep)) fail(context, 'symlink escapes node_modules root');
            prefix = target.slice(boundary.length).split(path.sep).filter(Boolean);
          } else {
            prefix = [...path.relative(boundary, path.dirname(cursor)).split(path.sep).filter(Boolean), ...target.split(path.sep).filter(Boolean)];
          }
          pending = [...prefix.map(part => ({ part, mustExist: true })), ...pending];
          cursor = boundary;
          parents = [{ file: boundary, stat: boundaryStat }];
          stat = initial;
          continue;
        }
        if (pending.length) {
          if (!stat.isDirectory()) fail(context, 'non-directory path ancestor');
          parents.push({ file: cursor, stat });
        }
      }
      return { file: cursor, stat, parents };
    }

    function verifyParents(parents) {
      // Also anchor node_modules to the original project rather than allowing a
      // later swap of the entire project directory to change the trust root.
      const currentRoot = fs.lstatSync(root);
      if (!same(currentRoot, rootStat) || !currentRoot.isDirectory() || currentRoot.isSymbolicLink()) fail(context, 'project changed');
      for (const item of parents) {
        const stat = fs.lstatSync(item.file);
        if (!same(stat, item.stat) || !stat.isDirectory() || stat.isSymbolicLink()) fail(context, 'directory changed during collection');
      }
    }

    function read(file, boundary, boundaryStat, cap) {
      const checked = walk(file, boundary, boundaryStat, false);
      if (!checked.stat.isFile()) fail(context, 'expected a regular file');
      if (!checked.stat.size || checked.stat.size > cap) fail(context, `file size must be 1..${cap} bytes`);
      if (++files > limits.files) fail(context, 'file count limit exceeded');
      if (bytes + checked.stat.size > limits.totalBytes) fail(context, 'total byte limit exceeded');
      verifyParents(checked.parents);
      const fd = fs.openSync(checked.file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
      try {
        const before = fs.fstatSync(fd);
        if (!before.isFile() || !same(before, checked.stat) || before.size !== checked.stat.size) fail(context, 'file changed before read');
        verifyParents(checked.parents);
        const buffer = Buffer.alloc(Math.min(cap + 1, before.size + 1, limits.totalBytes - bytes + 1));
        let length = 0;
        while (length < buffer.length) {
          const count = fs.readSync(fd, buffer, length, buffer.length - length, null);
          if (!count) break;
          length += count;
        }
        bytes += length;
        if (!length || length > cap || bytes > limits.totalBytes) fail(context, 'read byte limit exceeded');
        const after = fs.fstatSync(fd);
        const final = fs.lstatSync(checked.file);
        if (length !== before.size || !same(before, after) || !same(before, final) ||
            after.size !== before.size || final.size !== before.size ||
            before.mtimeMs !== after.mtimeMs || before.ctimeMs !== after.ctimeMs ||
            before.mtimeMs !== final.mtimeMs || before.ctimeMs !== final.ctimeMs) fail(context, 'file changed during read');
        verifyParents(checked.parents);
        return buffer.subarray(0, length);
      } finally { fs.closeSync(fd); }
    }

    function manifest(folder, boundary, boundaryStat) {
      const buffer = read(path.join(folder, 'package.json'), boundary, boundaryStat, limits.manifestBytes);
      let value;
      try { value = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(buffer)); }
      catch { fail(context, 'invalid package.json JSON/UTF-8'); }
      if (!object(value)) fail(context, 'package.json must be an object');
      return value;
    }

    function dependencies(value) {
      const merged = new Map();
      for (const [field, kind] of [['peerDependencies', 'peer'], ['dependencies', 'required'], ['optionalDependencies', 'optional']]) {
        if (!Object.hasOwn(value, field)) continue;
        const deps = value[field];
        if (!object(deps)) fail(context, `${field} must be an object`);
        for (const name of Object.keys(deps).sort(compare)) {
          if (++edges > limits.edges) fail(context, 'dependency edge limit exceeded');
          if (!validName(name)) fail(context, `invalid package name in ${field}`);
          if (typeof deps[name] !== 'string' || !deps[name].trim() || deps[name].length > 4096) fail(context, `invalid dependency spec for ${name}`);
          merged.set(name, kind);
        }
      }
      return [...merged].sort(([a], [b]) => compare(a, b));
    }

    function resolve(from, name) {
      if (!modules) return null;
      let cursor = from;
      while (inside(root, cursor)) {
        // Node skips node_modules/node_modules, but still tries the surrounding
        // .pnpm/<entry>/node_modules when starting from a real pnpm package.
        if (path.basename(cursor) !== 'node_modules') {
          const candidate = path.join(cursor, 'node_modules', ...name.split('/'));
          if (inside(modules, candidate)) {
            let checked;
            try { checked = walk(candidate, modules, modulesStat); }
            catch (error) {
              // A dangling/unsafe link is an installed but broken package, not
              // an absent optional edge: never silently fall back past it.
              if (error.code !== 'ENOENT') throw error;
            }
            if (checked) {
              verifyParents(checked.parents);
              if (!checked.stat.isDirectory()) fail(context, `dependency ${name} is not a directory`);
              const canonical = fs.realpathSync(checked.file);
              if (!inside(modules, canonical)) fail(context, 'real package path escapes node_modules root');
              if (!same(checked.stat, fs.lstatSync(canonical))) fail(context, 'package changed during resolution');
              return canonical;
            }
          }
        }
        if (cursor === root) break;
        cursor = path.dirname(cursor);
      }
      return null;
    }

    function noticeFiles(folder) {
      const checked = walk(folder, modules, modulesStat, false);
      if (!checked.stat.isDirectory()) fail(context, 'package must be a directory');
      verifyParents([...checked.parents, { file: checked.file, stat: checked.stat }]);
      const dir = fs.opendirSync(checked.file);
      const names = [];
      try {
        let count = 0, entry;
        while ((entry = dir.readSync()) !== null) {
          if (++count > limits.directoryEntries) fail(context, 'package directory entry limit exceeded');
          if (noticePattern.test(entry.name)) {
            if (names.length >= limits.noticesPerPackage) fail(context, 'notice file count per package exceeded');
            names.push(entry.name);
          }
        }
      } finally { dir.closeSync(); }
      verifyParents([...checked.parents, { file: checked.file, stat: checked.stat }]);
      return names.sort(compare);
    }

    const top = manifest(root, root, rootStat);
    const topEdges = dependencies(top);
    if (topEdges.length) {
      const folder = path.join(root, 'node_modules');
      try {
        const stat = fs.lstatSync(folder);
        if (!stat.isDirectory() || stat.isSymbolicLink()) fail(context, 'node_modules root must be a real project-local directory');
        modules = folder;
        modulesStat = stat;
      } catch (error) { if (error.code !== 'ENOENT') throw error; }
    }

    // Optional publisher notices are supplied by the trusted skill manifest,
    // never resolved from package-controlled filesystem paths or the network.
    // Exact name/version binding keeps a grant from leaking to another release.
    if (!Array.isArray(supplementalNotices) || supplementalNotices.length > limits.packages) fail('supplements', 'invalid notice count');
    const supplemental = new Map();
    let supplementalBytes = 0;
    for (const notice of supplementalNotices) {
      if (!object(notice) || !validName(notice.package) ||
          typeof notice.version !== 'string' || !versionPattern.test(notice.version) ||
          typeof notice.name !== 'string' || !noticePattern.test(notice.name) ||
          notice.encoding !== 'base64' || typeof notice.content !== 'string' ||
          !/^[A-Za-z0-9+/]+={0,2}$/.test(notice.content) || notice.content.length > Math.ceil(limits.fileBytes / 3) * 4 ||
          typeof notice.sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(notice.sha256)) fail('supplements', 'invalid reviewed notice');
      supplementalBytes += notice.content.length;
      if (supplementalBytes > limits.totalBytes) fail('supplements', 'supplement byte limit exceeded');
      const raw = Buffer.from(notice.content, 'base64');
      if (!raw.length || raw.length > limits.fileBytes || raw.toString('base64') !== notice.content ||
          createHash('sha256').update(raw).digest('hex') !== notice.sha256) fail('supplements', 'notice digest/encoding mismatch');
      const key = `${notice.package}@${notice.version}`;
      if (supplemental.has(key)) fail('supplements', 'duplicate package/version notice');
      supplemental.set(key, notice);
    }

    const seen = new Map();
    function visit(from, list, depth, importer) {
      for (const [name, kind] of list) {
        context = `${name} (from ${importer})`;
        const folder = resolve(from, name);
        if (!folder) {
          if (kind === 'required') fail(context, 'missing required installed dependency');
          const code = kind === 'optional' ? 'RUNTIME_NOTICE_OPTIONAL_MISSING' : 'RUNTIME_NOTICE_PEER_MISSING';
          const diagnostic = { code, package: name, from: importer };
          diagnostics.push(diagnostic);
          process.emitWarning(`Runtime notices: missing ${kind} dependency ${name} (from ${importer}); skipped`, { code });
          continue;
        }
        // Cycle/alias edges to an already collected physical package consume no
        // recursion depth. Distinct installed versions keep distinct records.
        if (seen.has(folder)) continue;
        if (depth > limits.depth) fail(context, 'dependency depth limit exceeded');
        if (seen.size >= limits.packages) fail(context, 'package count limit exceeded');
        const value = manifest(folder, modules, modulesStat);
        if (!validName(value.name)) fail(context, 'invalid installed package name');
        if (typeof value.version !== 'string' || value.version.length > 256 || !versionPattern.test(value.version)) fail(context, 'invalid installed package version');
        const identity = `${value.name}@${value.version}`;
        seen.set(folder, identity);
        context = `${identity} (requested as ${name})`;
        const children = dependencies(value);
        const names = noticeFiles(folder);
        const reviewed = supplemental.get(identity);
        if (!names.length && !reviewed) fail(context, 'missing license/notice body (LICENSE, LICENCE, NOTICE or COPYING)');
        const installedBodies = new Set();
        for (const filename of names) {
          context = `${identity}/${filename}`;
          const content = read(path.join(folder, filename), modules, modulesStat, limits.fileBytes);
          const encoded = content.toString('base64');
          installedBodies.add(encoded);
          result.push({ name: filename, package: value.name, version: value.version, encoding: 'base64', content: encoded });
        }
        // Attribution-only NOTICE files never suppress a complete publisher
        // grant. Retain both; only identical bodies need no second copy.
        if (reviewed && !installedBodies.has(reviewed.content)) {
          const size = Buffer.from(reviewed.content, 'base64').length;
          if (++files > limits.files || (bytes += size) > limits.totalBytes) fail(context, 'supplement resource limit exceeded');
          result.push({ name: reviewed.name, package: value.name, version: value.version,
            encoding: 'base64', content: reviewed.content, source: reviewed.source,
            npm_integrity: reviewed.npm_integrity });
        }
        visit(folder, children, depth + 1, identity);
      }
    }
    visit(root, topEdges, 1, 'project');
    return result;
  } catch (error) {
    if (error instanceof Error && error.message.startsWith('Runtime notices:')) throw error;
    // Never interpolate JSON parser excerpts, filesystem paths or file bytes.
    fail(context, `filesystem operation failed (${typeof error.code === 'string' ? error.code : 'UNKNOWN'})`);
  }
}
