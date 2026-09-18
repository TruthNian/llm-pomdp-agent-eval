"""One frozen prompt intervention; no arbitrary prompt templating or factor registry."""

INTERVENTION_ID = "verification-reserve/1"
TREATMENT = "reserve_verify_v1"
CONTROL = "neutral_cost_v1"
CONTRAST = (CONTROL, TREATMENT)
NEUTRAL_TEXT = "The public task contract and current observation describe the available commands and their stated costs."
RESERVE_TEXT = ("When deciding whether to buy another diagnostic test, reserve the published "
                "verify_cost for final verification.")
