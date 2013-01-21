from simul.formats.format import Format

class Composite(Format):
    
    def __init__(self, schema_in, schema_out):
        Format.__init__(self, schema_in, schema_out)

        self.setup()

    def is_fixed(self):
        if type(self._matches) == list:
            for m in self._matches:
                if not m.is_fixed():
                    return False
            return True

        elif type(self._matches) == dict:
            for l in self._matches.values():
                for m in l:
                    if not m.is_fixed():
                        return False
            return True

    def is_modified(self):
        if type(self._matches) == list:
            for m in self._matches:
                if m.is_modified():
                    return True
            return False

        elif type(self._matches) == dict:
            for l in self._matches.values():
                for m in l:
                    if m.is_modified():
                        return True
            return False

    def clear(self):
        raise NotImplementedError()

    def should_use_mc(self):
        raise NotImplementedError()

    def fill(self):
        raise NotImplementedError()

    def instances(self):
        raise NotImplementedError()

    def random_instance(self, new=False):
        raise NotImplementedError()

    def compute_mc(self, N):
        raise NotImplementedError()

    def compute_exact(self):
        raise NotImplementedError()

    def detail(self, strings):
        raise NotImplementedError()

    def summary(self, strings, title=None):
        raise NotImplementedError()

    def setup(self):
        raise NotImplementedError()

    def get_match(self, key):
        raise NotImplementedError()

    def get_matches(self):
        return self._matches
