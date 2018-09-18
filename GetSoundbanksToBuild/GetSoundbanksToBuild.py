
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

        def getQuerySearchCriteria(id):
            #print("Get a list of the audio files currently in the project, under the selected object")
            arguments = {
                "from": {"id": [id]},
                "transform": [
                    {"select": ["children"]},
                    {"where": ["type:isIn", ["SearchCriteria"]]}
                ],
                "options": {
                    "return": ["id","type", "name", "path"]
                }
            }
            try:
                res = yield from(self.call(WAAPI_URI.ak_wwise_core_object_get, **arguments))
            except Exception as ex:
                print("call error: {}".format(ex))
            else:
                MyComponent.SoundbankQuerySearchCriteria = res.kwresults["return"][0]

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

        def SetQuerySearchProperty(object, searchValue):
            arguments = {
                "object": object,
                "property":'ObjectReferenced',
                "value": searchValue
            }
            try:
                yield from(self.call(WAAPI_URI.ak_wwise_core_object_setproperty, **arguments))
            except Exception as ex:
                print("call error: {}".format(ex))
            else:
                print ("value set")


        def GetSoundbankQuery():
            print("Getting query from wwise")

            arguments = {
                "from": {"ofType": ["Query"]},
                "transform": [
                    {"where": ["name:matches", "SoundbankReferencing"]}
                        ],
                "options": {
                    "return": ["id", "name","path"]
                }
            }
            try:
                res = yield from(self.call(WAAPI_URI.ak_wwise_core_object_get, **arguments))
            except Exception as ex:
                print("call error: {}".format(ex))
            else:
                MyComponent.SoundbankQuery= res.kwresults["return"][0]

        def RunSoundbankQuery(query):
            print("Running Query")

            arguments = {
                "from": {"query": [query]},
                "options": {
                    "return": ["id", "name", "type","path"]
                }
            }
            try:
                res = yield from(self.call(WAAPI_URI.ak_wwise_core_object_get, **arguments))
            except Exception as ex:
                print("call error: {}".format(ex))
            else:
                queryResults = res.kwresults["return"]
                for i in queryResults:
                    MyComponent.BanksToGenerate.append(i)

        def SearchForBankRefsAndUpdateLists(actorMixerList):
            print("hello")

            for ActorMixer in actorMixerList:
                id = str(ActorMixer['id'])
                workunit = ActorMixer['workunit']['name']
                yield SetQuerySearchProperty(str(MyComponent.SoundbankQuerySearchCriteria['id']), id)



                ## use object get with the query for X in changes
                yield RunSoundbankQuery(MyComponent.SoundbankQuery['id'])

        def GetSoundbanksFromPath():
            print("Getting query from wwise")

            arguments = {
                "from": {"path": ["\\Soundbanks"]},
                "transform": [
                    {"select": ["descendants"]},
                    {"where": ["type:isIn", ["SoundBank"]]}
                        ],
                "options": {
                    "return": ["id", "name","path"]
                }
            }
            try:
                res = yield from self.call(WAAPI_URI.ak_wwise_core_object_get, **arguments)
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


        ## Get the soundbank query ID from project
 #       yield GetSoundbankQuery()

        ## Set the query property  Property Name="ObjectReferenced" to GUID
#        yield getQuerySearchCriteria(MyComponent.SoundbankQuery['id'])

        yield from GetSoundbanksFromPath()

        #Get the actor mixers from project
 #       yield getActorMixersInProject()

        #Loop through actor mixer list, setting query and running, append bank list
#        yield SearchForBankRefsAndUpdateLists(MyComponent.ActorMixersInProject)


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
