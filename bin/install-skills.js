#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");

const REPO_ROOT = path.resolve(__dirname, "..");
const DEFAULT_TARGET = "agents-project";
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

Examples:
  npx github:seaworld008/Commonly-used-high-value-skills install
  npx github:seaworld008/Commonly-used-high-value-skills install --target codex,claude
  npx github:seaworld008/Commonly-used-high-value-skills install --all
  npx github:seaworld008/Commonly-used-high-value-skills install --target custom --dir ./vendor/skills

Options:
  --target <names>       Comma-separated targets: agents-project, codex, claude, claude-project, openclaw, custom.
                         Default: ${DEFAULT_TARGET}
  --all                  Install to agents-project, codex, claude, claude-project, and openclaw.
  --dir <path>           Destination directory. Required for --target custom; overrides destination for one target.
  --source-root <path>   Override categorized source skills root. Mainly useful for tests or local forks.
  --openclaw-root <path> Override flat OpenClaw source skills root. If unavailable, categorized skills are flattened.
  --dry-run              Print what would be installed without writing files.
  --help, -h             Show this help.

Notes:
  - Categorized skills are flattened during install so clients can discover each skill by name.
  - Existing skills with the same name are replaced; unrelated existing skills in the destination are preserved.
  - OpenClaw uses openclaw-skills/ when available; npm installs fall back to flattening skills/.
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
    dryRun: false,
  };

  const input = [...argv];
  if (input[0] && !input[0].startsWith("-")) {
    args.command = input.shift();
  }

  for (let i = 0; i < input.length; i += 1) {
    const flag = input[i];
    if (flag === "--help" || flag === "-h") {
      args.command = "help";
    } else if (flag === "--all") {
      args.all = true;
    } else if (flag === "--dry-run") {
      args.dryRun = true;
    } else if (flag === "--target") {
      args.targets = parseTargetList(requireValue(input, ++i, flag));
    } else if (flag.startsWith("--target=")) {
      args.targets = parseTargetList(flag.slice("--target=".length));
    } else if (flag === "--dir") {
      args.destDir = expandPath(requireValue(input, ++i, flag));
    } else if (flag.startsWith("--dir=")) {
      args.destDir = expandPath(flag.slice("--dir=".length));
    } else if (flag === "--source-root") {
      args.sourceRoot = expandPath(requireValue(input, ++i, flag));
    } else if (flag.startsWith("--source-root=")) {
      args.sourceRoot = expandPath(flag.slice("--source-root=".length));
    } else if (flag === "--openclaw-root") {
      args.openclawRoot = expandPath(requireValue(input, ++i, flag));
    } else if (flag.startsWith("--openclaw-root=")) {
      args.openclawRoot = expandPath(flag.slice("--openclaw-root=".length));
    } else {
      throw new Error(`Unknown option: ${flag}`);
    }
  }

  if (args.all) {
    args.targets = ["agents-project", "codex", "claude", "claude-project", "openclaw"];
  }
  return args;
}

function requireValue(input, index, flag) {
  const value = input[index];
  if (!value || value.startsWith("-")) {
    throw new Error(`${flag} requires a value`);
  }
  return value;
}

