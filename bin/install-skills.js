#!/usr/bin/env node
"use strict";

const crypto = require("crypto");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");
const { npmInvocation } = require("./npm-command");

const REPO_ROOT = path.resolve(__dirname, "..");
const PACKAGE = require(path.join(REPO_ROOT, "package.json"));
const INSTALLER_ID = "common-high-value-skills";
const MANIFEST_NAME = ".high-value-skills-manifest.json";
const DEFAULT_TARGET = "agents-project";
const BUNDLE_MANIFESTS = {
  "gsd-core": "open-gsd-core-2026-08.bundle.json",
  "gsd-pi": "open-gsd-pi-2026-08.bundle.json",
};
const BUNDLE_TARGET_FLAGS = {
  codex: "--codex",
  claude: "--claude",
  cursor: "--cursor",
  antigravity: "--antigravity",
};
const TARGETS = {
  "agents-project": {
    label: "project .agents skills",
    dest: () => path.resolve(process.cwd(), ".agents", "skills"),
    source: "skills",
  },
  codex: {
    label: "Codex user skills",
    dest: () => path.join(os.homedir(), ".codex", "skills"),
    source: "skills",
  },
  claude: {
    label: "Claude Code user skills",
    dest: () => path.join(os.homedir(), ".claude", "skills"),
    source: "skills",
  },
  cursor: {
    label: "Cursor user skills",
    dest: () => path.join(os.homedir(), ".cursor", "skills"),
    source: "skills",
  },
  antigravity: {
    label: "Antigravity user skills",
    dest: () =>
      path.join(
        process.env.ANTIGRAVITY_CONFIG_DIR || path.join(os.homedir(), ".gemini", "antigravity"),
        "skills"
      ),
    source: "skills",
  },
  "claude-project": {
    label: "Claude Code project skills",
    dest: () => path.resolve(process.cwd(), ".claude", "skills"),
    source: "skills",
  },
  openclaw: {
    label: "OpenClaw flat skills",
    dest: () => path.join(os.homedir(), ".openclaw", "skills"),
    source: "openclaw",
  },
};

function printHelp() {
  console.log(`Common High-Value Skills installer

Usage:
  high-value-skills install [options]
  high-value-skills list-targets
  high-value-skills list-skills [options]
  high-value-skills list-bundles
  high-value-skills audit-conflicts [--roots <paths>] [--json]

Examples:
  high-value-skills install --target codex
  high-value-skills install --target codex --dry-run
  high-value-skills install --target codex --prune-retired
  high-value-skills install --bundle gsd-core --target codex --dry-run
  high-value-skills audit-conflicts --roots ~/.codex/skills,~/.agents/skills

Options:
  --target <names>       Comma-separated targets: agents-project, codex, claude, cursor,
                         antigravity, claude-project, openclaw, custom. Default: ${DEFAULT_TARGET}
  --all                  Install normal skills to all standard skill targets.
  --dir <path>           Destination directory for one target; required for custom.
  --source-root <path>   Override categorized source skills root.
  --openclaw-root <path> Override flat OpenClaw source skills root.
  --category <names>     Install only matching categories.
  --skill <names>        Install only matching skill names.
  --bundle <name>        Explicitly install a governed bundle. Currently enabled: gsd-core.
  --prune-retired        Remove installer-owned unchanged retired skills; archive all others.
  --portfolio-policy <p> Override the retirement policy path.
  --roots <paths>        Roots for audit-conflicts (comma-separated).
  --json                 Emit machine-readable conflict audit output.
  --dry-run              Calculate and print the exact plan without writing or invoking installers.
  --help, -h             Show this help.

Safety:
  - Normal installation never includes installer-only bundles.
  - Each destination receives ${MANIFEST_NAME} with owner, source digest, file digest, and mode.
  - Modified or unowned replacements are archived; copies are staged and verified first.
  - Source/destination overlap and duplicate selected skill names are rejected before writes.
  - Dry-run performs no writes and never invokes an upstream installer.
  - Retired files are deleted only when this installer owns them and their digests are unchanged.
`);
}

