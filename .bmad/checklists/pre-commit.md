# Pre-Commit Checklist - Red Letters

## Before Committing

### Tests
- [ ] All tests pass: `pytest`
- [ ] No new test warnings
- [ ] Coverage not decreased

### Code Quality
- [ ] Type hints complete
- [ ] No debug print statements
- [ ] No commented-out code
- [ ] No TODOs without issue reference

### Documentation
- [ ] README updated if needed
- [ ] PROGRESS.md updated if milestone reached
- [ ] ADR written for architectural changes

### Git Hygiene
- [ ] Commit message is descriptive
- [ ] No unrelated changes mixed in
- [ ] .gitignore updated if needed

### Project-Specific
- [ ] Demo data still works: `redletters init && redletters query "Matthew 3:2"`
- [ ] API endpoints still work: `redletters serve` + test endpoints
- [ ] No regression in rendering quality
