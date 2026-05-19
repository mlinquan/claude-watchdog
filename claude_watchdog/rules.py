# Rule: list of dialog patterns with match regex and keystroke sequence
# Each entry: (name, regex, keys, description)

RULES = [
    (
        "proceed",
        r"Do you want to proceed",
        ["1", "Enter"],
        "Tool confirmation dialog — select option 1 (Yes)",
    ),
    (
        "edit_or_overwrite",
        r"Do you want to (make this edit|overwrite)",
        ["Down", "Enter"],
        "File edit/overwrite dialog — 'Allow all this session'",
    ),
    (
        "accept_edits",
        r"accept edits on",
        ["Enter"],
        "Diff review prompt — accept pending diffs",
    ),
    (
        "custom_api_key",
        r"Detected a custom API key",
        ["Up", "Enter"],
        "API key detection — confirm custom key (select Yes)",
    ),
    (
        "interrupted",
        r"Interrupted",
        ["2", "Enter"],
        "Interrupted dialog — select option 2 (Bypass/Continue)",
    ),
    (
        "rate_claude",
        r"(Rate this response|How was this)",
        ["Escape"],
        "Rating/evaluation dialog — dismiss (press Escape)",
    ),
]
