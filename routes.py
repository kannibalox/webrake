from flask import Flask, render_template, flash, Response, request, redirect, url_for, jsonify
from Globals import Log, Manager, db
import HandBrakeCLI
from time import sleep
import simplejson, json
import glob

app = Flask(__name__)
@app.route('/')
@app.route('/queue')
def home():
  items = db.query_db('select * from job order by id desc')
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
  h = HandBrakeCLI.HandBrakeCLI()
  h.Options.setDefaults()
  arguments = dict(request.form)
  for key in arguments.keys():
    if len(arguments[key]) == 1:
      arguments[key] = arguments[key][0]
  for key in arguments:
    setattr(h.Options, key, arguments[key])
  h.Options.isPreview = True
  Manager.addJob(h)
  return redirect(url_for('home'))

@app.route('/job/<int:job_id>')
def jobShow(job_id):
  jobInfo = db.query_db('SELECT * FROM job WHERE ID=(?)', (job_id,), True)
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
  if job_id == 0:
    hbo = HandBakeCLI.HandBrakeOptions()
    hbo.setDefaults()
    return hbo.toJSON()
  jobInfo = db.query_db('SELECT * FROM job WHERE ID=(?)', (job_id,), True)
  job = {}
  job['args'] = json.loads(jobInfo['arguments'])
  for argument in job['args'].keys():
    if job['args'][argument] is None or not job['args'][argument]:
      del job['args'][argument]
  job['id'] = job_id
  job['status'] = jobInfo['status']
  static_dir = 'static/jobs/' + str(job_id)
  images = glob.glob(static_dir + '/*.png');
  job['images'] = images
  output = glob.glob(static_dir + '/*.mkv');
  job['output'] = output
  return jsonify(job)
  

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=9000, debug=True, use_reloader=False, use_debugger=True)