function parseArgs(argv) {
  const args = {
    command: "install",
    targets: [DEFAULT_TARGET],
    all: false,
    destDir: null,
    sourceRoot: path.join(REPO_ROOT, "skills"),
    openclawRoot: path.join(REPO_ROOT, "openclaw-skills"),
    categories: [],
    skillNames: [],
    bundle: null,
    pruneRetired: false,
    portfolioPolicy: path.join(REPO_ROOT, "docs", "sources", "portfolio-policy.json"),
    roots: [],
    json: false,
    dryRun: false,
  };
  const input = [...argv];
  if (input[0] && !input[0].startsWith("-")) args.command = input.shift();
  const valueFlags = new Map([
    ["--target", "targets"],
    ["--dir", "destDir"],
    ["--source-root", "sourceRoot"],
    ["--openclaw-root", "openclawRoot"],
    ["--category", "categories"],
    ["--skill", "skillNames"],
    ["--bundle", "bundle"],
    ["--portfolio-policy", "portfolioPolicy"],
    ["--roots", "roots"],
  ]);
  for (let i = 0; i < input.length; i += 1) {
    let flag = input[i];
    if (flag === "--help" || flag === "-h") {
      args.command = "help";
    } else if (flag === "--all") {
      args.all = true;
    } else if (flag === "--dry-run") {
      args.dryRun = true;
    } else if (flag === "--prune-retired") {
      args.pruneRetired = true;
    } else if (flag === "--json") {
      args.json = true;
    } else {
      let key = valueFlags.get(flag);
      let value;
      if (key) {
        value = requireValue(input, ++i, flag);
      } else {
        const pair = [...valueFlags].find(([name]) => flag.startsWith(`${name}=`));
        if (!pair) throw new Error(`Unknown option: ${flag}`);
        [flag, key] = pair;
        value = input[i].slice(flag.length + 1);
        if (!value) throw new Error(`${flag} requires a value`);
      }
      if (["targets", "categories", "skillNames", "roots"].includes(key)) {
        args[key] = parseList(value, key === "roots");
      } else if (["destDir", "sourceRoot", "openclawRoot", "portfolioPolicy"].includes(key)) {
        args[key] = expandPath(value);
      } else {
        args[key] = value;
      }
    }
  }
  if (args.all) {
    args.targets = [
      "agents-project",
      "codex",
      "claude",
      "cursor",
      "antigravity",
      "claude-project",
      "openclaw",
    ];
  }
  return args;
}

function requireValue(input, index, flag) {
  const value = input[index];
  if (!value || value.startsWith("-")) throw new Error(`${flag} requires a value`);
  return value;
}

function parseList(value, paths = false) {
  const values = value.split(",").map((item) => item.trim()).filter(Boolean);
  return paths ? values.map(expandPath) : values;
}

function expandPath(value) {
  if (value === "~") return os.homedir();
  if (value.startsWith("~/")) return path.join(os.homedir(), value.slice(2));
  return path.resolve(process.cwd(), value);
}

function safeReaddir(dir) {
  if (!fs.existsSync(dir)) throw new Error(`Source directory does not exist: ${dir}`);
  return fs.readdirSync(dir).filter((name) => !name.startsWith("."));
}

function discoverCategorizedSkills(sourceRoot) {
  const skills = [];
  for (const category of safeReaddir(sourceRoot)) {
    const categoryPath = path.join(sourceRoot, category);
    if (!fs.statSync(categoryPath).isDirectory()) continue;
    for (const name of safeReaddir(categoryPath)) {
      const sourceDir = path.join(categoryPath, name);
      if (
        fs.statSync(sourceDir).isDirectory() &&
        fs.existsSync(path.join(sourceDir, "SKILL.md"))
      ) {
        skills.push({ name, category, sourceDir });
      }
    }
  }
  return skills.sort((a, b) => a.name.localeCompare(b.name));
}

function discoverFlatSkills(sourceRoot) {
  return safeReaddir(sourceRoot)
    .map((name) => ({ name, sourceDir: path.join(sourceRoot, name) }))
    .filter(
      (skill) =>
        fs.statSync(skill.sourceDir).isDirectory() &&
        fs.existsSync(path.join(skill.sourceDir, "SKILL.md"))
    )
    .sort((a, b) => a.name.localeCompare(b.name));
}

function filterSkills(skills, args) {
  const categoryFilter = new Set(args.categories);
  const nameFilter = new Set(args.skillNames);
  const categoriesByName =
    categoryFilter.size > 0
      ? new Map(
          discoverCategorizedSkills(args.sourceRoot).map((skill) => [
            skill.name,
            skill.category,
          ])
        )
      : new Map();
  const selected = skills.filter((skill) => {
    const category = skill.category || categoriesByName.get(skill.name);
    return (
      (categoryFilter.size === 0 || categoryFilter.has(category)) &&
      (nameFilter.size === 0 || nameFilter.has(skill.name))
    );
  });
  if ((categoryFilter.size || nameFilter.size) && selected.length === 0) {
    throw new Error("No skills matched the requested --category/--skill filters");
  }
  return selected;
}

