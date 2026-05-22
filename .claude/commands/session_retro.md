---
description: Generate a technical retrospective of the current session — decisions, affected files, tradeoffs, and final state.
---

# Session technical retrospective

Analyze this complete session and generate a reverse plan of what was implemented.

Do not invent information. Extract only what appears in the conversation and in tool results executed during this session.

**LANGUAGE: Respond in the same language the user has been speaking in this session.**

**IMPORTANT: The complete output must be a markdown code block.** Wrap the entire response in a single triple-backtick block with type `markdown`. Include nothing outside the block.

## Output structure

### Title
One line. What was implemented or resolved.

### Context
- Initial objective stated by the user.
- How it evolved (if there were pivots, redefinitions, or discoveries that changed scope).

### Decision timeline
Chronological list. For each decision:
- **Decision**: what was chosen (or discarded).
- **Reason**: why (technical constraint, user preference, finding in code).
- **Discarded alternative** (if applicable).

### Affected files and modules
Table or list with:
- File path.
- Change type: created / modified / deleted / read-no-change.
- One-line description of what changed.

### Implemented changes
Technical summary per file or feature. No paraphrasing — extract actual changes observed in diffs or edits from the session.

### Validations executed
- Tests run, lint/build commands, manual inspections, UI previews.
- Result (passed / failed / not executed).

### Risks, tradeoffs, and out-of-scope items
- What was left undone and why.
- Consciously introduced technical debt.
- Uncovered edge cases.
- Unverified external dependencies or assumptions.

### Final state
Before writing this section, run `git branch --show-current` to get the actual current branch. Do not rely on conversation context for this.
- Current branch and name.
- Commits made (hash + message if they appear in session).
- Whether pushed or local only.
- Build/deploy status if executed.

### Pending items and recommendations
Prioritized list of concrete next steps. No vagueness — specific actions with file or module where applicable.
