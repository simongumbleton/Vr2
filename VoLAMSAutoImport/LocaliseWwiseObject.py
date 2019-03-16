#!/usr/bin/env python3
import os
import sys
sys.path.append('..')

import asyncio


import fnmatch

#from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from wamp import ApplicationSession, ApplicationRunner
from ak_autobahn import AkComponent


from waapi_SG import WAAPI_URI

class MyComponent(AkComponent):

# this script allows auto importing of new VO files, creating associated events.
# It takes a string input (section name) to construct the path to the files and the import path in wwise
# It creates a list of exisiting sound objects underneath the selected import parent
# It imports any NEW audio files, leaving exisiting structures intact
# It also creates events for any new audio files imported

# When this script runs, it will look up in the folder tree for a common ancestor folder with the Wwise project.
# It uses the stepsUpToCommonDirectory variable to walk up the tree.



#args for audio import
    ImportAudioFilePath = ""    #full path to root folder for files to import

    INPUT_SectionName = "Actor-Mixer Hierarchy"      #the section name, from BAT file. Use to find actor mixer and events parent for importing

    WwiseParentObject = ""

    DefaultLanguage = "English(UK)"

    ImportLanguages = ["French","German","Japanese"] #Default language for Wwise projects, Or SFX

    Results = {}

    LocaliseSelectedObject = False

    pathToOriginalsFromProjectRoot = ["Originals","Voices", DefaultLanguage] # Where are the English VO files

    stepsUpToCommonDirectory = 2    # How many folders up from the script is the shared dir with wwise project

    DirOfWwiseProjectRoot = ["Waapi_File_Importer","Wwise_Project","WAAPI_Test"] ## Name/path of wwise project relative to the common directory

    WwiseProjectPath = ""

    ImportAudioFileList = []

    WwiseQueryResults = []
    ExistingWwiseAudio = []

    OPTION_IsStreaming = True

    isError = False

    DefaultOriginalsPathForNewFiles = "WAAPI/TestImports"  ##TODO Variable this based on import language/SFX

#store a ref to the selected parent object
    parentObject = None
    parentObjectPath = ""
    parentID = ""

#dic to store return/results from yield calls
    Results = {}

    ImportOperationSuccess = False

#args for importing
    importArgs = {}

    def onJoin(self, details):  # onJoin called by WAAPI when the asyncIO process is run (script is run)