function listTargets() {
  console.log("Available targets:");
  for (const [name, config] of Object.entries(TARGETS)) {
    console.log(`  ${name.padEnd(15)} ${config.label} -> ${config.dest()}`);
  }
  console.log("  custom          custom destination selected with --dir");
}

function listSkills(args) {
  const selected = filterSkills(discoverCategorizedSkills(args.sourceRoot), args);
  const grouped = new Map();
  for (const skill of selected) {
    if (!grouped.has(skill.category)) grouped.set(skill.category, []);
    grouped.get(skill.category).push(skill.name);
  }
  for (const category of [...grouped.keys()].sort()) {
    console.log(`${category}:`);
    for (const name of grouped.get(category).sort()) console.log(`  ${name}`);
  }
  console.log(`Total: ${selected.length} skills`);
}

function loadJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function loadBundle(name) {
  const fileName = BUNDLE_MANIFESTS[name];
  if (!fileName) {
    throw new Error(`Unknown bundle '${name}'. Run 'high-value-skills list-bundles'.`);
  }
  const manifestPath = path.join(REPO_ROOT, "docs", "sources", fileName);
  const data = loadJson(manifestPath);
  validateBundleManifest(data, name);
  return { data, manifestPath };
}

function validateBundleManifest(data, requestedName) {
  const bundle = data.bundle || {};
  const policy = data.install_policy || {};
  const inventory = data.bundle_inventory || {};
  const installer = data.installer || {};
  if (
    bundle.id !== requestedName ||
    policy.mode !== "explicit_only" ||
    policy.default_install !== false
  ) {
    throw new Error(
      `Bundle '${requestedName}' does not satisfy the explicit-only install contract`
    );
  }
  for (const field of ["package_files", "skills", "agents", "runtime_files"]) {
    if (!Number.isInteger(inventory[field]) || inventory[field] < 0) {
      throw new Error(`Bundle '${requestedName}' has invalid inventory.${field}`);
    }
  }
  if (installer.package_files !== inventory.package_files) {
    throw new Error(`Bundle '${requestedName}' package file count is inconsistent`);
  }
  if (
    !/^@[a-z0-9-]+\/[a-z0-9-]+@[0-9]+\.[0-9]+\.[0-9]+$/.test(
      installer.spec || ""
    )
  ) {
    throw new Error(`Bundle '${requestedName}' has an unsafe or unpinned installer spec`);
  }
  if (
    installer.registry !== "npm" ||
    installer.spec !== `${installer.package}@${installer.version}`
  ) {
    throw new Error(`Bundle '${requestedName}' has inconsistent installer metadata`);
  }
  if (!/^[0-9a-f]{64}$/.test(installer.tarball_sha256 || "")) {
    throw new Error(`Bundle '${requestedName}' has an invalid tarball digest`);
  }
  if (
    !/^sha512-[A-Za-z0-9+/]+={0,2}$/.test(installer.integrity || "") ||
    !/^[0-9a-f]{40}$/.test(installer.npm_shasum || "") ||
    !Number.isInteger(installer.unpacked_size) ||
    installer.unpacked_size < 0
  ) {
    throw new Error(`Bundle '${requestedName}' has incomplete package metadata`);
  }
}

function expectedNpmPackFilename(installer) {
  return (
    `${installer.package.replace(/^@/, "").replace(/\//g, "-")}-` +
    `${installer.version}.tgz`
  );
}

function downloadAndVerifyBundle(installer, tempDir) {
  const npm = npmInvocation("npm");
  const result = spawnSync(
    npm.command,
    [...npm.args, "pack", installer.spec, "--json", "--ignore-scripts"],
    {
      cwd: tempDir,
      encoding: "utf8",
      maxBuffer: 10 * 1024 * 1024,
      shell: false,
    }
  );
  if (result.error) {
    throw new Error(`Unable to download pinned bundle: ${result.error.message}`);
  }
  if (result.status !== 0) {
    const detail = (result.stderr || "").trim().slice(0, 500);
    throw new Error(
      `npm pack failed with status ${result.status}${detail ? `: ${detail}` : ""}`
    );
  }

  let records;
  try {
    records = JSON.parse(result.stdout);
  } catch {
    throw new Error("npm pack returned invalid JSON metadata");
  }
  if (!Array.isArray(records) || records.length !== 1) {
    throw new Error("npm pack did not return exactly one package record");
  }
  const record = records[0];
  const expectedFilename = expectedNpmPackFilename(installer);
  if (
    !record ||
    record.id !== installer.spec ||
    record.name !== installer.package ||
    record.version !== installer.version ||
    record.filename !== expectedFilename ||
    record.integrity !== installer.integrity ||
    record.shasum !== installer.npm_shasum ||
    record.unpackedSize !== installer.unpacked_size ||
    !Array.isArray(record.files) ||
    record.files.length !== installer.package_files
  ) {
    throw new Error("npm pack metadata does not match the governed bundle manifest");
  }

  const entries = fs.readdirSync(tempDir);
  if (entries.length !== 1 || entries[0] !== expectedFilename) {
    throw new Error("npm pack did not produce exactly the expected tarball");
  }
  const tarballPath = path.join(tempDir, expectedFilename);
  const stat = fs.lstatSync(tarballPath);
  if (stat.isSymbolicLink() || !stat.isFile() || stat.size !== record.size) {
    throw new Error("npm pack output is not the expected regular tarball");
  }
  const actualDigest = sha256File(tarballPath);
  if (
    !crypto.timingSafeEqual(
      Buffer.from(actualDigest, "hex"),
      Buffer.from(installer.tarball_sha256, "hex")
    )
  ) {
    throw new Error("Downloaded bundle tarball SHA-256 does not match the manifest");
  }
  return tarballPath;
}

