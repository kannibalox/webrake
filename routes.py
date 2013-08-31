from flask import Flask, render_template, flash, Response, request, redirect, url_for, jsonify
import Globals
import Jobs
import HandBrakeCLI
from time import sleep
import simplejson, json
import glob

app = Flask(__name__)
@app.route('/')
@app.route('/queue')
def home():
  items = Globals.db.query('select * from job order by id desc')
  for i in items:
    args = json.loads(i['arguments'])
    for attr in args:
      i[attr] = args[attr]
    i['status'] = '<br />\n'.join(i['status'].split(':'))
  return render_template('index.html', jobs=items)

@app.route('/start')
def new():
  copy_id = request.args.get('copy')
  if copy_id is None:
    copy_id = 0
  x264Presets = "ultrafast/superfast/veryfast/faster/fast/medium/slow/slower/veryslow/placebo".split('/') # I'm a lazy bastard
  return render_template('start.html', copyJob=copy_id, presets=x264Presets)

@app.route('/launch', methods=['POST'])
def launch():
  hbo = HandBrakeCLI.HandBrakeOptions()
  hbo.setDefaults()

  arguments = dict(request.form)
  # Iron out a few quirks
  if not 'isPreview' in arguments:
    arguments['isPreview'] = [False]
  if arguments['Crop'] == [u'', u'', u'', u'']:
    del(arguments['Crop'])

  for key in arguments.keys():
    if len(arguments[key]) == 1:
      arguments[key] = arguments[key][0]
  for key in arguments:
    setattr(hbo, key, arguments[key])

  Jobs.Manager.addJob(hbo)
  return redirect(url_for('home'))

@app.route('/job/<int:jobID>')
def jobShow(jobID):
  jobInfo = Globals.db.query('SELECT * FROM job WHERE ID=(?)', (jobID,), True)
  job = {}
  job['args'] = json.loads(jobInfo['arguments'])
  for argument in job['args'].keys():
    if job['args'][argument] is None or not job['args'][argument]:
      del job['args'][argument]
  job['id'] = jobID
  job['status'] = jobInfo['status']
  static_dir = 'static/jobs/' + str(jobID)
  images = glob.glob(static_dir + '/*.png');
  output = glob.glob(static_dir + '/*.mkv');
  return render_template('job.html', images=images, output=output, job=job)

@app.route('/job/<int:jobID>/json')
def jobJSON(jobID):
  job = {}
  if jobID == 0:
    # Zero gets the default
    hbo = HandBrakeCLI.HandBrakeOptions()
    hbo.setDefaults()
    job['args'] = hbo.__dict__
  else:
    jobInfo = Globals.db.query('SELECT * FROM job WHERE ID=(?)', (jobID,), True)
    job = {}
    job['args'] = json.loads(jobInfo['arguments'])
    job['status'] = jobInfo['status']
    static_dir = 'static/jobs/' + str(jobID)
    images = glob.glob(static_dir + '/*.png');
    job['images'] = images
    output = glob.glob(static_dir + '/*.mkv');
    job['output'] = output
  for argument in job['args'].keys():
    if job['args'][argument] is None or not job['args'][argument]:
      del job['args'][argument]
  job['id'] = jobID
  return jsonify(job)

@app.route('/delete/<int:jobID>')
def deleteJob(jobID):
  Jobs.Manager.action("delete", jobID)

@app.route('/purge/<int:jobID>')
def purgeJob(jobID):
  Jobs.Manager.purgeJob(jobID)
  return redirect(url_for('jobShow', jobID=jobID))

@app.route('/stop/<int:jobID>')
def stopJob(jobID):
  Jobs.Manager.action("stop", jobID)
  return "uhh"
  
@app.route('/shutdown', methods=['POST'])
def shutdown():
  shutdown_server()
  return 'Server shutting down...'

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=9000, debug=True, use_reloader=False, use_debugger=True)
