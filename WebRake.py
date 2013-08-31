#!/usr/bin/python
# Runs the web server and the job manager
import Globals
import Jobs
import routes

def run():
    Globals.init()
    Jobs.init()
    routes.app.run(host='0.0.0.0', port=9000, debug=True, use_reloader=False, use_debugger=True)
    Globals.Log.info("Shut down web server")
    Globals.Log.info("Exiting...")
