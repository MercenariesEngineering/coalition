# -*- coding: utf-8 -*-

"""
This module provides functions used for google cloud service.
"""


from cloud import common
import subprocess
import json
from string import Template
import tempfile
from base64 import encodestring


def startInstance(name, config):
	"""
	Run the gcloud command to start a worker instance.
	Return the created FIXME
	"""

	# gcloud command line tool is picky with params escaping (eg. key-id in json)
	# So we use a real temporary file
	startup_script_file = tempfile.NamedTemporaryFile(delete=True)
	startup_script_file.write(_getStartupScript(name, config))
        startup_script_file.flush()

	if config.get("worker", "preemptible") == True:
		cmd = ["aws", "ec2", "request-spot-instances",
				"--spot-price", config.get("spot", "spotprice"),
				"--instance-count", config.get("spot", "instancecount"),
				"--type", config.get("spot", "type"),
				"--launch-specification", _getLaunchSpecification(name, config),]
		output = common._run_or_none(cmd)
		if output:
			requestid = json.loads(output)["SpotInstanceRequests"][0]["SpotInstanceRequestId"]
			return requestid

	else:
		cmd = ["gcloud", "compute", "--project", config.get("authentication", "project"),
				"instances", "create", name,
				"--zone", config.get("worker", "zone"),
				"--machine-type", config.get("worker", "machinetype"),
				"--subnet", config.get("worker", "subnet"),
				"--maintenance-policy", config.get("worker", "maintenancepolicy"),
				"--service-account", config.get("authentication", "serviceaccount"),
				"--scopes", config.get("authentication", "scopes"),
				"--image", config.get("worker", "image"),
				"--image-project", config.get("worker", "imageproject"),
				"--boot-disk-size", config.get("worker", "bootdisksize"),
				"--boot-disk-type", config.get("worker", "bootdisktype"),
				"--boot-disk-device-name", name,
				"--metadata-from-file", "startup-script={}".format(startup_script_file.name),]
		output = common._run_or_none(cmd)
		# Delete the file after use
		startup_script_file.close()
		if output:
			for line in output.split('\n'):
				if line.startswith('Created'):
					instanceid = (line.split('/')[10].strip('].'))
			return instanceid

	return None


def stopInstance(name, config):
	"""Run the gcloud command to terminate the instance."""
    zone = config.get("worker", "zone")
	cmd = ["glcoud", "compute", "instances", "delete", "--quiet", "--zone", zone, name]
	return common._run_or_none(cmd)


def _getStartupScript(name, config):
	"""
	Prepare the startup-script in bash script syntax.
	Return the script as a string.
	"""

	with open(config.get("authentication", "keyfile"), 'r') as f:
		key_id_data = f.read()

	with open("cloud/gcloud_worker_startup_script.template", 'r') as f:
		template = Template(f.read())
		values = {
			"key_id_json": key_id_data,
			"hostname": name,
			"mount_point": config.get("storage", "mountpoint"),
			"bucket_name": config.get("storage", "name"),
            "install_dir": config.get("worker", "installdir"),
			"coalition_package": config.get("storage", "coalitionpackage"),
			"main_program_package": config.get("main_program", "package"),
			"main_program_environment": config.get("main_program", "environment"),
			"coalition_server_ip": config.get("coalition", "ip"),
			"coalition_server_port": config.get("coalition", "port"),}
	return template.substitute(values)

# vim: tabstop=4 noexpandtab shiftwidth=4 softtabstop=4 textwidth=79