function listBundles() {
  console.log("Governed bundles (never included in normal installation):");
  for (const name of Object.keys(BUNDLE_MANIFESTS).sort()) {
    const { data } = loadBundle(name);
    const enabled = name === "gsd-core";
    console.log(
      `  ${name.padEnd(10)} ${data.installer.spec}; ` +
        `${data.bundle_inventory.skills} skills, ${data.bundle_inventory.agents} agents; ` +
        `explicit-only; ${enabled ? "enabled" : "optional/list-only"}`
    );
  }
}

function resolveInstallPlan(args, target) {
  if (target === "custom") {
    if (!args.destDir) throw new Error("--target custom requires --dir <path>");
    return {
      target,
      label: "custom skills directory",
      destRoot: args.destDir,
      sourceRoot: args.sourceRoot,
      skills: filterSkills(discoverCategorizedSkills(args.sourceRoot), args),
    };
  }
  const config = TARGETS[target];
  if (!config) {
    throw new Error(`Unknown target '${target}'. Run 'high-value-skills list-targets'.`);
  }
  if (args.destDir && args.targets.length > 1) {
    throw new Error("--dir can only override a single target at a time");
  }
  const hasOpenClawExport =
    config.source === "openclaw" && fs.existsSync(args.openclawRoot);
  const sourceRoot = hasOpenClawExport ? args.openclawRoot : args.sourceRoot;
  return {
    target,
    label: config.label,
    destRoot: args.destDir || config.dest(),
    sourceRoot,
    skills: filterSkills(
      hasOpenClawExport
        ? discoverFlatSkills(sourceRoot)
        : discoverCategorizedSkills(sourceRoot),
      args
    ),
  };
}

function relativeFiles(root) {
  const result = [];
  function walk(dir, prefix) {
    for (const name of fs.readdirSync(dir).sort()) {
      if (name === "__pycache__") continue;
      const absolute = path.join(dir, name);
      const relative = prefix ? path.posix.join(prefix, name) : name;
      const stat = fs.lstatSync(absolute);
      if (stat.isSymbolicLink()) {
        throw new Error(`Symbolic links are not supported in managed skills: ${absolute}`);
      }
      if (stat.isDirectory()) walk(absolute, relative);
      else if (stat.isFile()) result.push({ absolute, relative, stat });
    }
  }
  walk(root, "");
  return result;
}

