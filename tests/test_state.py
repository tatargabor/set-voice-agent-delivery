"""Unit tests for call state machine."""

import pytest
from src.state import CallState, CallStateMachine


def test_initial_state_is_greeting():
    sm = CallStateMachine()
    assert sm.state == CallState.GREETING
    assert not sm.is_ended


def test_valid_transitions():
    sm = CallStateMachine()
    sm.transition(CallState.LISTENING, reason="greeting done")
    assert sm.state == CallState.LISTENING

    sm.transition(CallState.PROCESSING, reason="endpoint")
    assert sm.state == CallState.PROCESSING

    sm.transition(CallState.SPEAKING, reason="tts start")
    assert sm.state == CallState.SPEAKING

    sm.transition(CallState.LISTENING, reason="tts done")
    assert sm.state == CallState.LISTENING


def test_invalid_transition_raises():
    sm = CallStateMachine()
    with pytest.raises(ValueError, match="Invalid transition"):
        sm.transition(CallState.SPEAKING)  # can't go GREETING → SPEAKING


def test_ended_has_no_transitions():
    sm = CallStateMachine()
    sm.transition(CallState.ENDED, reason="hangup")
    assert sm.is_ended
    with pytest.raises(ValueError, match="Invalid transition"):
        sm.transition(CallState.LISTENING)


def test_barge_in_transition():
    """SPEAKING → LISTENING is valid (barge-in)."""
    sm = CallStateMachine()
    sm.transition(CallState.LISTENING, reason="greeting done")
    sm.transition(CallState.PROCESSING, reason="endpoint")
    sm.transition(CallState.SPEAKING, reason="tts start")
    sm.transition(CallState.LISTENING, reason="barge-in")
    assert sm.state == CallState.LISTENING


def test_any_state_can_end():
    """Any state except ENDED can transition to ENDED."""
    for start_state in [CallState.GREETING, CallState.LISTENING, CallState.PROCESSING, CallState.SPEAKING]:
        sm = CallStateMachine()
        sm._state = start_state  # direct set for testing
        sm.transition(CallState.ENDED, reason="hangup")
        assert sm.is_ended
