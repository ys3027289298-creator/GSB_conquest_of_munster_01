from pyquest.script_engine import QuestValue, Script

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
        self.__dict__ = kwattribs
        self.name = name

    def __str__(self):
        return "Object {} with attributes {}".format(self.name, self.__dict__)

    def __setattr__(self, key, value):
        if isinstance(value, int) or isinstance(value, str) or isinstance(value, float):
            object.__setattr__(self, key, QuestValue(value))
        else:
            object.__setattr__(self, key, value)


def encode_world_value(value):
    """Convert a live world-model value into a snapshot-safe form."""
    if isinstance(value, QuestValue):
        return value._value
    if isinstance(value, QuestObject):
        return {"__object__": value.name}
    if isinstance(value, Script):
        return {"__script__": value.name, "code": value.code}
    if isinstance(value, list):
        return [encode_world_value(item) for item in value]
    if isinstance(value, dict):
        return {key: encode_world_value(item) for key, item in value.items()}
    return value


def decode_world_value(value, identities):
    """Inverse of encode_world_value, resolving object references by name."""
    if isinstance(value, dict) and "__object__" in value:
        name = value["__object__"]
        if name not in identities:
            raise KeyError("Cannot restore state: object '{}' is missing".format(name))
        return identities[name]
    if isinstance(value, dict) and "__script__" in value:
        return Script(value["__script__"], value["code"])
    if isinstance(value, list):
        return [decode_world_value(item, identities) for item in value]
    if isinstance(value, dict):
        return {key: decode_world_value(item, identities)
                for key, item in value.items()}
    return value


def snapshot_object(obj):
    """Return a plain-data snapshot of an object's attributes."""
    return {key: encode_world_value(value) for key, value in obj.__dict__.items()}


def restore_object(obj, data, identities):
    """Restore an object's attributes from a snapshot produced by snapshot_object."""
    for key, value in data.items():
        if key == "name":
            continue  # the object's identity never changes
        setattr(obj, key, decode_world_value(value, identities))
    return obj
