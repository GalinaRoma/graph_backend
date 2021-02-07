class NeighborConnection:
    def __init__(self, connection=None):
        self.neighbor_id = connection['neighbor_id']
        self.approved = connection['approved']
        self.protocols = connection['protocols']