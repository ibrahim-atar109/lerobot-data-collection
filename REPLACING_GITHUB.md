# Replace the old GitHub main branch

This directory has its own Git repository and one root commit. The operational checkout at `S:/Dev/so-101/lerobot` is not modified. Do not run these replacement commands inside that operational checkout.

Review the README and files here first. Then, in Windows Anaconda Prompt:

```bat
cd /d S:\Dev\intelsys-repo\lerobot-data-collection
git log --oneline
git fetch origin
git push --force-with-lease origin main:main
```

`git log --oneline` should show only the new collection-package commit before fetching. Fetching downloads the current remote refs so force-with-lease can detect intervening remote changes. The push replaces remote main history with this package's one-commit history. It does not merge the old commits. Coordinate first if teammates have added work. If the lease is rejected, inspect the remote changes before retrying. Do not use plain --force.

The old GitHub repository showed two branches. After replacing main, open GitHub's branches page and delete any unneeded other branch that still points to the old LeRobot history. Preserve any actual teammate work first. Old commits may remain accessible through cached views or old commit URLs; this does not mean new main inherits them. GitHub's contributor display can take time to update. Old LFS uploads are not automatically purged by rewriting main.

Existing clones of the full repository should not pull/merge the new main. Team members should make a fresh clone of the collection repository and follow README.md. Keep an old clone if needed for backups or existing robot operation.
