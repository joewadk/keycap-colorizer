import assert from "node:assert/strict";
import { test } from "node:test";
import { analyzeCommits } from "@semantic-release/commit-analyzer";
import { generateNotes } from "@semantic-release/release-notes-generator";
import config from "../release.config.cjs";

test("renders first-release notes with the configured preset and writer", async () => {
  const notes = await generateNotes(config.plugins[1][1], {
    cwd: process.cwd(),
    env: {},
    options: { repositoryUrl: "https://github.com/joewadk/keycap-colorizer.git" },
    commits: [
      { hash: "a".repeat(40), message: "feat: add layout switching\n\nCompare color combinations across 65%, 75%, and TKL boards.\n\n- Choose a board from the layout menu.\n- Preview your selected palette before buying keycaps." },
      { hash: "b".repeat(40), message: "fix: correct keycap colors" },
      { hash: "c".repeat(40), message: "feat!: change configuration format\n\nBREAKING CHANGE: saved layouts use stable key IDs" },
    ],
    lastRelease: {},
    nextRelease: { version: "1.0.0", gitTag: "v1.0.0", gitHead: "c".repeat(40) },
    logger: { log() {} },
  });
  assert.match(notes, /1\.0\.0/);
  assert.match(notes, /add layout switching/);
  assert.match(notes, /correct keycap colors/);
  assert.match(notes, /saved layouts use stable key IDs/);
  assert.match(notes, /### New features/);
  assert.match(notes, /Compare color combinations across 65%, 75%, and TKL boards\./);
  assert.match(notes, /- Choose a board from the layout menu\./);
  assert.match(notes, /### Fixes/);
  assert.match(notes, /github\.com\/joewadk\/keycap-colorizer\/commit\/a{40}/);
});

for (const [message, expected] of [
  ["fix: correct keycap colors", "patch"],
  ["feat: add layout switching", "minor"],
  ["feat!: change configuration format", "major"],
  ["docs: simplify setup instructions", null],
]) {
  test(`${message} => ${expected ?? "no release"}`, async () => {
    const result = await analyzeCommits(config.plugins[0][1], {
      cwd: process.cwd(),
      commits: [{ hash: "test", message }],
      logger: { log() {} },
    });
    assert.equal(result, expected);
  });
}
