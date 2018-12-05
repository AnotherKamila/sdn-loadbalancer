import attr
from twisted.internet import defer
from myutils.twisted_utils import print_method_call


@attr.s
class P4Table(object):
    name       = attr.ib()
    controller = attr.ib()
    data       = attr.ib(factory=dict)

    def __getitem__(self, key):
        key = tuple(str(k) for k in key)
        return self.data[key]

    def __setitem__(self, key, value):
        raise NotImplementedError("To write to the table, use the .add / .modify methods.")

    def __len__(self):
        return len(self.data)

    @print_method_call
    @defer.inlineCallbacks
    def add(self, keys, action, values):
        keys, values = self._fix_keys_values(keys, values)
        assert keys not in self.data, "add called with duplicate keys!"
        res = yield self.controller.table_add(self.name, action, keys, values)
        assert res != None, "table_add failed!"
        self.data[keys]    = (action, values)

    @print_method_call
    @defer.inlineCallbacks
    def modify(self, keys, new_action, new_values):
        keys, new_values = self._fix_keys_values(keys, new_values)
        assert keys in self.data, "modify called without existing entry!"
        yield self.controller.table_modify_match(self.name, new_action, keys, new_values)
        self.data[keys] = (new_action, new_values)

    def _fix_keys_values(self, keys, values):
        keys   = tuple(str(k) for k in keys)
        values = tuple(str(v) for v in values)
        return keys, values