function sha256File(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

function lstatExists(file) {
  try {
    fs.lstatSync(file);
    return true;
  } catch (error) {
    if (error.code === "ENOENT") return false;
    throw error;
  }
}

function inventorySkill(root, owner) {
  const files = relativeFiles(root).map(({ absolute, relative, stat }) => ({
    path: relative,
    sha256: sha256File(absolute),
    mode: (stat.mode & 0o777).toString(8).padStart(3, "0"),
    owner,
  }));
  const tree = crypto.createHash("sha256");
  for (const file of files) {
    tree.update(`${file.path}\0${file.sha256}\0${file.mode}\n`);
  }
  return { source_digest: tree.digest("hex"), files };
}

function readInstallManifest(destRoot) {
  const manifestPath = path.join(destRoot, MANIFEST_NAME);
  if (!fs.existsSync(manifestPath)) {
    return {
      schema_version: 1,
      installer: INSTALLER_ID,
      installer_version: PACKAGE.version,
      skills: {},
    };
  }
  const data = loadJson(manifestPath);
  if (
    data.schema_version !== 1 ||
    data.installer !== INSTALLER_ID ||
    !data.skills ||
    typeof data.skills !== "object" ||
    Array.isArray(data.skills)
  ) {
    throw new Error(`Refusing invalid or foreign install manifest: ${manifestPath}`);
  }
  for (const [name, entry] of Object.entries(data.skills)) {
    const safeName = /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(name);
    const safeDigest = /^[0-9a-f]{64}$/.test(entry && entry.source_digest);
    const safeFiles =
      entry &&
      entry.owner === name &&
      Array.isArray(entry.files) &&
      entry.files.every(
        (file) =>
          file &&
          file.owner === name &&
          typeof file.path === "string" &&
          file.path.length > 0 &&
          !path.posix.isAbsolute(file.path) &&
          !file.path.includes("\\") &&
          !file.path.split("/").includes("..") &&
          /^[0-9a-f]{64}$/.test(file.sha256) &&
          /^(?:[0-7]{3}|[0-7]{4})$/.test(file.mode)
      );
    if (!safeName || !safeDigest || !safeFiles) {
      throw new Error(`Refusing malformed ownership entry '${name}' in ${manifestPath}`);
    }
  }
  return data;
}

function writeJsonAtomic(file, data) {
  const temp = `${file}.tmp-${process.pid}-${crypto.randomBytes(6).toString("hex")}`;
  fs.writeFileSync(temp, `${JSON.stringify(data, null, 2)}\n`, {
    mode: 0o600,
    flag: "wx",
  });
  fs.renameSync(temp, file);
}

// Resolve the nearest existing ancestor too, so aliases and not-yet-created
// destination descendants receive the same overlap checks as existing paths.
function canonicalPath(file, allowDanglingLeaf = false) {
  const absolute = path.resolve(file);
  if (lstatExists(absolute)) {
    try {
      return fs.realpathSync(absolute);
    } catch (error) {
      // A missing leaf link will be archived, not traversed. Ancestor links
      // remain strict so an unresolved alias cannot hide a source overlap.
      if (!allowDanglingLeaf || error.code !== "ENOENT" ||
          !fs.lstatSync(absolute).isSymbolicLink()) throw error;
      return path.join(canonicalPath(path.dirname(absolute)), path.basename(absolute));
    }
  }
  const parent = path.dirname(absolute);
  if (parent === absolute) return absolute;
  return path.join(canonicalPath(parent), path.basename(absolute));
}

function pathsOverlap(left, right) {
  function contains(parent, child) {
    const relative = path.relative(parent, child);
    return relative === "" ||
      (relative !== ".." && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative));
  }
  return contains(left, right) || contains(right, left);
}

function prepareInstallPlans(plans) {
  const sources = plans.flatMap((plan) => [canonicalPath(plan.sourceRoot),
    ...plan.skills.map((skill) => canonicalPath(skill.sourceDir))]);
  const destinations = plans.map((plan) => canonicalPath(plan.destRoot, true));
  for (let i = 0; i < plans.length; i += 1) {
    if (sources.some((source) => pathsOverlap(source, destinations[i]))) {
      throw new Error(`Source and destination overlap: ${plans[i].destRoot}`);
    }
    if (destinations.slice(0, i).some((dest) => pathsOverlap(dest, destinations[i]))) {
      throw new Error(`Installation destinations overlap: ${plans[i].destRoot}`);
    }
  }
  return plans.map((plan) => {
    const manifest = readInstallManifest(plan.destRoot);
    const expected = new Map();
    for (const skill of plan.skills) {
      if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(skill.name)) {
        throw new Error(`Unsafe skill name: ${skill.name}`);
      }
      if (expected.has(skill.name)) throw new Error(`Duplicate skill name: ${skill.name}`);
      if (!fs.lstatSync(skill.sourceDir).isDirectory()) {
        throw new Error(`Skill source must be a real directory: ${skill.sourceDir}`);
      }
      const inventory = inventorySkill(skill.sourceDir, skill.name);
      expected.set(skill.name, { ...inventory, owner: skill.name });
    }
    const danglingDestination = lstatExists(plan.destRoot) &&
      fs.lstatSync(plan.destRoot).isSymbolicLink() && !fs.existsSync(plan.destRoot)
      ? fs.readlinkSync(plan.destRoot) : null;
    return { ...plan, manifest, expected, danglingDestination };
  });
}

