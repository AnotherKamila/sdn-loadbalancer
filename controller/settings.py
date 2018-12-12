import json
import os

def load_pools(filename='./pools.json'):
    if not os.path.exists(filename):
        raise ValueError('{}: File does not exist'.format(filename))

    with open(filename) as f:
        try:
            return json.load(f)
        except json.decoder.JSONDecodeError as e:
            raise ValueError("{}: invalid JSON".format(filename))


def load_p4settings(filename):
    d = {}
    with open(filename) as f:
        for line in f.readlines():
            if not line.startswith('#define'): continue
            split = line.split(None, 2)
            if len(split) < 3: continue
            _, key, value = split
            try:
                value = int(value.strip(), 0)
            except ValueError:
                continue
            d[key] = value
    return d

p4settings = load_p4settings(os.path.join(os.path.dirname(__file__), '..', 'p4src', 'settings.p4'))
# print(p4settings)
