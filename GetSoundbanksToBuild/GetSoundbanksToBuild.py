
import asyncio


from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from ak_autobahn import AkComponent

from waapi import WAAPI_URI



class MyComponent(AkComponent):


    ## List of banks with changes that need generating ##
    BanksToGenerate = []

    SoundbankQuery = {}
    SoundbankQuerySearchCriteria = {}

    SearchValue = ""

    ActorMixersInProject = {}

    WorkUnitsToBanksMap = {}



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

        def getActorMixersInProject():
            #print("Get a list of the audio files currently in the project, under the selected object")
            arguments = {
                "from": {"path": ["\\Actor-Mixer Hierarchy"]},
                "transform": [
                    {"select": ["descendants"]},
                    {"where": ["type:isIn", ["ActorMixer"]]}
                ],
                "options": {
                    "return": ["id", "name", "workunit"]
                }
            }
            try:
                res = yield from(self.call(WAAPI_URI.ak_wwise_core_object_get, **arguments))
            except Exception as ex:
                print("call error: {}".format(ex))
            else:
                MyComponent.ActorMixersInProject = res.kwresults["return"]


        def SearchForBankRefsAndUpdateLists(actorMixerList):
            print("hello")

            for ActorMixer in actorMixerList:
                id = str(ActorMixer['id'])
                workunit = ActorMixer['workunit']['name']


        def GetSoundbanksFromActorMixerWorkUnit(workunit):
            print("Getting query from wwise")

            # Return all Soundbanks referencing any object of the Default Work Unit directly
            arguments = {
                 "from": {"path": ['\\Actor-Mixer Hierarchy\\'+workunit]},
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
                "return": ['id', 'name', 'type']
            }
            try:
                res = yield from self.call(WAAPI_URI.ak_wwise_core_object_get, **arguments,options=options)
            except Exception as ex:
                print("call error: {}".format(ex))
            else:
                print (res.kwresults["return"])

        def GetSoundbanksFromEventWorkUnit(workunit):
            print("Getting query from wwise")

            # Return all Soundbanks referencing any object of the Default Work Unit directly
            arguments = {
                 "from": {"path": ['\\Events\\'+workunit]},
                    "transform": [
                    {"select": ['descendants']},
                    {"select": ['referencesTo']},
                    {"where": ['type:isIn', ['SoundBank']]},
                    "distinct",
                    ]
            }
            options = {
                "return": ['id', 'name', 'type']
            }
            try:
                res = yield from self.call(WAAPI_URI.ak_wwise_core_object_get, **arguments,options=options)
            except Exception as ex:
                print("call error: {}".format(ex))
            else:
                print (res.kwresults["return"])



        ###### Main logic flow #########
        ## Connect to Wwise ##
        try:
            res = yield from(self.call(WAAPI_URI.ak_wwise_core_getinfo))  # RPC call without arguments
        except Exception as ex:
            print("call error: {}".format(ex))
        else:
            # Call was successful, displaying information from the payload.
            print("Hello {} {}".format(res.kwresults['displayName'], res.kwresults['version']['displayName']))


        #####  Do Some Cool stuff here #######

        # Get the actor mixers from project
        #yield getActorMixersInProject()

        testPath = '\\Actor-Mixer Hierarchy\\VO'

        yield from GetSoundbanksFromActorMixerWorkUnit('VO')

        yield from GetSoundbanksFromEventWorkUnit('VO')



        exit()


    def onDisconnect(self):
        print("The client was disconnected.")

        asyncio.get_event_loop().stop()


if __name__ == '__main__':
    runner = ApplicationRunner(url=u"ws://127.0.0.1:8095/waapi", realm=u"realm1")
    try:
        runner.run(MyComponent)
    except Exception as e:
        print(type(e).__name__ + ": Is Wwise running and Wwise Authoring API enabled?")
