import os
import sys

import asyncio

sys.path.append('..')

from autobahn.asyncio.wamp import ApplicationRunner
from ak_autobahn import AkComponent

import fnmatch

from waapi_SG import WAAPI_URI

import tkinter
from tkinter import filedialog


class MyComponent(AkComponent):

# this script allows creation of Wwise objects and events
# Selecting a parent object in wwise triggers a callback that
# creates the desired object type underneath the selected parent
# Optionally, it is possible to create an event at the same time
# that Plays the recently created object....


#store a ref to the selected parent object
    parentObject = None

#flow control
    parentSelected = False
    objectCreated = False
    eventCreated = False

#dic to store return/results from yield calls
    Results = {}

#Variables for object creation
    objParID = "None"
    objType = ""
    objName = ""
    nameConflict = "merge"
    objNotes = "This object was auto created...."

#args dict for object creation For use with create object call
    createObjArgs = {}

#variables for event creation
    eventName = ""
    eventTarget = ""
    evActionType = 1

#args dict for event creation
    createEventArgs = {}

#args for audio import
    INPUT_audioFilePath = "~/Projects/Wwise/WAAPI/AudioFiles"
    INPUT_audioFileList = []
    INPUT_originalsPath = "WAAPI/TestImports"

    importArgs = {}

