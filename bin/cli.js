#!/usr/bin/env node
"use strict";

/**
 * Install portable agent skills into agent skill directories.
 *
 * Mirrors scripts/install.py. Node has no dependencies here on purpose: the
 * package must run under `npx` with nothing else present.
 *
 * Unlike the Python installer, this copies rather than symlinks. An npx cache
 * directory is transient, so a symlink into it would dangle as soon as npm
 * cleans up.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");

// agent -> install directory. Keep in sync with AGENT_TARGETS in scripts/skilllib.py.
const AGENT_TARGETS = {
  jcode: "~/.jcode/skills",
  claude: "~/.claude/skills",
  codex: "~/.codex/skills",
  windsurf: "~/.codeium/windsurf/skills",
  cursor: "~/.cursor/skills",
  opencode: "~/.config/opencode/skills",
};

// Agents whose primary entry point is a single rules file; they also get a
// generated index so the skills are discoverable.
const POINTER_FILES = {
  codex: "~/.codex/AGENTS.md",
  windsurf: "~/.codeium/windsurf/memories/global_rules.md",
  cursor: "~/.cursor/rules/skills.mdc",
};

const BEGIN = "<!-- BEGIN managed skills index -->";
const END = "<!-- END managed skills index -->";

const SKILLS_DIR = path.join(__dirname, "..", "skills");

function expand(p) {
  return p.startsWith("~") ? path.join(os.homedir(), p.slice(1)) : path.resolve(p);
}

/** Minimal frontmatter reader: only the keys the installer needs. */
function parseFrontmatter(text) {
  if (!text.startsWith("---")) return {};
  const lines = text.split(/\r?\n/);
  let end = -1;
  for (let i = 1; i < lines.length; i++) {
    if (lines[i].trim() === "---") {
      end = i;
      break;
    }
  }
  if (end === -1) return {};

  const meta = {};
  for (const line of lines.slice(1, end)) {
    if (!line.trim() || line.trimStart().startsWith("#")) continue;
    const idx = line.indexOf(":");
    if (idx === -1) continue;
    const key = line.slice(0, idx).trim();
    let raw = line.slice(idx + 1).trim();
    if (raw.startsWith("[") && raw.endsWith("]")) {
      const inner = raw.slice(1, -1).trim();
      meta[key] = inner ? inner.split(",").map((s) => unquote(s.trim())) : [];
    } else {
      meta[key] = unquote(raw);
    }
  }
  return meta;
}

function unquote(s) {
  if (s.length >= 2 && s[0] === s[s.length - 1] && (s[0] === '"' || s[0] === "'")) {
    return s.slice(1, -1);
  }
  return s;
}

function discover(names) {
  if (!fs.existsSync(SKILLS_DIR)) return [];
  return fs
    .readdirSync(SKILLS_DIR, { withFileTypes: true })
    .filter((e) => e.isDirectory() && !e.name.startsWith("."))
    .filter((e) => !names || names.has(e.name))
    .map((e) => {
      const dir = path.join(SKILLS_DIR, e.name);
      const md = path.join(dir, "SKILL.md");
      const meta = fs.existsSync(md) ? parseFrontmatter(fs.readFileSync(md, "utf8")) : {};
      return { name: meta.name || e.name, dir, meta, missing: !fs.existsSync(md) };
    })
    .sort((a, b) => a.name.localeCompare(b.name));
}

function targetsFor(skill) {
  let agents = skill.meta.agents || ["all"];
  if (typeof agents === "string") agents = [agents];
  agents = agents.map((a) => String(a).trim().toLowerCase());
  if (agents.includes("all")) return Object.keys(AGENT_TARGETS).sort();
  return agents.filter((a) => a in AGENT_TARGETS);
}

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name);
    const d = path.join(dest, entry.name);
    if (entry.isDirectory()) copyDir(s, d);
    else if (entry.isSymbolicLink()) fs.symlinkSync(fs.readlinkSync(s), d);
    else fs.copyFileSync(s, d);
  }
}

function install(skill, dest, { force, dry }) {
  const exists = fs.existsSync(dest) || isSymlink(dest);
  if (exists && !force) return "exists (use --force)";
  if (dry) return exists ? "would replace" : "would install";
  if (exists) rm(dest);
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  copyDir(skill.dir, dest);
  return "installed";
}

function isSymlink(p) {
  try {
    return fs.lstatSync(p).isSymbolicLink();
  } catch {
    return false;
  }
}

function rm(p) {
  if (isSymlink(p)) fs.unlinkSync(p);
  else fs.rmSync(p, { recursive: true, force: true });
}

function uninstall(dest, { dry }) {
  if (!fs.existsSync(dest) && !isSymlink(dest)) return "absent";
  if (dry) return "would remove";
  rm(dest);
  return "removed";
}

