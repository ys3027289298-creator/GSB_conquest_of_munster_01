import os.path as path

from game.YamlUtil import YamlUtil
from game.GameError import GameError
from game.GameContext import GameContext
from gameobjects.GameObject import GameObject
from gameobjects.Enemy import Enemy
from gameobjects.Item import Item

class Game(object):
    """
    A Game object is an instance of one entire game. It keeps
    track of all enemy templates, rooms, items, player info, and 
    so on.
    """
    
    def __init__(self, enemies, items, rooms, player):
        """
        @param enemies List of EnemyTemplate objects
        @param items TODO: not yet implemented
        @param rooms TODO: not yet implemented
        @param player TODO: not yet implemented
        """
        self.enemies = enemies
        self.items = items
        self.rooms = rooms
        self.player = player
        # Object templates available to spawn, keyed by simplified name:
        # {name: (GameObject subclass, raw yaml template)}
        self.templates = {}

    def new_context(self) -> GameContext:
        """
        Creates a fresh GameContext with the game's spawn templates loaded
        @return A new empty GameContext
        """
        return GameContext(self.templates)
    
    def save_game_state(self, save_path : str) -> None:
        """
        Saves the current state of the game into a file
        TODO: not yet implemented
        @param save_path the path of the file to write game data into
        """
        pass
    
    def load_game_state(self, load_path : str) -> None:
        """
        Loads a game state previously saved by save_game_state.
        TODO: not yet implemented
        @param load_path the path of the save file to load
        """
        pass
    
    @staticmethod
    def load_game(directory : str):
        """
        Loads yaml files from input directory into a game object.
        @param directory directory to load the game from
        @return a loaded Game object
        @throws GameError if the directory is missing, a yaml file is invalid,
                a required field is missing, or a name is invalid/duplicate
        """
        if not path.isdir(directory):
            raise GameError("Could not find game directory '{}'".format(directory))

        enemy_templates = YamlUtil.load_yaml_data( YamlUtil.get_yaml_filename(directory, "enemies") )
        rooms = YamlUtil.load_yaml_data( YamlUtil.get_yaml_filename(directory, "rooms") )
        item_templates = YamlUtil.load_yaml_data( YamlUtil.get_yaml_filename(directory, "items") )
        player = YamlUtil.load_yaml_data( YamlUtil.get_yaml_filename(directory, "player") )

        enemy_names = YamlUtil.get_names(enemy_templates)
        item_names = YamlUtil.get_names(item_templates)
        YamlUtil.get_names(rooms)

        # Aggregator files (include-only) load as empty objects; drop them
        rooms = [room for room in rooms if 'name' in room]
        player = [entry for entry in player if 'name' in entry]

        # Names must be unique across all spawnable object categories
        seen = {}
        templates = {}
        for name in enemy_names:
            seen[name] = 'enemy'
        for name in item_names:
            if name in seen:
                raise GameError('The name "{}" is used by both an item and a {}'.format(name, seen[name]))
            seen[name] = 'item'

        def build(template_list, klass, category):
            objects = []
            for template in template_list:
                if 'name' not in template:
                    continue # Aggregator file (include-only), no object defined
                try:
                    obj = GameObject.load_from_template(template, klass)
                except GameError:
                    raise
                except (AttributeError, KeyError) as ex:
                    raise GameError('Invalid {} definition: {}'.format(category, ex))
                objects.append(obj)
                templates[YamlUtil.simplify_name(template['name'])] = (klass, template)
            return objects

        enemies = build(enemy_templates, Enemy, 'enemy')
        items = build(item_templates, Item, 'item')

        game = Game(enemies, items, rooms, player)
        game.templates = templates
        return game
