class BaseChunker:
    def __init__(self, parser):
        self.parser = parser

    def build(self):
        raise NotImplementedError