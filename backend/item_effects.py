from typing import Protocol, Any
from api_wrapper import ItemTarget
import os
import yaml

class MonsterContext(Protocol):
    health: int

def direct_damage(target: MonsterContext, amount: int) -> None:
    target.health -= amount

    
EFFECT_REGISTRY = {
    "DIRECT_DAMAGE": (ItemTarget.MONSTER, direct_damage),
}

ITEM_REGISTRY = {}

MONSTER_REGISTRY = {}

library_path = os.path.join(os.path.dirname(__file__), 'library.yaml')
with open(library_path, 'r') as file:
    try:
        data: dict[str, dict[Any]] = yaml.load(file, yaml.Loader)
        for name, item_data in data["items"].items():
            ITEM_REGISTRY[name] = item_data
        for name, monster_data in data["monsters"].items():
            MONSTER_REGISTRY[name] = monster_data

    except yaml.YAMLError as exc:
        print(exc)

