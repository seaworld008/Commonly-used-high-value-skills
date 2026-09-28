"use strict";

const fs = require("fs");
const path = require("path");

// Windows .cmd wrappers cannot be spawned directly with shell:false. Resolve
// npm's JavaScript entry point instead; arguments never enter a command shell.
function npmInvocation(name, options = {}) {
  if (!["npm", "npx"].includes(name)) throw new Error(`Unsupported npm command: ${name}`);
  const { platform = process.platform, execPath = process.execPath,
    env = process.env, exists = fs.existsSync } = options;
  if (platform !== "win32") return { command: name, args: [] };
  const entry = `${name}-cli.js`;
  const candidates = [];
  if (env.npm_execpath && /^(npm|npx)-cli\.js$/.test(path.basename(env.npm_execpath))) {
    candidates.push(path.join(path.dirname(env.npm_execpath), entry));
  }
  for (const dir of [path.dirname(execPath), ...(env.PATH || env.Path || "").split(path.delimiter)]) {
    if (dir) candidates.push(path.join(dir, "node_modules", "npm", "bin", entry));
  }
  const cli = candidates.find(exists);
  if (!cli) throw new Error(`Cannot locate ${name} npm CLI entry point; install Node.js with npm or run through npm exec.`);
  return { command: execPath, args: [cli] };
}

module.exports = { npmInvocation };