function copySkill(sourceDir, destDir, expected, owned, archive) {
  const stage = fs.mkdtempSync(path.join(path.dirname(destDir), ".high-value-skills-stage-"));
  const next = path.join(stage, "next");
  let previous = null;
  let preserveStage = false;
  let archived = false;
  try {
    fs.cpSync(sourceDir, next, {
      recursive: true,
      filter: (source) => !source.split(path.sep).includes("__pycache__"),
    });
    if (!inventoryMatches(next, expected)) {
      throw new Error(`Staged skill failed inventory verification: ${sourceDir}`);
    }
    // Recheck ownership after copying, immediately before moving the old tree.
    if (lstatExists(destDir)) {
      archived = !owned || !inventoryMatches(destDir, owned);
      previous = archived ? archive : path.join(stage, "previous");
      fs.mkdirSync(path.dirname(previous), { recursive: true });
      if (lstatExists(previous)) throw new Error(`Backup destination already exists: ${previous}`);
      fs.renameSync(destDir, previous);
    }
    try {
      fs.renameSync(next, destDir);
    } catch (error) {
      if (previous) {
        try {
          if (lstatExists(destDir)) throw new Error("destination changed concurrently");
          fs.renameSync(previous, destDir);
        } catch (restoreError) {
          preserveStage = true;
          throw new Error(`Install failed: ${error.message}; rollback failed: ${restoreError.message}; previous copy preserved at ${previous}`);
        }
      }
      throw error;
    }
    return archived;
  } finally {
    if (!preserveStage) fs.rmSync(stage, { recursive: true, force: true });
  }
}

function inventoryMatches(root, expected) {
  if (!lstatExists(root) || !fs.lstatSync(root).isDirectory()) return false;
  try {
    const actual = inventorySkill(root, expected.owner);
    return (
      actual.source_digest === expected.source_digest &&
      JSON.stringify(actual.files) === JSON.stringify(expected.files)
    );
  } catch {
    return false;
  }
}

function backupRoot(destRoot, timestamp) {
  return path.join(
    path.dirname(destRoot),
    ".high-value-skills-backups",
    timestamp,
    path.basename(destRoot)
  );
}

function pruneRetired(destRoot, manifest, policyPath, dryRun, timestamp) {
  const policy = loadJson(policyPath);
  if (!Array.isArray(policy.retired_skills)) {
    throw new Error(`Invalid portfolio policy: ${policyPath}`);
  }
  const result = { deleted: [], archived: [], absent: [] };
  for (const item of policy.retired_skills) {
    const name = item.name;
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(name)) {
      throw new Error(`Unsafe retired skill name: ${name}`);
    }
    const current = path.join(destRoot, name);
    if (!lstatExists(current)) {
      result.absent.push(name);
      delete manifest.skills[name];
      continue;
    }
    const owned = manifest.skills[name];
    if (owned && inventoryMatches(current, owned)) {
      result.deleted.push(name);
      if (!dryRun) fs.rmSync(current, { recursive: true, force: true });
    } else {
      result.archived.push(name);
      if (!dryRun) {
        const archive = path.join(backupRoot(destRoot, timestamp), name);
        fs.mkdirSync(path.dirname(archive), { recursive: true });
        if (lstatExists(archive)) {
          throw new Error(`Backup destination already exists: ${archive}`);
        }
        fs.renameSync(current, archive);
      }
    }
    delete manifest.skills[name];
  }
  return result;
}

function installDanglingDestination(plan, args, timestamp) {
  // Build the complete new root before moving the user's link. A failed copy
  // leaves it untouched; a failed final rename restores it from the archive.
  const stage = fs.mkdtempSync(path.join(path.dirname(plan.destRoot), ".high-value-skills-root-"));
  const archive = `${backupRoot(plan.destRoot, timestamp)}.symlink`;
  try {
    const summary = installPlan({ ...plan, destRoot: stage, danglingDestination: null }, args, timestamp);
    if (!lstatExists(plan.destRoot) || !fs.lstatSync(plan.destRoot).isSymbolicLink() ||
        fs.existsSync(plan.destRoot) || fs.readlinkSync(plan.destRoot) !== plan.danglingDestination) {
      throw new Error(`Destination symlink changed concurrently: ${plan.destRoot}`);
    }
    fs.mkdirSync(path.dirname(archive), { recursive: true });
    if (lstatExists(archive)) throw new Error(`Backup destination already exists: ${archive}`);
    fs.renameSync(plan.destRoot, archive);
    try {
      fs.renameSync(stage, plan.destRoot);
    } catch (error) {
      try {
        if (lstatExists(plan.destRoot)) throw new Error("destination changed concurrently");
        fs.renameSync(archive, plan.destRoot);
      } catch (restoreError) {
        throw new Error(`Install failed: ${error.message}; rollback failed: ${restoreError.message}; original link preserved at ${archive}`);
      }
      throw error;
    }
    return { ...summary, destRoot: plan.destRoot, archivedDestination: archive };
  } finally {
    // Never remove the archive: it remains the user's recoverable original.
    if (lstatExists(stage)) fs.rmSync(stage, { recursive: true, force: true });
  }
}

