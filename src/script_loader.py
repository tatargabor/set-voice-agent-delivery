"""Load YAML call scripts into CallContext."""

from pathlib import Path
import yaml
from .agent import CallContext


SCRIPTS_DIR = Path(__file__).parent.parent / "call_scripts"


def load_script(
    script_name: str,
    variables: dict[str, str],
) -> CallContext:
    """Load a call script and substitute variables.

    Args:
        script_name: Script name (without .yaml extension).
        variables: Variable values to substitute (customer_name, company_name, etc.).

    Returns:
        CallContext ready for use.

    Raises:
        FileNotFoundError: If the script file doesn't exist.
        ValueError: If required fields or variables are missing.
    """
    script_path = SCRIPTS_DIR / f"{script_name}.yaml"
    if not script_path.exists():
        raise FileNotFoundError(f"Call script not found: {script_path}")

    with open(script_path) as f:
        script = yaml.safe_load(f)

    # Validate required sections
    if "context" not in script:
        raise ValueError(f"Script '{script_name}' missing required field: context")
    if "purpose" not in script["context"]:
        raise ValueError(f"Script '{script_name}' missing required field: context.purpose")

    # Check required variables
    required_vars = script["context"].get("variables", [])
    missing_vars = [v for v in required_vars if v not in variables]
    if missing_vars:
        raise ValueError(f"Missing required variables: {', '.join(missing_vars)}")

    # Build CallContext
    purpose = script["context"]["purpose"]
    for key, value in variables.items():
        purpose = purpose.replace(f"{{{key}}}", value)

    return CallContext(
        customer_name=variables.get("customer_name", ""),
        company_name=variables.get("company_name", ""),
        purpose=purpose,
        website_url=variables.get("website_url"),
    )
