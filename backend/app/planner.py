import re
from typing import List
from backend.app.models import PlanStep, PlanState

def parse_plan_markdown(markdown_text: str) -> PlanState:
    """
    Parses Markdown numbered lists into structured PlanStep items.
    Example:
    1. *Add a new function `is_prime` in `math.py`.*
       - Description bullet point
    """
    lines = markdown_text.strip().splitlines()
    steps: List[PlanStep] = []

    current_id = None
    current_title = ""
    current_details = []

    step_regex = re.compile(r'^\s*(\d+)\.\s*(.*)')

    for line in lines:
        match = step_regex.match(line)
        if match:
            if current_id is not None:
                steps.append(PlanStep(
                    id=current_id,
                    title=current_title.strip("* "),
                    details="\n".join(current_details).strip()
                ))
            current_id = int(match.group(1))
            current_title = match.group(2).strip()
            current_details = []
        else:
            if current_id is not None:
                current_details.append(line)

    if current_id is not None:
        steps.append(PlanStep(
            id=current_id,
            title=current_title.strip("* "),
            details="\n".join(current_details).strip()
        ))

    first_incomplete = next((s.id for s in steps if not s.completed), None)
    return PlanState(
        raw_markdown=markdown_text,
        steps=steps,
        current_step_id=first_incomplete
    )
