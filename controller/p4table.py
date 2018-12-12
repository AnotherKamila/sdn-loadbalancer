import attr
from twisted.internet import defer
from myutils.twisted_utils import print_method_call
from myutils import all_results

@attr.s
class P4Table(object):
    controller = attr.ib()
    name       = attr.ib()
    data       = attr.ib(factory=dict, init=False)

    def _convert_values(self, keys=[], action='', params=[]):
        """
        Applies an arbitrary function to (keys, action, params) just before
        writing it to the switch. This conversion will not be visible in
        self.data.
        Override this in subclasses if needed.
        """
        return [str(k) for k in keys], action, [str(p) for p in params]

    def __getitem__(self, key):
        return self.data[tuple(key)]

    def __setitem__(self, key, value):
        raise NotImplementedError("To write to the table, use the .add / .modify methods.")

    def __len__(self):
        return len(self.data)

    @print_method_call
    @defer.inlineCallbacks
    def add(self, keys, action, params):
        keys, params = tuple(keys), tuple(params)
        if keys in self.data:
            raise ValueError("add called with duplicate keys: {}".format(keys))
        real_keys, real_action, real_params = self._convert_values(keys, action, params)
        self.data[keys] = (action, params)
        res = yield self.controller.table_add(self.name, real_action, real_keys, real_params)
        assert res != None, "table_add failed!"

    @print_method_call
    @defer.inlineCallbacks
    def modify(self, keys, new_action, new_params):
        keys, new_params = tuple(keys), tuple(new_params)
        if not keys in self.data:
            raise ValueError("modify called without existing entry: {}".format(keys))
        real_keys, real_action, real_params = self._convert_values(keys, new_action, new_params)
        yield self.controller.table_modify_match(self.name, real_action, real_keys, real_params)
        self.data[keys] = (new_action, new_params)

    @print_method_call
    @defer.inlineCallbacks
    def rm(self, keys):
        keys = tuple(keys)
        if not keys in self.data:
            raise ValueError("rm called for a non-existent entry: {}".format(keys))
        old_action, old_params = self.data[keys]
        real_keys, _, _ = self._convert_values(keys, old_action, old_params)
        yield self.controller.table_delete_match(self.name, real_keys)
        del self.data[keys]


@attr.s
class VersionedP4Table(P4Table):
    """
    Uses 1 table as "scratch" / "dirty" (the one pointed to by next_version).
    This is the one that gets updated by add/rm/modify functions. The version
    pointed to by active_version is the clean, committed one that is used by
    the controller.

    Therefore:

    * The switch should not use next_version, only active_version and older.
    * max_versions specifies the max possible number of versions _including the
      dirty one_, so the switch can in fact use at most (max_versions - 1)
      versions at a time. If the switch _needs_ k versions, set max_versions to
      k+1 (and size your version counter in P4 accordingly).

    param version_signalling_table: if None, will not signal to the switch and
                                    you should handle it yourself
    """
    version_signalling_register = attr.ib()
    max_versions                = attr.ib()
    active_version              = attr.ib(0, init=False)  # used in the switch
    next_version                = attr.ib(init=False)     # operated on by my functions
    versioned_data              = attr.ib(factory=list, init=False)  # list of dicts => data from P4Table will be set to point at data[next_version]

    def _convert_values(self, keys=[], action='', params=[]):
        keys = (self.next_version,) + keys
        return P4Table._convert_values(self, keys, action, params)

    def __attrs_post_init__(self):
        self.versioned_data = [{} for i in range(self.max_versions)]

    def init(self):
        return self._set_next_and_data()

    def _set_next_and_data(self):
        self.next_version = (self.active_version + 1) % self.max_versions
        assert 0 <= self.next_version < self.max_versions, 'math is hard'
        self.data = self.versioned_data[self.next_version]
        return self._signal_active_version()

    @print_method_call
    @defer.inlineCallbacks
    def commit_and_slide(self, copy_contents=True):
        """Flips the signalling table to commit the current state.

        Starts filling a new table (which will not be activated until the next
        commit).

        After this function, active_version will become the previous
        next_version and next_version will advance.
        """

        # 1. flip next_version => active_version
        self.active_version = self.next_version
        self.data = self.versioned_data[self.next_version]
        yield self._set_next_and_data()

        # note for the future me: if I decide to prematurely optimise and
        # parallelise, I need to wait for all removals before adding or I'll
        # get a duplicate keys error :D

        # 2. clean out the old stuff from the next_version table
        for keys in dict(self.data):  # copy to avoid changing the dict while iterating
            yield self.rm(keys)

        # 3. copy the active_version's data into the next_version table if needed
        if copy_contents:
            for keys, (action, params) in self.versioned_data[self.active_version].items():
                yield self.add(keys, action, params)

        print(' -------- committed version: {}, next version now {} --------'.format(
            self.active_version, self.next_version))

    @print_method_call
    @defer.inlineCallbacks
    def _signal_active_version(self):
        if self.version_signalling_register:
            reg_name, index = self.version_signalling_register
            yield self.controller.register_write(reg_name, index, self.active_version)

    @classmethod
    @defer.inlineCallbacks
    def get_initialised(cls, *args, **kwargs):
        obj = cls(*args, **kwargs)
        yield obj.init()
        defer.returnValue(obj)
