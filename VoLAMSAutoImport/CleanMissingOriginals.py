import os
import sys

import asyncio

sys.path.append('..')

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from ak_autobahn import AkComponent

from waapi_SG import WAAPI_URI





class MyComponent(AkComponent):
    Results = {}
    parentObject = {}

    WwiseQueryResults = {}
    WwiseAudioMissingOriginals = {}
    WwiseEventsToDelete = []
    parentID = ""
    Input_ParentObjectName = "DesertMission"
    ActorMixerPath = "\Actor-Mixer Hierarchy"

    ImportAudioFilePath = ""    #full path to root folder for files to import
    ImportLanguage = "English(UK)" #Default language for Wwise projects, Or SFX
    pathToOriginalsFromProjectRoot = ["Originals","Voices",ImportLanguage] # Where are the English VO files
    stepsUpToCommonDirectory = 1    # How many folders up from the script is the shared dir with wwise project
    DirOfWwiseProjectRoot = ["Wwise_Project","WAAPI_Test"] ## Name/path of wwise project relative to the common directory

    def onJoin(self, details):
        ###### Function definitions #########

        def exit():
            self.leave()

        def beginUndoGroup():
            self.call(WAAPI_URI.ak_wwise_core_undo_begingroup)

        def cancelUndoGroup():
            self.call(WAAPI_URI.ak_wwise_core_undo_cancelgroup)

        def endUndoGroup():
            undoArgs = {"displayName": "Script Auto Cleaning"}
            self.call(WAAPI_URI.ak_wwise_core_undo_endgroup, {}, **undoArgs)

        def saveWwiseProject():
            self.call(WAAPI_URI.ak_wwise_core_project_save)

        def setupSubscriptions():
            # Subscribe to ak.wwise.core.object.created
            # Calls on_object_created whenever the event is received
            self.subscribe(onParentSelected, WAAPI_URI.ak_wwise_ui_selectionchanged)

        def getProject():
            arguments = {
                "from": {"ofType": ["Project"]},
                "options": {
                    "return": ["type","id", "name", "filePath"]
                }
            }
            try:
                res = yield from self.call(WAAPI_URI.ak_wwise_core_object_get, **arguments)
            except Exception as ex:
                print("call error: {}".format(ex))
                cancelUndoGroup()
            else:
                MyComponent.WwiseProjectPath = res.kwresults["return"][0]['filePath']
                MyComponent.WwiseProjectPath = MyComponent.WwiseProjectPath.replace("Y:","~").replace('\\', '/')
                MyComponent.pathToWwiseProject = os.path.dirname(os.path.abspath(MyComponent.WwiseProjectPath))

        def getDefaultLanguage():

            arguments = {
                "from": {"ofType": ["Project"]},
                "options": {
                    "return": ["@DefaultLanguage"]
                }
            }
            try:
                res = yield from self.call(WAAPI_URI.ak_wwise_core_object_get, **arguments)
            except Exception as ex:
                print("call error: {}".format(ex))
                cancelUndoGroup()
            else:
                MyComponent.ImportLanguage = res.kwresults["return"][0]['@DefaultLanguage']


        def getSelectedObject():
            selectedObjectArgs = {
                "options": {
                    "return": ["workunit", "name", "parent", "id", "path","@IsVoice","type"]
                }
            }
            try:
                x = yield from self.call(WAAPI_URI.ak_wwise_ui_getselectedobjects, {}, **selectedObjectArgs)
            except Exception as ex:
                print("call error: {}".format(ex))
            else:
                MyComponent.Results = x

        def getAudioFilesInWwise(object):
            #print("Get a list of the audio files currently in the project, under the selected object")
            arguments = {
                "from": {"id": [object]},
                "transform": [
                    {"select": ["descendants"]},
                    {"where":["type:isIn",["Sound"]]}
                ],
                "options": {
                    "return": ["id","type", "name", "path", "sound:originalWavFilePath", "isPlayable","audioSource:playbackDuration"]
                }
            }
            try:
                res = yield from self.call(WAAPI_URI.ak_wwise_core_object_get, **arguments)
            except Exception as ex:
                print("call error: {}".format(ex))
            else:
                MyComponent.WwiseQueryResults = res.kwresults["return"]

        def getWwiseEventByName(eventName):
            arguments = {
                "from": {"path": ["\\Events"]},
                "transform": [
                    {"select":["descendants"]},
                    {"where": ["name:matches", eventName]}
                ],
                "options": {
                    "return": ["id", "name", "path"]
                }
            }
            try:
                res = yield from self.call(WAAPI_URI.ak_wwise_core_object_get, **arguments)
            except Exception as ex:
                print("call error: {}".format(ex))
            else:
                MyComponent.WwiseEventsToDelete.append(res.kwresults["return"][0])

        def getIDofParent(ActorMixerPath,parentObject):
            arguments = {
                "from": {"path": [ActorMixerPath + parentObject]},
                "options": {
                    "return": ["id", "name", "path"]
                }
            }
            try:
                res = yield from self.call(WAAPI_URI.ak_wwise_core_object_get, **arguments)
            except Exception as ex:
                print("call error: {}".format(ex))
            else:
                MyComponent.parentID = (res.kwresults["return"][0]["id"])

        def createListOfBrokenAudio(WwiseQueryResults):
            #print("creating a list of existing wwise sounds")
            list = []
            for i in WwiseQueryResults:
                #print(i)
                if i["audioSource:playbackDuration"]["playbackDurationMax"] == 0.0:
                    #print(i)
                    list.append(i)
            MyComponent.WwiseAudioMissingOriginals = list

        def deleteWwiseObject(object):
            args = {"object":object}
            try:
                yield from self.call(WAAPI_URI.ak_wwise_core_object_delete, {}, **args)
            except Exception as ex:
                print("call error: {}".format(ex))

        def SetupImportParentObject(objectName):
            # Setting up the import parent object
            arguments = {
                "from": {"path": ["\Actor-Mixer Hierarchy"]},
                "transform": [
                    {"select":['descendants']},
                    {"where": ["name:matches", objectName]}
                ],
                "options": {
                    "return": ["id","type", "name", "path"]
                }
            }
            try:
                res = yield from self.call(WAAPI_URI.ak_wwise_core_object_get, **arguments)
            except Exception as ex:
                print("call error: {}".format(ex))
                cancelUndoGroup()
            else:
                ID = ""
                obj = ""
                path = ""
                for x in res.kwresults["return"]:
                    if x["type"] == "WorkUnit":
                        ID = str(x["id"])
                        obj = x
                        path = str(x["path"])
                MyComponent.parentObject = obj
                MyComponent.parentObjectPath = path
                MyComponent.parentID = ID


        def setupBatchFileSysArgs():
            print("Cleaning missing files from.. " + sys.argv[1])  # Import section name
            MyComponent.Input_ParentObjectName = str(sys.argv[1])
            #StringInputOfDirOfWwiseProjectRoot = (sys.argv[2])
            #MyComponent.DirOfWwiseProjectRoot = StringInputOfDirOfWwiseProjectRoot.split("/")
            #MyComponent.stepsUpToCommonDirectory = int(sys.argv[3])

        def walk_up_folder(path, depth):
            _cur_depth = 0
            while _cur_depth < depth:
                path = os.path.dirname(path)
                _cur_depth += 1
            return path

        ###### End of function definitions  #########


        ###### Main logic flow #########
        try:
            res = yield from self.call(WAAPI_URI.ak_wwise_core_getinfo)  # RPC call without arguments
        except Exception as ex:
            print("call error: {}".format(ex))
        else:
            # Call was successful, displaying information from the payload.
            print("Hello {} {}".format(res.kwresults['displayName'], res.kwresults['version']['displayName']))

        #setupSubscriptions()

        if (len(sys.argv) > 1):
            if(len(sys.argv)) >= 2:
                setupBatchFileSysArgs()
            else:
                print("ERROR! Not enough arguments")

        if MyComponent.Input_ParentObjectName == "":
            exit()

        beginUndoGroup()

        currentWorkingDir = os.getcwd()
        print("Current Working Directory = " + currentWorkingDir)

        yield from getProject()

        yield from getDefaultLanguage()

        #### Construct the import audio file path. Use Section name from args

        ## Construct the path down to the Originals section folder containing the files to import

        pathToOriginalFiles = os.path.join(MyComponent.pathToWwiseProject, *MyComponent.pathToOriginalsFromProjectRoot)
        pathToSectionFiles = os.path.join(pathToOriginalFiles, MyComponent.Input_ParentObjectName)
        MyComponent.ImportAudioFilePath = os.path.abspath(pathToSectionFiles)


        yield from SetupImportParentObject(MyComponent.Input_ParentObjectName)

        #yield getIDofParent(MyComponent.ActorMixerPath,MyComponent.Input_ParentObjectName)
        yield from getAudioFilesInWwise(MyComponent.parentID)
        createListOfBrokenAudio(MyComponent.WwiseQueryResults)

        for x in MyComponent.WwiseAudioMissingOriginals:
            name = str(x["name"])
            yield from getWwiseEventByName(name)
            yield from deleteWwiseObject(x["id"])

        for x in MyComponent.WwiseEventsToDelete:
            id = str(x["id"])
            yield from deleteWwiseObject(id)

        numberOfFilesCleaned = len(MyComponent.WwiseAudioMissingOriginals)
        print(str(numberOfFilesCleaned) + " Files cleaned from " + MyComponent.Input_ParentObjectName)
        if numberOfFilesCleaned > 0:
            saveWwiseProject()

        endUndoGroup()
		

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