function installPlan(plan, args, timestamp) {
  if (plan.danglingDestination !== null && !args.dryRun) {
    return installDanglingDestination(plan, args, timestamp);
  }
  const { manifest, expected } = plan;
  if (!args.dryRun) fs.mkdirSync(plan.destRoot, { recursive: true });
  let archived = 0;
  let added = 0;
  let updated = 0;
  let unchanged = 0;
  for (const skill of plan.skills) {
    const destDir = path.join(plan.destRoot, skill.name);
    const entry = expected.get(skill.name);
    const matches = inventoryMatches(destDir, entry);
    if (matches) unchanged += 1;
    else if (lstatExists(destDir)) updated += 1;
    else added += 1;
    if (!matches) {
      const owned = manifest.skills[skill.name];
      if (args.dryRun) {
        if (lstatExists(destDir) && (!owned || !inventoryMatches(destDir, owned))) archived += 1;
      } else if (copySkill(skill.sourceDir, destDir, entry, owned,
        path.join(backupRoot(plan.destRoot, timestamp), skill.name))) {
        archived += 1;
      }
    }
    manifest.skills[skill.name] = entry;
  }
  let pruned = { deleted: [], archived: [], absent: [] };
  if (args.pruneRetired) {
    pruned = pruneRetired(
      plan.destRoot,
      manifest,
      args.portfolioPolicy,
      args.dryRun,
      timestamp
    );
  }
  if (!args.dryRun) {
    manifest.installer_version = PACKAGE.version;
    manifest.updated_at = new Date().toISOString();
    writeJsonAtomic(path.join(plan.destRoot, MANIFEST_NAME), manifest);
  }
  const selected = new Set(plan.skills.map((skill) => skill.name));
  const existing = fs.existsSync(plan.destRoot)
    ? fs
        .readdirSync(plan.destRoot)
        .filter(
          (name) =>
            !name.startsWith(".") &&
            fs.lstatSync(path.join(plan.destRoot, name)).isDirectory()
        )
    : [];
  return {
    ...plan,
    skillCount: plan.skills.length,
    added,
    updated,
    unchanged,
    archived,
    preserved: existing.filter((name) => !selected.has(name)).length,
    pruned,
  };
}

