import attr
from twisted.internet import defer
from myutils.twisted_utils import print_method_call


@attr.s
class P4Table(object):
    name       = attr.ib()
    controller = attr.ib()
    data       = attr.ib(factory=dict)

    def __getitem__(self, key):
        key = self._fix_values(key)
        return self.data[key]

    def __setitem__(self, key, value):
        raise NotImplementedError("To write to the table, use the .add / .modify methods.")

    def __len__(self):
        return len(self.data)

    @print_method_call
    @defer.inlineCallbacks
    def add(self, keys, action, params):
        keys, params = self._fix_keys_params(keys, params)
        if keys in self.data:
            raise ValueError("add called with duplicate keys: {}".format(keys))
        res = yield self.controller.table_add(self.name, action, keys, params)
        assert res != None, "table_add failed!"
        self.data[keys] = (action, params)

    @print_method_call
    @defer.inlineCallbacks
    def modify(self, keys, new_action, new_params):
        keys, new_params = self._fix_keys_params(keys, new_params)
        if not keys in self.data:
            raise ValueError("modify called without existing entry: {}".format(keys))
        yield self.controller.table_modify_match(self.name, new_action, keys, new_params)
        self.data[keys] = (new_action, new_params)

    def rm(self, keys):
        keys = self._fix_values(keys)
        if not keys in self.data:
            raise ValueError("rm called for a non-existent entry: {}".format(keys))
        yield self.controller.table_delete_match(self.name, keys)
        del self.data[keys]

    def _fix_keys_params(self, keys, params):
        return [self._fix_values(x) for x in (keys, params)]

    def _fix_values(self, xs):
        return tuple(str(x) for x in xs)
