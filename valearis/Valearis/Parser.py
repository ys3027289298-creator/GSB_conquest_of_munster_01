def parseCommand(command):
    if (command == None):
        raise ValueError("command should be given")

    if (not isinstance(command, str)):
        raise ValueError("command should be a string")

    parts = command.strip().split(None, 1)

    if (parts.__len__() == 0):
        raise ValueError("command should not be empty")

    verb = parts[0].lower()
    argument = parts[1].strip() if parts.__len__() > 1 else None
    return (verb, argument)
