* fix the ui layout in the pause menu.
* add recipes.json
* &nbsp;create a chat dilogue box let this get debug msg as well it located at the bottom right hand corner it should have a transparency of about 75% Then add all active dialogue output to the new chat in the chat should allow for interactive click icon for scripted dialogue options.
* create a debug system link it into and / commands to the dialogue box that can bring up help files.
* do something about image generation
* go through the code see if there is anything we can add to the ECS
* 

## Code Analysis (iso_rpg)
*   **Architecture**: The project uses a hybrid approach. It has an ECS (`ecs.py`, `systems.py`), but the main rendering and state management are still centralized in `IsoGame` (`protoiso.py`).
*   **Assets**: All textures are currently procedurally generated in `asset_loader.py`. This is good for prototyping but limits artistic control. Audio files are loaded directly in components, which can lead to resource duplication.
*   **Quest System**: `quest_system.py` contains logic for a "legacy format" (simple dicts), indicating a need to standardize on the new `Quest` class structure.
*   **AI**: `MobSystem` uses A* pathfinding but the movement logic (`d < 0.1`) can be jittery. It re-plans paths frequently (every 0.5-1.0s).