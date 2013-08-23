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
  return render_template('index.html', jobs=items)

@app.route('/start')
def new():
  copy_id = request.args.get('copy')
  if copy_id is None:
    copy_id = 0
  return render_template('start.html', copyJob=copy_id)

@app.route('/launch', methods=['POST'])
def launch():
  hbo = HandBrakeCLI.HandBrakeOptions()
  hbo.setDefaults()
  arguments = dict(request.form)
  # The only way to iron out a minor bug
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

@app.route('/job/<int:job_id>')
def jobShow(job_id):
  jobInfo = Globals.db.query('SELECT * FROM job WHERE ID=(?)', (job_id,), True)
  job = {}
  job['args'] = json.loads(jobInfo['arguments'])
  for argument in job['args'].keys():
    if job['args'][argument] is None or not job['args'][argument]:
      del job['args'][argument]
  job['id'] = job_id
  job['status'] = jobInfo['status']
  static_dir = 'static/jobs/' + str(job_id)
  images = glob.glob(static_dir + '/*.png');
  output = glob.glob(static_dir + '/*.mkv');
  return render_template('job.html', images=images, output=output, job=job)

@app.route('/job/<int:job_id>/json')
def jobJSON(job_id):
  job = {}
  if job_id == 0:
    # Zero gets the default
    hbo = HandBrakeCLI.HandBrakeOptions()
    hbo.setDefaults()
    job['args'] = hbo.__dict__
  else:
    jobInfo = Globals.db.query('SELECT * FROM job WHERE ID=(?)', (job_id,), True)
    job = {}
    job['args'] = json.loads(jobInfo['arguments'])
    job['status'] = jobInfo['status']
    static_dir = 'static/jobs/' + str(job_id)
    images = glob.glob(static_dir + '/*.png');
    job['images'] = images
    output = glob.glob(static_dir + '/*.mkv');
    job['output'] = output
  for argument in job['args'].keys():
    if job['args'][argument] is None or not job['args'][argument]:
      del job['args'][argument]
  job['id'] = job_id
  return jsonify(job)

@app.route('/kill')
def kill():
  Jobs.Manager.actionQueue.put("interrupt")
  return "uhh"
  
@app.route('/shutdown', methods=['POST'])
def shutdown():
  shutdown_server()
  return 'Server shutting down...'

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=9000, debug=True, use_reloader=False, use_debugger=True)
