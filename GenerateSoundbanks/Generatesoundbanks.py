import sys
import os

import asyncio
from autobahn.asyncio.component import run
import autobahn.asyncio.wamp

sys.path.append('..')

from ak_autobahn import AkComponent
from MyWwiseComponent import myWaapiComponent
from waapi import WAAPI_URI


class MyComponent(AkComponent):

    WwiseParentObject = {}

    def onJoin(self, details):

############# Function definitions #########################################
        def exit():
            self.leave()

        def beginUndoGroup():
            yield from self.call(WAAPI_URI.ak_wwise_core_undo_begingroup)

        def cancelUndoGroup():
            yield from self.call(WAAPI_URI.ak_wwise_core_undo_cancelgroup)

        def endUndoGroup():
            undoArgs = {"displayName": "My Waapi Script"}
            yield from self.call(WAAPI_URI.ak_wwise_core_undo_endgroup, {}, **undoArgs)

        def saveWwiseProject():
            yield from self.call(WAAPI_URI.ak_wwise_core_project_save)

        def getSelectedWwiseObject():
            try:
                res = yield from self.call(WAAPI_URI.ak_wwise_ui_getselectedobjects)
            except Exception as ex:
                print("call error: {}".format(ex))
            else:
                MyComponent.WwiseParentObject = res.kwresults["objects"][0]

        def generatesoundbanks(object):
            print("generating soundbanks")

            args = {
                "command": "GenerateSelectedSoundbanksAllPlatforms",
                "objects": [
                    object
                ]
            }
            yield from self.call(WAAPI_URI.ak_wwise_ui_commands_execute, **args)



############## End of Function definitions ##############################################



############### Main Script logic flow ####################################################
        ## First try to connect to wwise to get Wwise info
        try:
            res = yield from self.call(WAAPI_URI.ak_wwise_core_getinfo)  # RPC call without arguments
        except Exception as ex:
            print("call error: {}".format(ex))
        else:
            # Call was successful, displaying information from the payload.
            print("Hello {} {}".format(res.kwresults['displayName'], res.kwresults['version']['displayName']))



    ###########  Do Some Cool stuff here ##############

        beginUndoGroup()

        yield from getSelectedWwiseObject()

        #yield from generatesoundbanks("{B9F356E2-E334-48AC-8E3B-0E308A24289E}")

        yield from generatesoundbanks(MyComponent.WwiseParentObject['id'])

        ## Doesn't seem to work with name though
        # yield from generatesoundbanks(MyComponent.WwiseParentObject['name'])

        endUndoGroup()


    ############### Exit  #############################
        saveWwiseProject()
        exit()
        #self.leave()


    def onDisconnect(self):
         print("The client was disconnected.")

         asyncio.get_event_loop().stop()


if __name__ == '__main__':
    #runner = ApplicationRunner(url=u"ws://127.0.0.1:8095/waapi", realm=u"realm1")

    newComponent = myWaapiComponent
    newComponent.session_factory = MyComponent

    try:
        #runner.run(MyComponent)
        run([newComponent])
    except Exception as e:
        print(type(e).__name__ + ": Is Wwise running and Wwise Authoring API enabled?")
