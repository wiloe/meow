import pyray as rl
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

@dataclass
class QuestReward:
    xp: int = 0
    gold: int = 0
    items: List[Dict[str, Any]] = field(default_factory=list)

    @staticmethod
    def from_dict(data):
        return QuestReward(
            xp=data.get('xp', 0),
            gold=data.get('gold', 0),
            items=data.get('items', [])
        )
    
    def to_dict(self):
        return asdict(self)

@dataclass
class Quest:
    title: str
    description: str
    requirements: Dict[str, int]
    reward: QuestReward
    completed: bool = False
    id: str = ""

    @staticmethod
    def from_dict(data):
        # Handle legacy format (simple dicts on NPCs)
        if 'req' in data:
            reqs = {data['req']: data.get('count', 1)}
            reward_data = data.get('reward', {})
            items = []
            if 'item' in reward_data:
                items.append({'type': reward_data['item'], 'count': reward_data.get('count', 1)})
            
            reward = QuestReward(
                xp=reward_data.get('xp', 0),
                gold=reward_data.get('gold', 0),
                items=items
            )
            return Quest(
                title="Quest",
                description=data.get('desc', ''),
                requirements=reqs,
                reward=reward,
                completed=data.get('completed', False),
                id=str(id(data))
            )
        
        return Quest(
            title=data.get('title', 'Quest'),
            description=data.get('description', ''),
            requirements=data.get('requirements', {}),
            reward=QuestReward.from_dict(data.get('reward', {})),
            completed=data.get('completed', False),
            id=data.get('id', '')
        )

    def to_dict(self):
        return {
            'title': self.title,
            'description': self.description,
            'requirements': self.requirements,
            'reward': self.reward.to_dict(),
            'completed': self.completed,
            'id': self.id
        }

class QuestSystem:
    def __init__(self, game):
        self.game = game

    def check_requirements(self, quest: Quest) -> bool:
        inv = self.game.player['inventory']
        for item_type, count in quest.requirements.items():
            found = 0
            for slot in inv:
                if slot and slot['type'] == item_type:
                    found += slot['count']
            if found < count:
                return False
        return True

    def complete_quest(self, quest: Quest):
        if not self.check_requirements(quest):
            return False
            
        # Consume items
        inv = self.game.player['inventory']
        for item_type, count in quest.requirements.items():
            remaining = count
            for i, slot in enumerate(inv):
                if slot and slot['type'] == item_type:
                    take = min(remaining, slot['count'])
                    slot['count'] -= take
                    remaining -= take
                    if slot['count'] <= 0:
                        inv[i] = None
                    if remaining <= 0:
                        break
        
        quest.completed = True
        
        # Grant Rewards
        if quest.reward.xp > 0:
            self.game.gain_xp(quest.reward.xp)
        if quest.reward.gold > 0:
            self.game.player['stats']['gold'] = self.game.player['stats'].get('gold', 0) + quest.reward.gold
        for item in quest.reward.items:
            self.game.add_inventory_item(item['type'], item.get('count', 1))
            
        self.game.chat.log(f"Quest Completed! (+{quest.reward.xp} XP)", rl.GOLD)
        
        # Add to player completed quests log
        self.game.player['quests'].append(quest.to_dict())
        
        return True