# Project rules

These rules apply to all agent work in this public BambuStudio + PrintFins repository.

1. **Git safety:** Never directly modify `master` or `integration`. Use dedicated feature, fix, maintenance, or update branches. Never merge, force-push, release, or discard work without authorization. Maintainer approval is required before merging into protected branches.

2. **Stable baseline:** `integration` represents the last approved working development state. Preserve rollback through Git history, tags, and releases.

3. **Code quality:** Prefer minimal, focused, maintainable changes. Follow existing conventions. Avoid unnecessary abstractions, dependencies, refactoring, and AI-generated boilerplate.

4. **Upstream compatibility:** Minimize divergence from `bambulab/BambuStudio` and `gittrahan/support-fins`. Keep the integration modular without prematurely committing to a specific architecture. Handle upstream updates separately and verify compatibility.

5. **Verification:** Preserve existing functionality. Perform relevant tests, distinguish verified results from assumptions, and never claim unexecuted tests passed.

6. **Community:** Keep changes understandable, reviewable, and appropriately documented. Respect upstream licenses and attribution.

7. **Agent discipline:** Stay within the requested scope. Do not perform unrelated changes. Report modifications, tests, and limitations concisely.
