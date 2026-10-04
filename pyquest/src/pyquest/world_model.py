from pyquest.script_engine import QuestValue

__author__ = "Adrian Welcker"
__copyright__ = """Copyright 2018 Adrian Welcker

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""


class QuestObject:
    def __init__(self, name, **kwattribs):
        for key, value in kwattribs.items():
            setattr(self, key, value)
        self.name = name

    def __str__(self):
        return "Object {} with attributes {}".format(self.name, self.__dict__)

    def __setattr__(self, key, value):
        if isinstance(value, int) or isinstance(value, str) or isinstance(value, float):
            object.__setattr__(self, key, QuestValue(value))
        else:
            object.__setattr__(self, key, value)

    def snapshot(self):
        """Return a plain-data copy of this object's dynamic state.

        Structural references (the parent object) are not part of the
        snapshot; only scalar and list attributes are kept so the result
        can be serialised and later handed to restore().
        """
        state = {}
        parent = self.__dict__.get("parent")
        if parent is not None:
            parent_name = getattr(parent, "name", None)
            if isinstance(parent_name, QuestValue):
                parent_name = parent_name._value
            state["parent"] = parent_name
        for key, value in self.__dict__.items():
            if key == "parent":
                continue
            if isinstance(value, QuestValue):
                value = value._value
            if isinstance(value, (str, int, float, bool)) or value is None:
                state[key] = value
            elif isinstance(value, (list, tuple)):
                state[key] = [item._value if isinstance(item, QuestValue) else item
                              for item in value]
        return state

    def restore(self, state):
        """Reset this object's dynamic state from a snapshot.

        Attributes not present in the snapshot are removed; the object's
        name and parent (its place in the world tree) are preserved.
        """
        name = self.name
        parent = self.__dict__.get("parent")
        self.__dict__.clear()
        self.__dict__["name"] = name
        if parent is not None:
            self.__dict__["parent"] = parent
        for key, value in state.items():
            if key in ("name", "parent"):
                continue
            setattr(self, key, value)
