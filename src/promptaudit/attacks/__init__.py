from pathlib import Path
import yaml

from promptaudit.models import AttackScenario, AttackVector

_ATTACK_DIR = Path(__file__).parent


def load_templates(vector: AttackVector) -> list[AttackScenario]:
    yaml_file = _ATTACK_DIR / f"{vector.value}.yaml"
    if not yaml_file.exists():
        return []
    data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    scenarios = []
    for item in data.get("scenarios", []):
        scenarios.append(
            AttackScenario(
                id=item["id"],
                vector=vector,
                payload=item["payload"],
                description=item["description"],
                owasp_ref=item["owasp_ref"],
            )
        )
    return scenarios
