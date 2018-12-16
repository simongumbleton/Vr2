
import asyncio

import os.path


from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from ak_autobahn import AkComponent

from waapi_SG import WAAPI_URI



class MyComponent(AkComponent):

    INPUT_filelist = []
    INPUT_SelectedObj = None

    ActorMixerWUs = []
    EventWUs = []
    sourceWavs = []
    ## List of banks with changes that need generating ##
    BanksToGenerate = []

    myTransforms = [

    [
        {"select": ['referencesTo']},
        {"where": ['type:isIn', ['SoundBank']]},
        "distinct",
    ],

    [
        {"select": ['descendants']},
        {"select": ['referencesTo']},
        {"where": ['type:isIn', ['SoundBank']]},
        "distinct",
    ],

    [
        {"select": ['ancestors']},
        {"select": ['referencesTo']},
        {"where": ['type:isIn', ['SoundBank']]},
        "distinct",
    ],

    [
        {"select": ['referencesTo']},
        {"where": ['type:isIn', ['Action']]},
        "distinct",
        {"select": ['ancestors']},
        {"select": ['referencesTo']},
        {"where": ['type:isIn', ['SoundBank']]},
        "distinct",
    ],

    [
        {"select": ['descendants']},
        {"select": ['referencesTo']},
        {"where": ['type:isIn', ['Action']]},
        "distinct",
        {"select": ['ancestors']},
        {"select": ['referencesTo']},
        {"where": ['type:isIn', ['SoundBank']]},
        "distinct",
    ],

    [
        {"select": ['ancestors']},
        {"select": ['referencesTo']},
        {"where": ['type:isIn', ['Action']]},
        "distinct",
        {"select": ['ancestors']},
        {"select": ['referencesTo']},
        {"where": ['type:isIn', ['SoundBank']]},
        "distinct",
    ],
    ]

    def onJoin(self, details):
        ###### Function definitions #########

        def exit():
            self.leave()

        def beginUndoGroup():
            self.call(WAAPI_URI.ak_wwise_core_undo_begingroup)

        def cancelUndoGroup():
            self.call(WAAPI_URI.ak_wwise_core_undo_cancelgroup)

        def endUndoGroup():
            undoArgs = {"displayName": "Script Auto Importer"}
            self.call(WAAPI_URI.ak_wwise_core_undo_endgroup, {}, **undoArgs)

        def saveWwiseProject():
            self.call(WAAPI_URI.ak_wwise_core_project_save)

        def onSelectionChanged(objects):
            MyComponent.BanksToGenerate.clear()
            print("Selection changed")
            for object in objects:
                for transform in MyComponent.myTransforms:
                    yield from GetSoundbanks('id',object['id'],transform)
            print(MyComponent.BanksToGenerate)



        def SortInputFiles(inputfilelist):
            for file in inputfilelist:
                if os.path.splitext(file)[1][1:] == "wav":
                    MyComponent.sourceWavs.append(file)
                else:
                    if os.path.splitext(file)[1][1:] == "wwu":
                        if "Actor-Mixer Hierarchy" in os.path.abspath(file):
                            MyComponent.ActorMixerWUs.append(file)
                        if "Events" in os.path.abspath(file):
                            MyComponent.EventWUs.append(file)



        def GetSoundbanks(fromType,fromValue,transform):
            # Return all Soundbanks referencing any object of the Work Unit directly
            arguments = {
                "from": {fromType: [fromValue]},
                "transform": transform,
            }
            options = {
                "return": ['id', 'name', 'type']
            }
            try:
                res = yield from self.call(WAAPI_URI.ak_wwise_core_object_get, **arguments, options=options)
            except Exception as ex:
                print("call error: {}".format(ex))
            else:
                # print (res.kwresults["return"])
                for bank in res.kwresults["return"]:
                    if bank["name"] not in MyComponent.BanksToGenerate:
                        MyComponent.BanksToGenerate.append((bank["name"]))


        ###### Main logic flow #########
        ## Connect to Wwise ##
        try:
            res = yield from(self.call(WAAPI_URI.ak_wwise_core_getinfo))  # RPC call without arguments
        except Exception as ex:
            print("call error: {}".format(ex))
        else:
            # Call was successful, displaying information from the payload.
            print("Hello {} {}".format(res.kwresults['displayName'], res.kwresults['version']['displayName']))

        self.subscribe(onSelectionChanged,WAAPI_URI.ak_wwise_ui_selectionchanged)
        #####  Do Some Cool stuff here #######


        SortInputFiles(MyComponent.INPUT_filelist)



        #yield from GetSoundbanks("path",'\\Actor-Mixer Hierarchy\\Cinematics',MyComponent.myTransforms[0])



        #print (MyComponent.BanksToGenerate)
        #exit()


    def onDisconnect(self):
        print("The client was disconnected.")

        asyncio.get_event_loop().stop()


if __name__ == '__main__':
    runner = ApplicationRunner(url=u"ws://127.0.0.1:8095/waapi", realm=u"realm1")
    try:
        runner.run(MyComponent)
    except Exception as e:
        print(type(e).__name__ + ": Is Wwise running and Wwise Authoring API enabled?")
