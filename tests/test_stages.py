import pytest

from app.models import StageName as S
from app.services.stages import InvalidTransition, validate_transition


@pytest.mark.parametrize(
    "current,new",
    [
        (S.NEW, S.PHONE_SCREEN_SCHEDULED),
        (S.PHONE_SCREEN_SCHEDULED, S.INTERVIEW_SCHEDULED),
        (S.INTERVIEW_SCHEDULED, S.HIRED),
        (S.NEW, S.INTERVIEW_SCHEDULED),  # skipping ahead is allowed
        (S.NEW, S.REJECTED),
        (S.INTERVIEW_SCHEDULED, S.REJECTED),
    ],
)
def test_valid_transitions(current, new):
    validate_transition(current, new)


@pytest.mark.parametrize(
    "current,new",
    [
        (S.PHONE_SCREEN_SCHEDULED, S.NEW),  # backwards
        (S.INTERVIEW_SCHEDULED, S.PHONE_SCREEN_SCHEDULED),
        (S.NEW, S.NEW),  # same stage
        (S.HIRED, S.REJECTED),  # terminal
        (S.REJECTED, S.NEW),
        (S.HIRED, S.HIRED),
    ],
)
def test_invalid_transitions(current, new):
    with pytest.raises(InvalidTransition):
        validate_transition(current, new)
