from typing import Protocol
from api_wrapper import ItemTarget

class MonsterContext(Protocol):
    health: int

def direct_damage(target: MonsterContext, amount: int) -> None:
    target.health -= amount
    
    
EFFECT_REGISTRY = {
    "DIRECT_DAMAGE": (ItemTarget.MONSTER, direct_damage),
}
