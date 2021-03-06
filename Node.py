from hashlib import md5


class Node:
    """ Node class """
    def __init__(self, device=None, x=0, y=0):
        self.id = device['id']
        self.name = device['name']
        self.type = device['type']
        self.original_id = device['original_id'] if 'original_id' in device.keys() else None
        self.created_at = device['created_at'] if 'created_at' in device.keys() else None
        self.neighbors = device['neighbors'] if 'neighbors' in device.keys() else None
        self.children = device['children'] if 'children' in device.keys() else None
        self.interfaces = device['interfaces'] if 'interfaces' in device.keys() else None
        self.x = x
        self.y = y

    def __hash__(self):
        return int(md5(self.id.encode()).hexdigest(), 16)

    def __eq__(self, other):
        return self.id == other.id

    def __str__(self):
        return self.id
