import sys
import os
sys.path.append('..')

from waapi_SG import WaapiClient
import pprint

# Connect (default URL)
client = WaapiClient()

# Return all Soundbanks referencing any object of the Default Work Unit, through an event
args = {
    "from": {"path": ['\\Actor-Mixer Hierarchy\\Default Work Unit']},
    "transform": [
        {"select": ['descendants']},
        {"select": ['referencesTo']},
        {"where": ['type:isIn', ['Action']]},
        "distinct",
        {"select": ['ancestors']},
        {"select": ['referencesTo']},
        {"where": ['type:isIn', ['SoundBank']]},
        "distinct",
    ]
}
options = {
    "return": ['id', 'name','type']
}
result = client.call("ak.wwise.core.object.get", args, options=options)
pprint.pprint(result)

# Return all Soundbanks referencing any object of the Default Work Unit directly
args = {
    "from": {"path": ['\\Actor-Mixer Hierarchy\\Default Work Unit']},
    "transform": [
        {"select": ['descendants']},
        {"select": ['referencesTo']},
        {"where": ['type:isIn', ['SoundBank']]},
        "distinct",
    ]
}
options = {
    "return": ['id', 'name','type']
}
result = client.call("ak.wwise.core.object.get", args, options=options)
pprint.pprint(result)

# Disconnect
client.disconnect()