# Gameplay Behavior Change Checklist

Use this checklist for every change that affects gameplay behavior. Link the relevant tests, fixtures, validation changes, and migration notes in the pull request. Mark an item not applicable only with a short explanation.

- [ ] Swift unit test added or updated.
- [ ] Python parity test added or updated.
- [ ] Shared runtime-parity fixture added or updated.
- [ ] Generator validator updated.
- [ ] Editor playtest updated.
- [ ] JSON backward and forward compatibility considered.
- [ ] Production-level migration impact documented.

Before merging, run the repository's combined verification command described in the root `README.md` and record the result in the pull request.
