class Item(object):
    def __init__(self, ID = "", names = None, desc = "", takeDesc = "", isHidden = False, isTakeable = True):
        self.ID = ID
        self.names = [] if names is None else names
        self.desc = desc
        self.takeDesc = takeDesc
        self.isHidden = isHidden
        self.isTakeable = isTakeable
