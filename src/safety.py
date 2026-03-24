"""Call safety checks — DNC list and legal hours enforcement."""

import datetime
from pathlib import Path
import structlog

log = structlog.get_logger()

DATA_DIR = Path(__file__).parent.parent / "data"
DNC_FILE = DATA_DIR / "dnc.txt"


class CallSafety:
    """Pre-call safety gate: DNC list + legal hours."""

    def __init__(self, dnc_path: Path = DNC_FILE):
        self._dnc_path = dnc_path

    def _load_dnc(self) -> set[str]:
        if not self._dnc_path.exists():
            return set()
        return {
            line.strip()
            for line in self._dnc_path.read_text().splitlines()
            if line.strip()
        }

    def check_dnc(self, phone: str) -> bool:
        """Check if phone number is on the DNC list.

        Returns:
            True if the number is blocked (on DNC list).
        """
        dnc = self._load_dnc()
        blocked = phone in dnc
        if blocked:
            log.warning("dnc_blocked", phone=phone)
        return blocked

    def add_to_dnc(self, phone: str) -> None:
        """Add a phone number to the DNC list."""
        self._dnc_path.parent.mkdir(parents=True, exist_ok=True)
        dnc = self._load_dnc()
        if phone not in dnc:
            with open(self._dnc_path, "a") as f:
                f.write(f"{phone}\n")
            log.info("dnc_added", phone=phone)

    def check_legal_hours(self, now: datetime.datetime | None = None) -> bool:
        """Check if current time is within legal calling hours (08:00-20:00).

        Returns:
            True if outside legal hours (blocked).
        """
        if now is None:
            now = datetime.datetime.now()
        blocked = now.hour < 8 or now.hour >= 20
        if blocked:
            log.warning("legal_hours_blocked", hour=now.hour)
        return blocked

    def pre_call_check(self, phone: str) -> None:
        """Run all safety checks. Raises ValueError if any check fails."""
        errors = []
        if self.check_dnc(phone):
            errors.append(f"Phone {phone} is on the Do Not Call list")
        if self.check_legal_hours():
            errors.append("Outside legal calling hours (08:00-20:00)")
        if errors:
            raise ValueError("; ".join(errors))
