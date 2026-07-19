import random
from typing import Dict


class ABTestingService:
    def __init__(self):
        # Configuration for disease model AB tests.
        # e.g., "diabetes": {"Production": 90, "Staging": 10}
        self.configs = {}

    def set_config(self, disease: str, config: Dict[str, int]):
        """Set the traffic split, e.g., {'Production': 80, 'Staging': 20}."""
        total = sum(config.values())
        if total != 100:
            raise ValueError("AB Test config values must sum to 100")
        self.configs[disease] = config

    def assign_group(self, disease: str) -> str:
        """Assign a request to a model group based on traffic split."""
        if disease not in self.configs:
            return "Production"

        config = self.configs[disease]
        rand = random.uniform(0, 100)

        cumulative = 0
        for group, percentage in config.items():
            cumulative += percentage
            if rand <= cumulative:
                return group

        return "Production"


ab_testing_service = ABTestingService()
