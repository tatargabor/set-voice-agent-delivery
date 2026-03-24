"""Call state machine for voice agent pipeline."""

import enum
import time
import structlog

log = structlog.get_logger()


class CallState(enum.Enum):
    GREETING = "greeting"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ENDED = "ended"


# Valid state transitions: from_state -> set of allowed to_states
VALID_TRANSITIONS = {
    CallState.GREETING: {CallState.LISTENING, CallState.ENDED},
    CallState.LISTENING: {CallState.PROCESSING, CallState.ENDED},
    CallState.PROCESSING: {CallState.SPEAKING, CallState.ENDED},
    CallState.SPEAKING: {CallState.LISTENING, CallState.ENDED},
    CallState.ENDED: set(),
}


class CallStateMachine:
    """Manages call state transitions with logging and validation."""

    def __init__(self):
        self._state = CallState.GREETING
        self._transition_count = 0

    @property
    def state(self) -> CallState:
        return self._state

    @property
    def is_ended(self) -> bool:
        return self._state == CallState.ENDED

    def transition(self, new_state: CallState, reason: str = "") -> None:
        """Transition to a new state with validation and logging.

        Raises:
            ValueError: If the transition is not valid.
        """
        old_state = self._state

        if new_state not in VALID_TRANSITIONS.get(old_state, set()):
            raise ValueError(
                f"Invalid transition: {old_state.value} → {new_state.value}"
            )

        self._state = new_state
        self._transition_count += 1

        log.info(
            "state_transition",
            previous=old_state.value,
            new=new_state.value,
            reason=reason,
            transition_count=self._transition_count,
            timestamp=time.time(),
        )
