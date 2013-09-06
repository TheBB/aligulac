from simul.formats.composite import Composite

class Team(Composite):

    def __init__(self, schema_in, schema_out):
        Composite.__init__(self, schema_in, schema_out)
