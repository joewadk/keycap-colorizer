# Commit messages and releases

Use Conventional Commits so releases describe what changed:

- `fix: correct keycap colors` creates a patch release.
- `feat: add layout switching` creates a minor release.
- `feat!: change configuration format` creates a major release. Explain the migration in the commit body.
- `docs: simplify setup instructions`, `test: cover selection`, and `chore: update tooling` do not trigger releases on their own.

For squash merges, use this format in the PR title because it becomes the commit message on main.

## Writing useful feature notes

Release notes include the commit subject and body, grouped into New features, Fixes, Performance improvements, and Documentation. Explain what the user can do, why it helps, and how to try it. For example, a future layout-switching feature could use:

```text
feat(preview): switch between keyboard layouts

Compare color combinations across 65%, 75%, and TKL boards.

- Choose a board from the layout menu.
- Preview your selected palette before buying keycaps.
```

For a squash merge, keep this description in the final squash commit body. A PR description alone is not used unless it becomes part of that commit. Only describe implemented behavior; the generator formats your text and does not inspect code or invent feature descriptions.

Put migration requirements in a `BREAKING CHANGE:` footer so they appear in the dedicated breaking-changes section. Documentation commits appear in notes when another commit triggers a release; they still do not create releases by themselves.

After a push to `main`, GitHub Actions runs the backend tests, frontend tests, and frontend build. If those pass and the commits warrant a release, semantic-release creates a `vX.Y.Z` tag and a GitHub Release with generated notes. The first release is normally `1.0.0`.

Releases do not publish to npm or PyPI, deploy the app, or commit version bumps back to the repository. Git tags are the application release version; the existing package version fields remain development metadata.

The workflow uses GitHub's built-in `GITHUB_TOKEN`; no personal access token is needed. Repository or organization rules must permit tag creation and GitHub Releases.

To preview release analysis in a checkout with an `origin` remote, full history, and appropriate GitHub credentials:

```bash
npm ci
npm run release:dry-run
```

Run these commands from `frontend`. Release tooling shares its package manifest, lockfile, and `node_modules` with the frontend. Follow the [semantic-release documentation](https://semantic-release.gitbook.io/semantic-release/recipes/ci-configurations/github-actions) for CI authentication details.
