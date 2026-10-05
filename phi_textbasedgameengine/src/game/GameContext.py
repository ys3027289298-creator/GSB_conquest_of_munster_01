from gameobjects.GameObject import GameObject
from typing import Optional, Callable, List, Dict, Any, Tuple, Type
from game.GameError import GameError

class GameContext():
	def __init__(self, templates: Optional[Dict[str, Tuple[Type[GameObject], Dict[str, Any]]]] = None):
		self.objects: Dict[int, GameObject] = {}
		self.templates: Dict[str, Tuple[Type[GameObject], Dict[str, Any]]] = dict(templates or {})
		self.messages: List[str] = []

	def add(self, obj: GameObject) -> bool:
		"""
		Add a gameObject to the current context
		@param obj The object to add
		@return True if the object was added, False if an object with the
				same id was already present
		"""
		assert isinstance(obj, GameObject), "Only GameObjects can be added to context"
		if obj.id in self.objects:
			return False
		self.objects[obj.id] = obj
		return True

	def spawn(self, name: str) -> GameObject:
		"""
		Spawns a new instance of a named object template into this context
		@param name The (simplified) name of the object template
		@return The newly spawned GameObject
		@throws GameError if no template with that name exists
		"""
		if name not in self.templates:
			raise GameError(f'Cannot spawn unknown object "{name}"')
		_class, template = self.templates[name]
		obj = GameObject.load_from_template(template, _class)
		self.add(obj)
		return obj

	def send(self, message: str) -> None:
		"""
		Sends a message to the entity interacting with the context
		(e.g. the player), recording it for delivery/display
		@param message The message to send
		"""
		self.messages.append(message)

	def clear(self) -> List[GameObject]:
		"""
		Removes every object from the context
		@return The objects that were removed
		"""
		removed = list(self.objects.values())
		self.objects = {}
		return removed

	def enter(self, objects: Optional[List[GameObject]] = None) -> None:
		"""
		Switches the context to a new area: removes all objects currently in
		the context (so they can no longer be acted upon) and optionally
		populates it with the objects of the area entered
		@param objects GameObjects present in the area entered
		"""
		self.clear()
		if objects:
			for obj in objects:
				self.add(obj)

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

