from app.config import settings


def should_early_break(
    scores: list[int | float],
    window: int | None = None,
    min_relative_gain: float | None = None,
) -> bool:
    w = window if window is not None else settings.ats_stagnation_window
    g = min_relative_gain if min_relative_gain is not None else settings.ats_min_gain
    if len(scores) <= w:
        return False
    recent = scores[-(w + 1) :]
    for i in range(1, len(recent)):
        prev = recent[i - 1]
        cur = recent[i]
        if prev == 0:
            gain = 0.0 if cur == 0 else float("inf")
        else:
            gain = (cur - prev) / prev
        if gain >= g:
            return False
    return True
