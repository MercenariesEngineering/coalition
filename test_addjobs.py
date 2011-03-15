import os

nbP = 20	# nb parents
nbC = 10	# nb children

for p in range(0,nbP):
	pipe = os.popen ('python control.py -c "" -t "Parent job' + str(p) + '" http://127.0.0.1:19211 add')
	parent = int(pipe.read ())

	for c in range(0,nbC):
		pipe = os.popen ('python control.py -c "python job.py" -t "Job ' + str(c) + '" -P ' + str(parent) + ' http://127.0.0.1:19211 add')
		child = int(pipe.read ())
