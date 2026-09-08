module.exports = {
  branches: ["master"],
  tagFormat: "v${version}",
  plugins: [
    ["@semantic-release/commit-analyzer", { preset: "conventionalcommits" }],
    ["@semantic-release/release-notes-generator", {
      preset: "conventionalcommits",
      presetConfig: {
        types: [
          { type: "feat", section: "New features" },
          { type: "fix", section: "Fixes" },
          { type: "perf", section: "Performance improvements" },
          { type: "docs", section: "Documentation" },
        ],
      },
      writerOpts: {
        // Include the commit body so features explain behavior and usage.
        commitPartial: `#### {{#if scope}}{{scope}}: {{/if}}{{subject}}

{{#if body}}{{{body}}}

{{/if}}[Commit {{shortHash}}]({{@root.host}}/{{@root.owner}}/{{@root.repository}}/commit/{{hash}})
{{#each references}}
{{#if issue}} · {{prefix}}{{issue}}{{/if}}
{{/each}}

`,
      },
    }],
    ["@semantic-release/github", {
      successComment: false,
      failComment: false,
      failTitle: false,
      releasedLabels: false,
    }],
  ],
};
