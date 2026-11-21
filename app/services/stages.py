from app.models import StageName

# Linear pipeline. REJECTED is reachable from any non-terminal stage.
PIPELINE = [
    StageName.NEW,
    StageName.PHONE_SCREEN_SCHEDULED,
    StageName.INTERVIEW_SCHEDULED,
    StageName.HIRED,
]
TERMINAL = {StageName.HIRED, StageName.REJECTED}


class InvalidTransition(ValueError):
    pass


def validate_transition(current: StageName, new: StageName) -> None:
    """Raise InvalidTransition unless moving current -> new is a forward move."""
    if current in TERMINAL:
        raise InvalidTransition(f"'{current.value}' is final; the stage cannot change")
    if new == current:
        raise InvalidTransition(f"Application is already in '{current.value}'")
    if new == StageName.REJECTED:
        return
    if PIPELINE.index(new) < PIPELINE.index(current):
        raise InvalidTransition(f"Cannot move backwards from '{current.value}' to '{new.value}'")