function writePointer(agent, skills, { dry }) {
  const target = expand(POINTER_FILES[agent]);
  // Expanded, not "~": scripts/install.py writes the absolute path, and the two
  // installers must produce a byte-identical block or they rewrite each other.
  const root = expand(AGENT_TARGETS[agent]);
  const lines = [
    BEGIN,
    "",
    "## Available skills",
    "",
    `Skill instructions live in \`${root}/<name>/SKILL.md\`.`,
    "Read the matching SKILL.md in full before acting on its topic.",
    "",
  ];
  for (const s of skills) lines.push(`- **${s.name}** — ${s.meta.description || ""}`);
  lines.push("", END, "");
  const block = lines.join("\n");

  const existing = fs.existsSync(target) ? fs.readFileSync(target, "utf8") : "";
  let next;
  if (existing.includes(BEGIN) && existing.includes(END)) {
    const head = existing.slice(0, existing.indexOf(BEGIN));
    const tail = existing.slice(existing.indexOf(END) + END.length).replace(/^\n+/, "");
    next = head + block + tail;
  } else {
    next = (existing.trim() ? existing.replace(/\s+$/, "") + "\n\n" : "") + block;
  }
  if (next === existing) return "up-to-date";
  if (dry) return "would update";
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, next);
  return "updated";
}

function parseArgs(argv) {
  const out = { skill: [], agent: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--all") out.all = true;
    else if (a === "--list") out.list = true;
    else if (a === "--force") out.force = true;
    else if (a === "--dry-run") out.dry = true;
    else if (a === "--uninstall") out.uninstall = true;
    else if (a === "--help" || a === "-h") out.help = true;
    else if (a === "--skill" || a === "--agent") {
      const value = argv[++i];
      if (value === undefined || value.startsWith("--")) {
        return { error: `${a} needs a value` };
      }
      if (a === "--skill") out.skill.push(value);
      else out.agent.push(value.toLowerCase());
    }
    else if (a.startsWith("--skill=")) out.skill.push(a.split("=")[1]);
    else if (a.startsWith("--agent=")) out.agent.push(a.split("=")[1].toLowerCase());
    else return { error: `unknown argument: ${a}` };
  }
  return out;
}

const USAGE = `agent-skills — install portable agent skills

Usage:
  npx agent-skills-kit --all               install every skill for every agent it declares
  npx agent-skills-kit --skill review-pr   install one skill
  npx agent-skills-kit --agent claude      restrict to one agent (repeatable)
  npx agent-skills-kit --list              show skills and target directories
  npx agent-skills-kit --all --dry-run     show what would happen
  npx agent-skills-kit --all --uninstall   remove installed skills

Flags:
  --force      overwrite an existing install
  --dry-run    print actions without touching the filesystem
`;

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.error) {
    console.error(args.error + "\n\n" + USAGE);
    return 1;
  }
  if (args.help) {
    console.log(USAGE);
    return 0;
  }

  const skills = discover(args.skill.length ? new Set(args.skill) : null);
  if (!skills.length) {
    if (args.skill.length) {
      const known = discover(null).map((s) => s.name);
      console.error(`no such skill: ${args.skill.join(", ")}`);
      console.error(`available: ${known.join(", ")}`);
    } else {
      console.error("no skills found in this package");
    }
    return 1;
  }
  const broken = skills.filter((s) => s.missing);
  if (broken.length) {
    for (const s of broken) console.error(`${s.name}: missing SKILL.md`);
    return 1;
  }

  if (args.list) {
    console.log("targets:");
    for (const [agent, p] of Object.entries(AGENT_TARGETS)) {
      const present = fs.existsSync(expand(p)) ? "present" : "missing";
      console.log(`  ${agent.padEnd(9)} ${p}  (${present})`);
    }
    console.log("\nskills:");
    for (const s of skills) {
      console.log(`  ${s.name.padEnd(24)} agents=${targetsFor(s).join(",")}`);
    }
    return 0;
  }

  if (!args.all && !args.agent.length && !args.skill.length) {
    console.error("pass --all, --agent, --skill, or --list\n\n" + USAGE);
    return 1;
  }

  const wanted = args.agent.length ? new Set(args.agent) : null;
  if (wanted) {
    const unknown = [...wanted].filter((a) => !(a in AGENT_TARGETS));
    if (unknown.length) {
      console.error(`unknown agent(s): ${unknown.join(", ")}`);
      console.error(`known: ${Object.keys(AGENT_TARGETS).join(", ")}`);
      return 1;
    }
  }

  // npx installs are copies, so --force is implied on reinstall unless dry.
  const force = args.force || !args.uninstall;
  const touched = {};
  for (const s of skills) {
    for (const agent of targetsFor(s)) {
      if (wanted && !wanted.has(agent)) continue;
      const dest = path.join(expand(AGENT_TARGETS[agent]), s.name);
      let status;
      if (args.uninstall) {
        status = uninstall(dest, { dry: args.dry });
      } else {
        status = install(s, dest, { force, dry: args.dry });
        (touched[agent] = touched[agent] || []).push(s);
      }
      console.log(`${agent.padEnd(9)} ${s.name.padEnd(24)} ${status}`);
    }
  }

  for (const [agent, installed] of Object.entries(touched)) {
    if (agent in POINTER_FILES) {
      const status = writePointer(agent, installed, { dry: args.dry });
      console.log(`${agent.padEnd(9)} ${"(pointer index)".padEnd(24)} ${status}`);
    }
  }
  return 0;
}

process.exit(main());
