"""Exception types shared by the pyquest script engine and world model."""

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


class QuestError(Exception):
    """Base class for all recoverable pyquest runtime errors."""


class ScriptError(QuestError):
    """A script could not be parsed or executed."""


class UndefinedJumpError(ScriptError):
    """A script tried to call or jump to a function that is not defined."""

    def __init__(self, name):
        self.target = name
        super().__init__("Undefined jump target or function: " + str(name))


class MissingObjectError(QuestError):
    """An object was referenced that does not exist in the world model."""

    def __init__(self, name):
        self.object_name = name
        super().__init__("No such object in the world model: " + str(name))