function runBundle(args) {
  if (args.bundle !== "gsd-core") {
    if (args.bundle === "gsd-pi") {
      throw new Error(
        "Bundle 'gsd-pi' is optional/list-only in this release and is not enabled for installation"
      );
    }
    loadBundle(args.bundle);
  }
  if (
    args.all ||
    args.destDir ||
    args.categories.length ||
    args.skillNames.length ||
    args.pruneRetired
  ) {
    throw new Error(
      "--bundle cannot be combined with --all, --dir, skill filters, or --prune-retired"
    );
  }
  if (args.targets.length !== 1) {
    throw new Error(
      "--bundle accepts exactly one target per invocation so each client can be verified before continuing"
    );
  }
  const { data } = loadBundle(args.bundle);
  const flags = args.targets.map((target) => {
    const flag = BUNDLE_TARGET_FLAGS[target];
    if (!flag) {
      throw new Error(`Bundle '${args.bundle}' does not support target '${target}'`);
    }
    return flag;
  });
  const commandArgs = ["--yes", data.installer.spec, ...flags, "--global"];
  const expected =
    `${data.bundle_inventory.skills} skills, ` +
    `${data.bundle_inventory.agents} agents, ` +
    `${data.bundle_inventory.commands} commands, ` +
    `${data.bundle_inventory.runtime_files} runtime files`;
  if (args.dryRun) {
    console.log(`[dry-run] Would run: npx ${commandArgs.join(" ")}`);
    console.log(`[dry-run] Acceptance contract from pinned manifest: ${expected}.`);
    return 0;
  }
  const tempDir = fs.mkdtempSync(
    path.join(os.tmpdir(), `${INSTALLER_ID}-bundle-`)
  );
  if (process.platform !== "win32") fs.chmodSync(tempDir, 0o700);
  try {
    const tarballPath = downloadAndVerifyBundle(data.installer, tempDir);
    const verifiedCommandArgs = ["--yes", tarballPath, ...flags, "--global"];
    const npx = npmInvocation("npx");
    const result = spawnSync(npx.command, [...npx.args, ...verifiedCommandArgs], {
      stdio: "inherit",
      shell: false,
    });
    if (result.error) {
      throw new Error(`Unable to run verified bundle installer: ${result.error.message}`);
    }
    if (result.status !== 0) {
      throw new Error(
        `Official ${args.bundle} installer exited with status ${result.status}`
      );
    }
  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
  console.log(
    `Installed governed bundle ${args.bundle} (${data.installer.spec}). ` +
      `Expected inventory: ${expected}.`
  );
  return 0;
}

function directSkillDirectories(root) {
  if (!fs.existsSync(root)) return [];
  return fs
    .readdirSync(root)
    .sort()
    .filter((name) => {
      const candidate = path.join(root, name);
      return (
        fs.lstatSync(candidate).isDirectory() &&
        fs.existsSync(path.join(candidate, "SKILL.md"))
      );
    });
}

function auditConflicts(args) {
  const roots = args.roots.length
    ? args.roots
    : [
        path.join(os.homedir(), ".codex", "skills"),
        path.join(os.homedir(), ".agents", "skills"),
      ];
  const rows = [];
  for (const root of roots) {
    let manifest = null;
    try {
      manifest = readInstallManifest(root);
    } catch {
      manifest = null;
    }
    for (const name of directSkillDirectories(root)) {
      const inventory = inventorySkill(path.join(root, name), name);
      const managed = manifest && manifest.skills[name];
      rows.push({
        name,
        root,
        digest: inventory.source_digest,
        ownership:
          managed && inventoryMatches(path.join(root, name), managed)
            ? INSTALLER_ID
            : "unowned-or-modified",
      });
    }
  }
  const byName = new Map();
  for (const row of rows) {
    if (!byName.has(row.name)) byName.set(row.name, []);
    byName.get(row.name).push(row);
  }
  const matrix = [...byName]
    .filter(([, entries]) => entries.length > 1)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([name, entries]) => ({
      name,
      conflict: new Set(entries.map((entry) => entry.digest)).size > 1,
      entries,
    }));
  const result = {
    roots,
    duplicate_names: matrix.length,
    content_conflicts: matrix.filter((item) => item.conflict).length,
    matrix,
  };
  if (args.json) {
    console.log(JSON.stringify(result, null, 2));
  } else {
    console.log("name\tconflict\townership\troot\tdigest");
    for (const item of matrix) {
      for (const entry of item.entries) {
        console.log(
          `${item.name}\t${item.conflict ? "yes" : "no"}\t${entry.ownership}\t` +
            `${entry.root}\t${entry.digest}`
        );
      }
    }
    console.log(
      `Duplicate names: ${result.duplicate_names}; ` +
        `content conflicts: ${result.content_conflicts}.`
    );
  }
  return 0;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.command === "help") {
    printHelp();
    return 0;
  }
  if (args.command === "list-targets") {
    listTargets();
    return 0;
  }
  if (args.command === "list-skills") {
    listSkills(args);
    return 0;
  }
  if (args.command === "list-bundles") {
    listBundles();
    return 0;
  }
  if (args.command === "audit-conflicts") return auditConflicts(args);
  if (args.command !== "install") throw new Error(`Unknown command: ${args.command}`);
  if (args.bundle) return runBundle(args);

  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const plans = prepareInstallPlans(args.targets.map((target) => resolveInstallPlan(args, target)));
  const summaries = plans.map((plan) => installPlan(plan, args, timestamp));
  for (const summary of summaries) {
    const prefix = args.dryRun ? "[dry-run] Would reconcile" : "Installed";
    console.log(
      `${prefix} ${summary.skillCount} skills to ${summary.label} ` +
        `(${summary.destRoot}). Added: ${summary.added}, Updated: ${summary.updated}, ` +
        `Unchanged: ${summary.unchanged}, Preserved extras: ${summary.preserved}. ` +
        `Archived replacements: ${summary.archived}.`
    );
    if (summary.archivedDestination) {
      console.log(`Archived destination symlink: ${summary.archivedDestination}`);
    }
    if (args.pruneRetired) {
      console.log(
        `${args.dryRun ? "[dry-run] " : ""}Retired: ` +
          `delete ${summary.pruned.deleted.length}, ` +
          `archive ${summary.pruned.archived.length}, ` +
          `absent ${summary.pruned.absent.length}.`
      );
    }
  }
  return 0;
}

try {
  process.exitCode = main();
} catch (error) {
  console.error(`error: ${error.message}`);
  process.exitCode = 1;
}
