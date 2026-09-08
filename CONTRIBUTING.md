# Commit messages and releases

Use Conventional Commits so releases describe what changed:

- `fix: correct keycap colors` creates a patch release.
- `feat: add layout switching` creates a minor release.
- `feat!: change configuration format` creates a major release. Explain the migration in the commit body.
- `docs: simplify setup instructions`, `test: cover selection`, and `chore: update tooling` do not trigger releases on their own.

For squash merges, use this format in the PR title because it becomes the commit message on main.

After a push to `main`, GitHub Actions runs the backend tests, frontend tests, and frontend build. If those pass and the commits warrant a release, semantic-release creates a `vX.Y.Z` tag and a GitHub Release with generated notes. The first release is normally `1.0.0`.

Releases do not publish to npm or PyPI, deploy the app, or commit version bumps back to the repository. Git tags are the application release version; the existing package version fields remain development metadata.

The workflow uses GitHub's built-in `GITHUB_TOKEN`; no personal access token is needed. Repository or organization rules must permit tag creation and GitHub Releases.

To preview release analysis in a checkout with an `origin` remote, full history, and appropriate GitHub credentials:

```bash
npm ci
npm run release:dry-run
```

Run these commands from `frontend`. Release tooling shares its package manifest, lockfile, and `node_modules` with the frontend. Follow the [semantic-release documentation](https://semantic-release.gitbook.io/semantic-release/recipes/ci-configurations/github-actions) for CI authentication details.