#Input variables. TO DO: Drive these from data e.g Reaper
    INPUT_ObjectType = "BlendContainer"
    INPUT_ObjectName = "MyCreatedObject"
    OPTION_CreateEvent = True




    def printThis(self,msg):
        print(msg)

    def onJoin(self, details):
        try:
            res = yield from self.call(WAAPI_URI.ak_wwise_core_getinfo)  # RPC call without arguments
        except Exception as ex:
            print("call error: {}".format(ex))
        else:
            # Call was successful, displaying information from the payload.
            print("Hello {} {}".format(res.kwresults['displayName'], res.kwresults['version']['displayName']))

        MyComponent.printThis(self,"Test")


        def askUserForImportDirectory():
            root = tkinter.Tk()
            root.withdraw()
            root.update()
            MyComponent.INPUT_audioFilePath = filedialog.askdirectory(title="Choose source directory")
            root.update()
            root.destroy()
            print(MyComponent.INPUT_audioFilePath)


        def setupSubscriptions():
            # Subscribe to ak.wwise.core.object.created
            # Calls on_object_created whenever the event is received
            self.subscribe(onParentSelected, WAAPI_URI.ak_wwise_ui_selectionchanged)

            objCreateSubArgs = {
                "options": {
                    "return": ["type", "name", "category", "id", "path"]
                }
            }
            self.subscribe(onObjectCreated, WAAPI_URI.ak_wwise_core_object_created, **objCreateSubArgs)

        def ResetGates():
            MyComponent.parentSelected = False
            MyComponent.objectCreated = False
            MyComponent.eventCreated = False

        def onSelectionChanged(objects):
            print("Selection changed")

        def onParentSelected(objects):
            # subscribe to selection change?
            if not MyComponent.parentSelected:
                print("Method to get the parent to create new object under")
                success = False
                parID = None
                MyComponent.parentObject = objects[0]
                #getSelectedObject()
                print("Selected object is...")

                if MyComponent.parentObject != None:
                    success = True
                    print("Selected object name is...{}".format(MyComponent.parentObject[u"name"]))
                    parID = str(MyComponent.parentObject["id"])
                    MyComponent.parentSelected = True

                if success:
                    setupCreateArgs(parID, MyComponent.INPUT_ObjectType, MyComponent.INPUT_ObjectName) # include optional arguments for type/name/conflict
                    yield from createWwiseObject(MyComponent.createObjArgs)
                    print(MyComponent.Results)
                    MyComponent.objectCreated = True
                else:
                    print("Something went wrong!!")
                    return

                #import audio
                setupAudioFilePath()
                importParent = MyComponent.Results.kwresults['id']
                setupImportArgs(importParent, MyComponent.INPUT_audioFileList,MyComponent.INPUT_originalsPath)
                yield from importAudioFiles(MyComponent.importArgs)

                #Setup an event to play the created object
                if MyComponent.OPTION_CreateEvent:
                    evName = MyComponent.Results.kwresults["name"]
                    evTarget = str(MyComponent.Results.kwresults["id"])
                    setupEventArgs(evName, evTarget)
                    yield from createWwiseObject(MyComponent.createEventArgs)
                    print(MyComponent.Results)
                    MyComponent.eventCreated = True

                saveWwiseProject()

                self.leave()

        def saveWwiseProject():
            yield from self.call(WAAPI_URI.ak_wwise_core_project_save)

        def setupEventArgs(oname,otarget,oactionType = 1):
            print("setting up event")

            MyComponent.eventName = oname
            MyComponent.eventTarget = otarget
            MyComponent.evActionType = oactionType

            MyComponent.createEventArgs = {

                "parent": "\\Events\\Default Work Unit",
                "type": "Folder",
                "name": "WAAPI Auto Events",
                "onNameConflict": "merge",
                "children": [
                    {
                        "type": "Event",
                        "name": "Play_" + MyComponent.eventName,
                        "children": [
                            {
                                "name": "",
                                "type": "Action",
                                "@ActionType": MyComponent.evActionType,
                                "@Target": MyComponent.eventTarget
                            }
                        ]
                    }
                ]
            }

        def setupCreateArgs(parentID ,otype = "BlendContainer", oname = "AutoCreatedObject", conflict = "merge"):
            #check the inputs
            if otype == "":
                MyComponent.objType = "BlendContainer"
                print("Defaulting type to Blend Container")
            else:
                MyComponent.objType = otype
            if oname == "":
                MyComponent.objName = "AutoCreatedObject"
                print("Defaulting name to AutoCreatedObject")
            else:
                MyComponent.objName = oname


            MyComponent.objParID = parentID
            MyComponent.nameConflict = conflict

            MyComponent.createObjArgs = {

                "parent": MyComponent.objParID,
                "type": MyComponent.objType,
                "name": MyComponent.objName,
                "onNameConflict": MyComponent.nameConflict,
                "notes": MyComponent.objNotes

            }

        def setupAudioFilePath():
            print("Setting up audio file path")
            pathToFiles = os.path.expanduser(MyComponent.INPUT_audioFilePath)
            setupAudioFileList(pathToFiles)

        def setupAudioFileList(path):
            print("Setting up list of audio files")

            filelist = []
            pattern = '*.wav'
            for root, dirs, files in os.walk(path):
                # for file in os.listdir(path):
                for filename in fnmatch.filter(files, pattern):
                    absFilePath = os.path.abspath(os.path.join(root, filename))
                    filelist.append(absFilePath)

            MyComponent.INPUT_audioFileList = filelist

        def setupImportArgs(parentID, fileList,originalsPath):
            print ("Args for audio importing")
            ParentID = str(parentID)
            importFilelist = []
            for audiofile in fileList:
                foo = audiofile.rsplit('.') #remove extension from filename
                audiofilename = foo[0]
                importFilelist.append(
                    {
                        "audioFile": audiofile,
                        "objectPath": "<Sound SFX>"+os.path.basename(audiofilename)
                    }
                )

            MyComponent.importArgs = {
                "importOperation": "useExisting",
                "default": {
                    "importLanguage": "SFX",
                    "importLocation": ParentID,
                    "originalsSubFolder": originalsPath
                    },
                "imports": importFilelist

                }
            print (MyComponent.importArgs)

        def getSelectedObject():
            try:
                x = yield from self.call(WAAPI_URI.ak_wwise_ui_getselectedobjects)
            except Exception as ex:
                print("call error: {}".format(ex))
            #print (x)
            MyComponent.Results = x

        def createWwiseObject(args):
            try:
                res = yield from self.call(WAAPI_URI.ak_wwise_core_object_create, {}, **args)
            except Exception as ex:
                print("call error: {}".format(ex))
            MyComponent.Results = res

        def importAudioFiles(args):
            try:
                res = yield from self.call(WAAPI_URI.ak_wwise_core_audio_import, {}, **args)
            except Exception as ex:
                print("call error: {}".format(ex))
            #MyComponent.Results = res

        def onObjectCreated(**kwargs):
            if not MyComponent.eventCreated:
                print("Object was created")
                print(kwargs)
                ob = kwargs["object"]
                obID = ob["id"]
                arguments = {
                    "from": {"id": [obID]},
                    "options": {
                        "return": ["type", "name", "category","id","path"]
                    }
                }
                try:
                    res2 = yield from self.call(WAAPI_URI.ak_wwise_core_object_get, **arguments)
                except Exception as ex:
                    print("call error: {}".format(ex))
                else:
                    print(res2.kwresults)

        askUserForImportDirectory()

        setupSubscriptions()

        #yield setupAudioFilePath()

        print("This is the name of the script", sys.argv[0])
        print("This is the number of arguments", len(sys.argv))
        print("The arguments are...", str(sys.argv))



        print("This script will auto create wwise objects and events...")
        print("...Select an object to be the parent in the Project Explorer")





    def onDisconnect(self):
        print("The client was disconnected.")

        asyncio.get_event_loop().stop()


if __name__ == '__main__':
    runner = ApplicationRunner(url=u"ws://127.0.0.1:8095/waapi", realm=u"realm1")
    try:
        runner.run(MyComponent)
    except Exception as e:
        print(type(e).__name__ + ": Is Wwise running and Wwise Authoring API enabled?")
