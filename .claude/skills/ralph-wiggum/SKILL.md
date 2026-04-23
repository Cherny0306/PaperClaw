# Ralph Wiggum Plugin

## Name
ralph-wiggum

## Description
Ralph Wiggum iterative development loop technique - run Claude in continuous self-improvement cycles with completion detection.

## triggers
- /ralph-loop
- /cancel-ralph

## Commands

### ralph-loop
Start a Ralph Wiggum loop in the current session.

```
/ralph-loop "Your task description" --max-iterations 20 --completion-promise "TASK COMPLETE"
```

### cancel-ralph
Cancel an active Ralph loop.

```
/cancel-ralph
```

## Implementation
This skill manages the Ralph Wiggum iterative development technique.

The core loop:
```bash
while :; do
  cat PROMPT.md | claude-code --continue
done
```

**Key concepts:**
- Same prompt fed repeatedly to Claude
- Claude sees its own previous work in files
- Stops when `<promise>TASK COMPLETE</promise>` detected or max iterations reached

**Completion signal:**
Claude must output `<promise>YOUR_MESSAGE</promise>` to signal completion.

**Stop hook configuration:**
The Claude Code stop hook should be configured to intercept and re-feed the prompt.