from flask import Flask, render_template, flash, Response, request, redirect, url_for, jsonify, Markup, send_from_directory
import Globals
import Config
import Jobs
import HandBrakeCLI

from time import sleep
import json
import glob
import os
import urllib2

app = Flask(__name__)

def frange(start, end=None, inc=1.0):
    "A range function, that does accept float increments..."
    
    if end == None:
        end = start + 0.0
        start = 0.0
        
    L = []
    while 1:
        next = start + len(L) * inc
        if inc > 0 and next > end:
            break
        elif inc < 0 and next < end:
            break
        L.append(next)
    return L

@app.route('/')
@app.route('/queue')
def home():
    num_items = Globals.db.query('select COUNT(*) from job', one=True)['COUNT(*)']
    page = request.args.get('page')
    last_page = num_items/25
    if page is None or page < 0:
        page = 1
    else:
        page = min(int(page), last_page)
    items = Globals.db.query('select * from job where status <> \'Deleted\' order by id desc')[(page-1)*25:page*25]
    for i in items:
        args = json.loads(i['arguments'])
        for attr in args:
            i[attr] = args[attr]
        i['status'] = i['status'].split(':', 1)
    return render_template('index.html', jobs=items, page=page, last_page=last_page)

@app.route('/start')
def new():
    copy_id = request.args.get('copy')
    if copy_id is None:
        copy_id = 0
    x264Presets = "ultrafast/superfast/veryfast/faster/fast/medium/slow/slower/veryslow/placebo".split('/') # I'm a lazy bastard
    return render_template('start.html', copyJob=copy_id, presets=x264Presets, selectorRoot = Config.SelectorRoot)

@app.route('/dirlist', methods=['POST'])
def dirlist():
    dirreq = urllib2.unquote(dict(request.form)['dir'][0])
    r=['<ul class="jqueryFileTree" style="display: none;">']
    try:
        if dirreq.find(Config.SelectorRoot, 0, len(Config.SelectorRoot)) == -1:
            raise PermissionError("Access outside of selector root not allowed")
        r=['<ul class="jqueryFileTree" style="display: none;">']
        d=dirreq
        for f in os.listdir(d):
            ff=os.path.join(d,f)
            if os.path.isdir(ff):
                r.append('<li class="directory collapsed"><a href="#" rel="%s/">%s</a></li>' % (ff,f))
            else:
                e=os.path.splitext(f)[1][1:] # get .ext and remove dot
                r.append('<li class="file ext_%s"><a href="#" rel="%s">%s</a></li>' % (e,ff,f))
        r.append('</ul>')
    except Exception,e:
        r.append('Could not load directory: %s' % str(e))
    r.append('</ul>')
    return ''.join(r)

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
    if arguments['Duration'] == [u'', u'']:
        del(arguments['Duration'])
    for key in arguments.keys():
        if len(arguments[key]) == 1:
            arguments[key] = arguments[key][0]
    for key, value in arguments.items():
        setattr(hbo, key, value)
    if arguments['action'] == "Start Multiple Encodes":
        print arguments['StepVar']
        for v in frange(float(arguments['StartIntv']), float(arguments['EndIntv']), float(arguments['StepIntv'])):
            setattr(hbo, arguments['StepVar'], str(v))
            Jobs.Manager.addJob(hbo)
    else:
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
    static_dir =    os.path.join(Config.JobsDirectory, str(jobID), '')
    images = [os.path.basename(g) for g in glob.glob(os.path.join(static_dir, '*.png'))]
    output = [os.path.basename(g) for g in glob.glob(os.path.join(static_dir, '*.mkv'))]
    log_paths = [os.path.basename(g) for g in glob.glob(os.path.join(static_dir, '*.log'))]
    logs = []
    for l in log_paths:
        with open(os.path.join(static_dir, l)) as log_file:
            log_str = unicode(log_file.read().replace('\n', '<br/>'), errors='ignore')
        logs.append({'path': l, 'text': log_str, 'name': os.path.basename(l), 'ID': os.path.basename(l).replace('.', '_')})
    Globals.Log.debug("Showing job %s (%s arguments, %s images, %s files, %s logs)" % (jobID, len(json.loads(jobInfo['arguments'])), len(images), len(output), len(logs)))
    return render_template('job.html', images=images, output=output, logs=logs, job=job)

@app.route('/job/static/<int:jobID>/<path:filename>')
def jobStatic(jobID, filename):
    if Config.JobsDirectory in filename:
        return send_from_directory(os.path.dirname(filename), os.path.basename(filename))
    return send_from_directory(os.path.join(Config.JobsDirectory, str(jobID)), filename)

@app.route('/multi/compare/<jobs>')
def jobCompare(jobs=None):
    jobData = []
    for j in jobs.split(','):
        jobInfo = {}
        jobInfo['args'] = json.loads(Globals.db.query('SELECT arguments FROM job WHERE ID=(?)', (j,), True)['arguments'])
        static_dir =    os.path.join(Config.JobsDirectory, str(j), '')
        jobInfo['images'] = [os.path.basename(i) for i in glob.glob(static_dir + '/*.png')]
        jobInfo['id'] = j
        jobData.append(jobInfo)
    allKeys = set()
    for j in jobData:
        allKeys = allKeys.union(set(j['args'].keys()))
    showKeys = []
    for k in allKeys:
        val = jobData[0]['args'][k]
        for j in jobData:
            if k not in j['args'] or j['args'][k] != val:
                showKeys.append(k)
                break
    for j in jobData:
        for a in j['args'].keys():
            if not a in showKeys:
                del j['args'][a]

    return render_template('compare.html', jobData=Markup(json.dumps(jobData)))

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
        job['images'] = glob.glob(static_dir + '/*.png')
        job['output'] = glob.glob(static_dir + '/*.mkv')
        job['logs'] = glob.glob(static_dir + '/*.log')
    for argument in job['args'].keys():
        if job['args'][argument] is None or not job['args'][argument]:
            del job['args'][argument]
    job['id'] = jobID
    return jsonify(job)

@app.route('/multi/remove/<jobs>')
def multiJobRemove(jobs=None):
    for j in jobs.split(','):
        Jobs.Manager.removeJob(j)
    return redirect(url_for('home'))

@app.route('/remove/<int:jobID>')
def removeJob(jobID):
    Jobs.Manager.removeJob(jobID)
    return redirect(url_for('home'))

@app.route('/export/<int:jobID>')
def exportJob(jobID):
    Jobs.Manager.exportJob(jobID)
    return redirect(url_for('jobShow', jobID=jobID))

@app.route('/finalize/<int:jobID>')
def finalizeJob(jobID):
    Jobs.Manager.finalizeJob(jobID)
    return redirect(url_for('home'))

@app.route('/purge/<int:jobID>')
def purgeJob(jobID):
    Jobs.Manager.purgeJob(jobID)
    return redirect(url_for('jobShow', jobID=jobID))

@app.route('/stop/<int:jobID>')
def stopJob(jobID):
    Jobs.Manager.stop(jobID)
    return redirect(url_for('jobShow', jobID=jobID))
    
@app.route('/shutdown', methods=['POST'])
def shutdown():
    shutdown_server()
    return 'Server shutting down...'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, debug=True, use_reloader=False, use_debugger=True)
