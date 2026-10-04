from gameobjects.GameObject import GameObject
from game.GameError import GameError
from typing import Optional, Callable, List, Dict, Any

class GameContext():
	def __init__(self):
		self.objects: Dict[int, GameObject] = {}
		self.messages: List[str] = []
		self.templates: Dict[str, GameObject] = {}

	def add(self, obj: GameObject) -> None:
		"""
		Add a gameObject to the current context
		@param obj The object to add
		@throws GameError if an object with the same id is already in the context
		"""
		assert isinstance(obj, GameObject), "Only GameObjects can be added to context"
		if obj.id in self.objects:
			raise GameError(f'Object with id {obj.id} is already in the context')
		self.objects[obj.id] = obj

	def switch_area(self, objects: List[GameObject]) -> None:
		"""
		Switches the current area, replacing all active objects with the
		objects of the new area. Objects from the previous area are no
		longer accessible through this context.
		@param objects The GameObjects of the new area
		"""
		self.objects = {}
		for obj in objects:
			self.add(obj)

	def send(self, message: str) -> None:
		"""
		Sends a message to the player (e.g. from a 'say' effect)
		@param message The message to send
		"""
		self.messages.append(message)

	def add_template(self, template: GameObject) -> None:
		"""
		Registers a template that can be spawned into the context by name
		@param template The GameObject to use as a template
		"""
		assert isinstance(template, GameObject), "Only GameObjects can be templates"
		self.templates[template.name] = template

	def spawn(self, name: str) -> GameObject:
		"""
		Spawns a new instance of a registered template into the context
		@param name The name of the template to spawn
		@throws GameError if no template with the given name is registered
		@return The newly spawned GameObject
		"""
		if name not in self.templates:
			raise GameError(f'Cannot spawn unknown object "{name}"')
		instance = self.templates[name].clone()
		self.add(instance)
		return instance

	def destroy(self, obj: GameObject) -> bool:
		"""
		Destroys a GameObject existing in the current context
		@param obj The GameObject to destroy
		@return True if obj existed and it destroyed, False if it did not exist
		"""
		if obj.id in self.objects:
			del self.objects[obj.id]
			return True
		return False

	def get_by_name(self, name: str) -> List[GameObject]:
		"""
		Gets a list of GameObjects with matching name property
		
		@param name Name of the GameObject to match
		@return A list of 0 or more matching GameObjects
		"""

		return self.get_by_prop('name', name)

	def get_by_prop(self, prop: str, value: Any) -> List[GameObject]:
		"""
		Gets a list of GameObjects with a given property
		e.g. get_by_prop('type', 'weapon')

		@param prop Name of the property to search
		@param value Value of the property to match
		@return A list of 0 or more matching GameObjects
		"""
		objects = []
		for obj in self.objects.values():
			if hasattr(obj, prop) and value == getattr(obj, prop):
				objects.append(obj)
		return objects

	def get_by_predicate(self, predicate: Callable[[GameObject], bool]) -> List[GameObject]:
		"""
		Gets a list of GameObjects matching some predicate
		e.g. get_by_predicate(lambda x: hasattr(x, 'attack') and x.attack > 5)

		@param predicate Function that takes a GameObject and
			   returns True/False based on some condition
		@return A list of 0 or more matching GameObjects
		"""
		return [obj for obj in self.objects.values() if predicate(obj)]

	# IDs are unique to instances, this will only ever return 1
	def get_by_id(self, id: int) -> Optional[GameObject]:
		"""
		Gets a gameobject by id

		@param id ID of the GameObject to find
		@return The GameObject or None if not found
		"""
		if id in self.objects:
			return self.objects[id]
		return None

