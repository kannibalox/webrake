Features
========
* Queueing of jobs
  * For certain parameters, queueing multiple jobs at once
* Automatic screenshots
* Allows passing in of arbitrary HandBrake arguments

Dependencies
============
* Python 3.7+
  * flask
* HandbrakeCLI (tested with v1.2.1)
* mpv (tested with v0.27.2)

Installation
============
```
git clone https://github.com/kannibalox/webrake.git
cd webrake
```
Copy Webrake.example.cfg to Webrake.cfg and make the necessary changes.
To run, execute the command `python WebRake.py`

TODO
====
* Canceling jobs (killing the HandBrakeCLI process is the current workaround)
* Better interface
