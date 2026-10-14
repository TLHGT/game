"""Carga mapas desde maps/<id>.json y construye un GameMap.

Para que un tipo nuevo pueda colocarse desde JSON, regístralo en
INTERACTABLE_TYPES (interactuables) o en entities/props.py (decorado).
"""
import json
import os

import pygame

from entities.chest import Chest
from entities.door import Door, SecretDoor
from entities.adventure import JumpSpot, LeafWall
from entities.enemy import Enemy
from entities.hospital import Elevator, PackAPunch, PerkCode, PerkMachine
from entities.npc import NPC
from entities.props import Prop, Wall
from entities.secret_object import SecretObject
from entities.sign import Sign
from game import settings
from world.collision import CollisionGrid
from world.forest import generate_forest
from world.map import GameMap
from world.transition import HiddenArea, MapTransition, TriggerZone

INTERACTABLE_TYPES = {
    "npc": NPC,
    "chest": Chest,
    "door": Door,
    "secret_door": SecretDoor,
    "sign": Sign,
    "secret_object": SecretObject,
    "enemy": Enemy,
    "leaf_wall": LeafWall,
    "jump_spot": JumpSpot,
    "elevator": Elevator,
    "perk_machine": PerkMachine,
    "perk_code": PerkCode,
    "pack_a_punch": PackAPunch,
}


def map_path(map_id):
    return os.path.join(settings.MAP_DIR, f"{map_id}.json")


def map_exists(map_id):
    return bool(map_id) and os.path.isfile(map_path(map_id))


def load_map(map_id):
    with open(map_path(map_id), encoding="utf-8") as f:
        data = json.load(f)
    return build_map(data)


def build_map(data):
    width, height = data["size"]
    m = GameMap(data["id"], data.get("name", data["id"]), width, height)

    m.walkable = [pygame.Rect(r) for r in data.get("walkable", [])]
    m.collision = CollisionGrid(width, height, settings.COLLISION_CELL, m.walkable)
    m.spawns = {k: tuple(v) for k, v in data.get("spawns", {}).items()}
    m.ground = data.get("ground", {})
    m.secrets = data.get("secrets", [])

    m.walls = [Wall.from_data(d) for d in data.get("walls", [])]
    for d in data.get("obstacles", []) + data.get("decorations", []):
        prop = Prop.from_data(d)
        (m.obstacles if prop.solid else m.decorations).append(prop)

    for d in data.get("interactables", []):
        cls = INTERACTABLE_TYPES.get(d["type"])
        if cls is None:
            print(f"[map_loader] Tipo de interactuable desconocido: {d['type']}")
            continue
        if cls is Enemy and not settings.ENEMIES_ENABLED:
            continue
        m.interactables.append(cls.from_data(d))

    m.triggers = [TriggerZone.from_data(d) for d in data.get("triggers", [])]
    m.exits = [MapTransition.from_data(d) for d in data.get("exits", [])]
    m.hidden_areas = [HiddenArea(d["rect"], d.get("style", "foliage"), d.get("secret"))
                      for d in data.get("hidden_areas", [])]

    forest = data.get("forest")
    if forest:
        # Los muros y los interactuables no deben quedar tapados por árboles.
        exclusions = [w.footprint.inflate(8, 8) for w in m.walls]
        exclusions += [it.rect.inflate(40, 40) for it in m.interactables]
        exclusions += [pygame.Rect(r) for r in forest.get("exclude", [])]
        m.forest = generate_forest(width, height, m.walkable, exclusions,
                                   forest.get("spacing", settings.FOREST_TREE_SPACING),
                                   forest.get("seed", 0), forest.get("pine_ratio", 0.25),
                                   forest.get("style", "forest"))

    m.build_index()
    return m
