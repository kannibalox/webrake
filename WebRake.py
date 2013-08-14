#!/usr/bin/python
# Runs the web server and the job manager
import Globals
import Jobs
import routes

Globals.init()
Jobs.startManager()
routes.app.run(host='0.0.0.0', port=9000, debug=True, use_reloader=False, use_debugger=True)
