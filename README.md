# IsoRPG Engine

A simple isometric RPG engine built with Python and PyRay.

## Features

*   **Isometric World:** Explorable world with different biomes (temperate, desert) and a cave system.
*   **Player and NPCs:** A player character and simple NPCs with dialogue.
*   **Object Interaction:** Interact with objects like ladders to move between maps.
*   **Point-and-Click Movement:** Move the player by clicking on the map.
*   **Character Animation:** Simple walking animation for the player.
*   **Dynamic Object Generation:** Trees, rocks, and chests are procedurally placed on the map.

## Debugging Tools

### Bounding Box Overlay

To help with debugging object placement and collision, a bounding box overlay can be toggled on and off.

*   **Toggle Key:** Press the `B` key to show or hide the bounding box overlay.
*   **Collision Indication:** The bounding boxes will be drawn in green. If the player's bounding box overlaps with another object's bounding box, both boxes will turn red.

### Un-blocking Exits

The map generation logic has been updated to prevent objects from being placed on top of important objects like ladders, ensuring that all exits are always accessible.
