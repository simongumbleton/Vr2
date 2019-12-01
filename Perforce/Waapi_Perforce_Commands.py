import sys
import os

import asyncio
from autobahn.asyncio.component import run
import autobahn.asyncio.wamp
from ak_autobahn import AkComponent
from MyWwiseComponent import myWaapiComponent
from waapi import WAAPI_URI

sys.path.append('..')


class MyComponent(AkComponent):

    def onJoin(self, details):

        ############# Function definitions #########################################
        def myExit():
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
            args = {
                "return": ["workunit", "id"]
            }
            try:
                res = yield from self.call(WAAPI_URI.ak_wwise_ui_getselectedobjects, options=args)
            except Exception as ex:
                print("call error: {}".format(ex))
            else:
                WwiseObject = res.kwresults["objects"][0]
                print(WwiseObject)
                WorkUnitID = WwiseObject["workunit"]["id"]
                print(WorkUnitID)
                #return WorkUnitID
                return WwiseObject["id"]

        def doPerforceOperation(operation, target):
            # print("Get a list of the audio files currently in the project, under the selected object")
            arguments = {
                "command": operation,
                "objects": [
                    target
                ]
            }
            try:
                res = yield from self.call(WAAPI_URI.ak_wwise_ui_commands_execute, **arguments)
            except Exception as ex:
                print("call error: {}".format(ex))
                return 0
            else:
                print("Checked out WWU")

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

        WorkUnit = yield from getSelectedWwiseObject()

        yield from doPerforceOperation("WorkgroupCheckoutWWU",WorkUnit)

        endUndoGroup()

        ############### Exit  #############################
        saveWwiseProject()
        myExit()
        # self.leave()

    def onDisconnect(self):
        print("The client was disconnected.")

        asyncio.get_event_loop().stop()


if __name__ == '__main__':
    # runner = ApplicationRunner(url=u"ws://127.0.0.1:8095/waapi", realm=u"realm1")

    newComponent = myWaapiComponent
    newComponent.session_factory = MyComponent

    try:
        # runner.run(MyComponent)
        run([newComponent])
    except Exception as e:
        print(type(e).__name__ + ": Is Wwise running and Wwise Authoring API enabled?")
