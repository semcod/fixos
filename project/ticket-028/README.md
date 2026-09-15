# Ticket 028: Install git in Docker test images for managed governance

- **ID**: ticket-028
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-15

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the human requested continuation of the
refactoring and publication work. The Multi-System Docker checks for the
managed governance plugin fail in the Fedora, Ubuntu and Debian images because
those images do not install the `git` executable, although the plugin invokes
Git during test collection. Add the missing tool to exactly those three test
images so the adopted governance contract can run consistently.

The scope is limited to the package-install layers of
`docker/fedora/Dockerfile`, `docker/ubuntu/Dockerfile` and
`docker/debian/Dockerfile`. Arch, Alpine, the Fedora base image and workflow
logic are not part of this repair because their current jobs either already
contain Git or are not implicated by the observed failure.

## Acceptance criteria

- [x] AC-01: The exact failing images and workflow consumers are identified;
  the request to continue records `SESSION_EXECUTION_AUTHORIZATION`.
- [x] AC-02: Fedora, Ubuntu and Debian test images install `git` in their
  image layer before the FixOS package is installed; no unrelated image or
  workflow changes are made. Local builds of all three candidate images
  completed successfully.
- [ ] AC-03: Governance and Python checks pass locally, and the targeted
  Docker image checks confirm that `git --version` is available in all three
  images. The image builds are complete; runtime checks and the full suite are
  the remaining evidence.
- [ ] AC-04: The exact material HEAD passes hosted checks, OneDev validation
  and the protected Validator merge flow.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