function parseTargetList(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function expandPath(value) {
  if (value === "~") {
    return os.homedir();
  }
  if (value.startsWith("~/")) {
    return path.join(os.homedir(), value.slice(2));
  }
  return path.resolve(process.cwd(), value);
}

function listTargets() {
  console.log("Available targets:");
  for (const [name, config] of Object.entries(TARGETS)) {
    console.log(`  ${name.padEnd(15)} ${config.label} -> ${config.dest()}`);
  }
  console.log("  custom          custom destination selected with --dir");
}

function discoverCategorizedSkills(sourceRoot) {
  const skills = [];
  for (const category of safeReaddir(sourceRoot)) {
    const categoryPath = path.join(sourceRoot, category);
    if (!fs.statSync(categoryPath).isDirectory()) {
      continue;
    }
    for (const skillName of safeReaddir(categoryPath)) {
      const skillPath = path.join(categoryPath, skillName);
      if (fs.statSync(skillPath).isDirectory() && fs.existsSync(path.join(skillPath, "SKILL.md"))) {
        skills.push({ name: skillName, sourceDir: skillPath });
      }
    }
  }
  return skills.sort((a, b) => a.name.localeCompare(b.name));
}

function discoverFlatSkills(sourceRoot) {
  return safeReaddir(sourceRoot)
    .map((skillName) => ({ name: skillName, sourceDir: path.join(sourceRoot, skillName) }))
    .filter((skill) => fs.statSync(skill.sourceDir).isDirectory() && fs.existsSync(path.join(skill.sourceDir, "SKILL.md")))
    .sort((a, b) => a.name.localeCompare(b.name));
}

function safeReaddir(dir) {
  if (!fs.existsSync(dir)) {
    throw new Error(`Source directory does not exist: ${dir}`);
  }
  return fs.readdirSync(dir).filter((name) => !name.startsWith("."));
}

function resolveInstallPlan(args, target) {
  if (target === "custom") {
    if (!args.destDir) {
      throw new Error("--target custom requires --dir <path>");
    }
    return {
      target,
      label: "custom skills directory",
      destRoot: args.destDir,
      skills: discoverCategorizedSkills(args.sourceRoot),
    };
  }

  const config = TARGETS[target];
  if (!config) {
    throw new Error(`Unknown target '${target}'. Run 'high-value-skills list-targets'.`);
  }
  if (args.destDir && args.targets.length > 1) {
    throw new Error("--dir can only override a single target at a time");
  }

  const hasOpenClawExport = config.source === "openclaw" && fs.existsSync(args.openclawRoot);
  const sourceRoot = hasOpenClawExport ? args.openclawRoot : args.sourceRoot;
  const skills = hasOpenClawExport ? discoverFlatSkills(sourceRoot) : discoverCategorizedSkills(sourceRoot);
  return {
    target,
    label: config.label,
    destRoot: args.destDir || config.dest(),
    skills,
  };
}

function copySkill(sourceDir, destDir) {
  fs.rmSync(destDir, { recursive: true, force: true });
  fs.cpSync(sourceDir, destDir, {
    recursive: true,
    filter: (source) => !source.split(path.sep).includes("__pycache__"),
  });
}

function installPlan(plan, dryRun) {
  const existing = fs.existsSync(plan.destRoot)
    ? new Set(
        fs
          .readdirSync(plan.destRoot)
          .filter((name) => fs.statSync(path.join(plan.destRoot, name)).isDirectory())
      )
    : new Set();

  let added = 0;
  let updated = 0;
  if (!dryRun) {
    fs.mkdirSync(plan.destRoot, { recursive: true });
  }

  for (const skill of plan.skills) {
    const destDir = path.join(plan.destRoot, skill.name);
    if (existing.has(skill.name)) {
      updated += 1;
    } else {
      added += 1;
    }
    if (!dryRun) {
      copySkill(skill.sourceDir, destDir);
    }
  }

  const preserved = [...existing].filter((name) => !plan.skills.some((skill) => skill.name === name)).sort();
  return {
    target: plan.target,
    label: plan.label,
    destRoot: plan.destRoot,
    skillCount: plan.skills.length,
    added,
    updated,
    preserved: preserved.length,
  };
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
  if (args.command !== "install") {
    throw new Error(`Unknown command: ${args.command}`);
  }

  const summaries = [];
  for (const target of args.targets) {
    const plan = resolveInstallPlan(args, target);
    summaries.push(installPlan(plan, args.dryRun));
  }

  for (const summary of summaries) {
    const prefix = args.dryRun ? "[dry-run] Would install" : "Installed";
    console.log(
      `${prefix} ${summary.skillCount} skills to ${summary.label} (${summary.destRoot}). ` +
        `Added: ${summary.added}, Updated: ${summary.updated}, Preserved extras: ${summary.preserved}.`
    );
  }
  return 0;
}

try {
  process.exitCode = main();
} catch (error) {
  console.error(`error: ${error.message}`);
  process.exitCode = 1;
}
