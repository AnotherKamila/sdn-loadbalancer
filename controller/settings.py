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