###### MyComponent Helper Function Definitions #######
        def beginUndoGroup():
            self.call(WAAPI_URI.ak_wwise_core_undo_begingroup)

        def cancelUndoGroup():
            self.call(WAAPI_URI.ak_wwise_core_undo_cancelgroup)

        def endUndoGroup():
            undoArgs = {"displayName": "Script Auto Importer"}
            self.call(WAAPI_URI.ak_wwise_core_undo_endgroup, {}, **undoArgs)

        def saveWwiseProject():
            self.call(WAAPI_URI.ak_wwise_core_project_save)

        def exit():
            self.leave()

        def printProgress(progress,total):
            fill = '█'
            percent = ("{0:." + str(1) + "f}").format(100 * (progress / float(total)))
            filledLength = int(100 * progress // total)
            bar = fill * filledLength + '-' * (100 - filledLength)
            sys.stdout.write('\r%s |%s| %s%% %s' % ("",bar, percent,""))
            sys.stdout.write('\033[F')
            sys.stdout.flush()
            #sys.stdout.write("\r")
            #print('\r%s |%s| %s%% %s' % ("",bar, percent,""), end="", flush=True)
            if progress == total:
                print("")


        def setupBatchFileSysArgs():
            print("Importing localised files into.. "+sys.argv[1])  # Import section name
            MyComponent.INPUT_SectionName = str(sys.argv[1])
            MyComponent.LocaliseSelectedObject = False
            print("args setup")

        def walk_up_folder(path, depth):
            _cur_depth = 0
            while _cur_depth < depth:
                path = os.path.dirname(path)
                _cur_depth += 1
            return path

###### MyComponent Importer Function Definitions #######
        def getSelectedWwiseObject():
            try:
                res = yield from self.call(WAAPI_URI.ak_wwise_ui_getselectedobjects)
            except Exception as ex:
                print("call error: {}".format(ex))
            else:
                MyComponent.WwiseParentObject = res.kwresults["objects"][0]

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


        def getLanguages():
            arguments = {
                "from": {"ofType": ["Language"]},
                "options": {
                    "return": ["name"]
                }
            }
            try:
                res = yield from self.call(WAAPI_URI.ak_wwise_core_object_get, **arguments)
            except Exception as ex:
                print("call error: {}".format(ex))
                cancelUndoGroup()
            else:
                MyComponent.ImportLanguages.clear()
                for lang in res.kwresults["return"]:
                    if lang['name'] != 'SFX' and lang['name'] != 'External' and lang['name'] != 'Mixed':
                        MyComponent.ImportLanguages.append(lang['name'])

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
                MyComponent.DefaultLanguage = res.kwresults["return"][0]['@DefaultLanguage']
                MyComponent.ImportLanguages.remove(MyComponent.DefaultLanguage)
            #print("Got languages")

        def getExistingAudioInWwise(object):
            #print("Get a list of the audio files currently in the project, under the selected object")
            arguments = {
                "from": {"id": [object]},
                "transform":[
                    {"select":["descendants"]},
                    {"where": ['type:isIn', ['Sound']]},
                ],
                "options": {
                    "return": ["type","id", "name", "path", "sound:originalWavFilePath","@IsVoice"]
                }
            }
            try:
                res = yield from self.call(WAAPI_URI.ak_wwise_core_object_get, **arguments)
            except Exception as ex:
                print("call error: {}".format(ex))
                cancelUndoGroup()
            else:
                MyComponent.WwiseQueryResults = res.kwresults["return"]

        def createExistingAudioList(WwiseQueryResults):
            #print("creating a list of existing wwise sounds")
            list = {}
            for i in WwiseQueryResults:
                if i["type"] == "Sound" and i["@IsVoice"] == True:
                    soundName = str(i["name"])
                    list[soundName] = i
                    MyComponent.ExistingWwiseAudio.append(i)

        def setupImportArgs(path,id, wavFile,language):
            importFilelist=[]
            importFilelist.append(
                {
                    "audioFile": wavFile,
                    "objectPath":path,
                    "objectType":"Sound"
                }
            )
            MyComponent.importArgs = {
                "importOperation": "useExisting",
                "default": {
                    "importLanguage": language,
                    "importLocation": id,
                    },
                "imports": importFilelist,
                #"autoAddToSourceControl":False  #not yet supported
                }

        def importAudioFiles(args):
            language = args['default']['importLanguage']
            try:
                yield from self.call(WAAPI_URI.ak_wwise_core_audio_import, {}, **args)
            except Exception as ex:
                fileError = os.path.basename(args['imports'][0]['audioFile'])
                MyComponent.Results[language]["fails"].append(fileError)
            else:
                MyComponent.Results[language]["imports"] += 1

        def SetupImportParentObject(objectName):
            # Setting up the import parent object
            if MyComponent.LocaliseSelectedObject:
                arguments = {
                    "from": {"id": [objectName]},
                    "options": {
                        "return": ["id", "type", "name", "path", "filePath", "workunit:type"]
                    }
                }
            else:
                arguments = {
                    "from": {"path": ["\Actor-Mixer Hierarchy"]},
                    "transform": [
                        {"select": ['descendants']},
                        {"where": ["name:matches", "^" + objectName + "$"]},
                        {"where": ['type:isIn', ['WorkUnit']]}
                    ],
                    "options": {
                        "return": ["id", "type", "name", "path", "filePath", "workunit:type"]
                    }
                }
                if objectName == 'Actor-Mixer Hierarchy':
                    arguments["transform"] = [{"where": ["name:matches", objectName]}]
            try:
                res = yield from self.call(WAAPI_URI.ak_wwise_core_object_get, **arguments)
            except Exception as ex:
                print("call error: {}".format(ex))
                cancelUndoGroup()
            else:
                ID = ""
                obj = ""
                path = ""
                matches = 0
                for x in res.kwresults["return"]:
                        matches += 1
                        ID = str(x["id"])
                        obj = x
                        path = str(x["path"])

                if matches > 1:
                    print("WARNING....More than 1 match found for import parent. Check import results..")

                MyComponent.parentObject = obj
                MyComponent.parentObjectPath = path
                MyComponent.parentID = ID
                print("Localising audio underneath "+path)

        def ImportIntoWwiseUnderParentObject(parentObjectID):
            #print("Method to get the parent to create new object under")
            success = False
            parID = parentObjectID
            if parID != None:
                success = True
            if success:
                yield from getExistingAudioInWwise(str(parID))
                createExistingAudioList(MyComponent.WwiseQueryResults)
                if len(MyComponent.ExistingWwiseAudio)==0:
                    print("List of Existing Wwise Voices is Empty...")
                    print("Unable to localise into selected wwise object...")
                    print("...Exiting...")
                    return
                for language in MyComponent.ImportLanguages:
                    MyComponent.Results[language] = {"fails": [], "imports": 0}
                count = 0
                for file in MyComponent.ExistingWwiseAudio:
                    path = file['path']  # MyComponent.ExistingWwiseAudio[file]['path']
                    id = file['id']  # MyComponent.ExistingWwiseAudio[file]['id']
                    name = file['name']  # MyComponent.ExistingWwiseAudio[file]['name']
                    if "sound:originalWavFilePath" in file:
                        originalWavpath = file["sound:originalWavFilePath"].replace('\\', '/').replace("Y:", "~")
                        originalWavpath = os.path.normpath(os.path.expanduser(originalWavpath))
                        for language in MyComponent.ImportLanguages:
                         #(path, filename, fileList, language)
                            languageWav = os.path.normpath(originalWavpath.replace(MyComponent.DefaultLanguage,language))
                            setupImportArgs(path, id, str(languageWav) ,language)
                            yield from importAudioFiles(MyComponent.importArgs)
                        count += 1
                    else:
                        print("sound:originalWavFilePath NOT in file")
                    printProgress(count,len(MyComponent.ExistingWwiseAudio))
                MyComponent.ImportOperationSuccess = True
            else:
                print("Something went wrong!!")
                MyComponent.ImportOperationSuccess = False
                return
            if (MyComponent.ImportOperationSuccess):
                saveWwiseProject()
                endUndoGroup()
                print("")
                print("Import operation success.......Results......")#+str(count)+" new files imported.")
                for lang in MyComponent.Results:
                    print("")
                    print("_____"+lang+"______")
                    print("Successful Imports = "+str(MyComponent.Results[lang]["imports"]))
                    if len(MyComponent.Results[lang]["fails"]) > 0:
                        print("Fails = "+str(len(MyComponent.Results[lang]["fails"])))
                        for fail in MyComponent.Results[lang]["fails"]:
                            print(str(fail))
                print("")
            else:
                print("Import operation failed! Check log for errors!")
                endUndoGroup()

###################  Main script flow  ###################
        #### Establish Wwise connection
        try:
            res = yield from self.call(WAAPI_URI.ak_wwise_core_getinfo)  # RPC call without arguments
        except Exception as ex:
            print("call error: {}".format(ex))
        else:
            # Call was successful, displaying information from the payload.
            print("Hello {} {}".format(res.kwresults['displayName'], res.kwresults['version']['displayName']))
            print("")


        #### If the sys args are longer than the default 1 (script name)
        if (len(sys.argv) > 1):
            setupBatchFileSysArgs()
        else:
            MyComponent.LocaliseSelectedObject = True
            print("No arguments given, using currently selected object")

        beginUndoGroup()

        yield from getLanguages()

        yield from getProject()

        if MyComponent.LocaliseSelectedObject:
            yield from getSelectedWwiseObject()
            ## Get the Section work unit object and store ID and path
            yield from SetupImportParentObject(MyComponent.WwiseParentObject['id'])
        else:
            ## Get the Section work unit object and store ID and path
            yield from SetupImportParentObject(MyComponent.INPUT_SectionName)

        if MyComponent.isError:
            exit()
        else:
            print("")
            print("...working...")

        ## Main import function - Takes the ID of an object, to import files under.
        ## This method calls several other methods as it executes
            yield from ImportIntoWwiseUnderParentObject(MyComponent.parentID)

            exit()



    def onDisconnect(self):
        print("The client was disconnected.")

        asyncio.get_event_loop().stop()


if __name__ == '__main__':

    #
    # transportOptions = {
    #     "maxFramePayloadSize": 0,
    #     "maxMessagePayloadSize": 0,
    #     "autoFragmentSize": 0,
    #     "failByDrop": False,
    #     "openHandshakeTimeout": 0,
    #     "closeHandshakeTimeout": 0,
    #     "tcpNoDelay": True,
    #     "autoPingInterval": 0,
    #     "autoPingTimeout": 0,
    #     "autoPingSize": 4,
    # }

    runner = ApplicationRunner(url=u"ws://127.0.0.1:8095/waapi", realm=u"realm1")
    try:
        runner.run(MyComponent)
    except Exception as e:
        print(type(e).__name__ + ": Is Wwise running and Wwise Authoring API enabled?")
