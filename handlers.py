from datetime import datetime, timezone

import sheets
import state


def parse_command(text: str) -> tuple[str, str]:
    """Return (command, argument) from raw message text."""
    stripped = text.strip()
    lower = stripped.lower()
    if lower.startswith("start "):
        return "start", stripped[6:].strip()
    if lower == "start":
        return "start", ""
    if lower == "stop":
        return "stop", ""
    if lower == "status":
        return "status", ""
    if lower == "today":
        return "today", ""
    if lower == "cancel":
        return "cancel", ""
    return "unknown", stripped


def dispatch(command: str, argument: str, user_id: str) -> str:
    if command == "start":
        return handle_start(user_id, argument)
    if command == "stop":
        return handle_stop(user_id)
    if command == "status":
        return handle_status(user_id)
    if command == "today":
        return handle_today(user_id)
    if command == "cancel":
        return handle_cancel(user_id)
    return handle_unknown(argument)


def handle_start(user_id: str, task: str) -> str:
    if not task:
        return "Please provide a task name.\nUsage: start <task name>"

    active = state.get_active(user_id)
    if active:
        return (
            f"You already have an active task: '{active['task']}'\n"
            "Send 'stop' to finish it or 'cancel' to discard it."
        )

    now = datetime.now(timezone.utc)
    state.set_active(user_id, task, now)
    local_now = now.astimezone()
    return f"Started tracking: '{task}'\nStarted at: {local_now.strftime('%H:%M:%S')}"


def handle_stop(user_id: str) -> str:
    active = state.get_active(user_id)
    if not active:
        return "No active task. Send 'start <task>' to begin tracking."

    task = active["task"]
    start_time = datetime.fromisoformat(active["start_time"])
    end_time = datetime.now(timezone.utc)
    duration_min = round((end_time - start_time).total_seconds() / 60, 1)

    try:
        sheets.append_entry(user_id, task, start_time, end_time)
    except Exception as e:
        return (
            f"Failed to save to Google Sheets: {e}\n"
            "Your task is still active — fix the issue and try 'stop' again."
        )

    state.clear_active(user_id)

    local_start = start_time.astimezone()
    local_end = end_time.astimezone()
    return (
        f"Stopped: '{task}'\n"
        f"Start: {local_start.strftime('%H:%M:%S')}\n"
        f"End:   {local_end.strftime('%H:%M:%S')}\n"
        f"Duration: {duration_min} min\n"
        "Saved to Google Sheets."
    )


def handle_status(user_id: str) -> str:
    active = state.get_active(user_id)
    if not active:
        return "No active task. Send 'start <task>' to begin tracking."

    task = active["task"]
    start_time = datetime.fromisoformat(active["start_time"])
    now = datetime.now(timezone.utc)
    elapsed_min = round((now - start_time).total_seconds() / 60, 1)
    local_start = start_time.astimezone()
    return (
        f"Active task: '{task}'\n"
        f"Started at: {local_start.strftime('%H:%M:%S')}\n"
        f"Elapsed: {elapsed_min} min"
    )


def handle_today(user_id: str) -> str:
    try:
        entries = sheets.get_today_entries(user_id)
    except Exception as e:
        return f"Failed to fetch today's entries: {e}"

    if not entries:
        return "No entries recorded today."

    lines = ["Today's entries:"]
    total = 0.0
    for e in entries:
        lines.append(
            f"  {e['start_time']} – {e['end_time']}  {e['duration_min']} min  '{e['task']}'"
        )
        total += e["duration_min"]
    lines.append(f"Total: {round(total, 1)} min")
    return "\n".join(lines)


def handle_cancel(user_id: str) -> str:
    active = state.get_active(user_id)
    if not active:
        return "No active task to cancel."

    task = active["task"]
    state.clear_active(user_id)
    return f"Cancelled task '{task}' without saving."


def handle_unknown(text: str) -> str:
    return (
        "Available commands:\n"
        "  start <task> — begin tracking a task\n"
        "  stop         — finish and save current task\n"
        "  status       — show elapsed time for active task\n"
        "  today        — list today's completed entries\n"
        "  cancel       — discard active task without saving"
    )
