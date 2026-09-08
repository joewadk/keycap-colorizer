import assert from "node:assert/strict";
import { test } from "node:test";
import { analyzeCommits } from "@semantic-release/commit-analyzer";
import config from "../release.config.cjs";

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
