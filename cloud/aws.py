"""This module provides functions used for aws service."""


from cloud import common
import subprocess
import json
from string import Template


def startInstance(name, config):
	"""
	Run the aws command to start a worker instance.
	Return the created instanceid.
	"""

	cmd = ["aws", "ec2", "run-instances",
			"--key-name", config.get("authentication", "keyname"),
			"--image-id", config.get("worker", "imageid"),
			"--instance-type", config.get("worker", "instancetype"),
			"--subnet-id", config.get("worker", "subnetid"),
			"--security-group-ids",
				config.get("worker", "securitygroupid"),
			"--iam-instance-profile",
				config.get("worker", "iaminstanceprofile"),
			"--user-data", _getUserData(name, config),]
	output = common._run_or_none(cmd)
	if output:
		instanceid = json.loads(output)['Instances'][0]['InstanceId']
		_nameInstance(instanceid, name)		   
		return instanceid
	return None


def _getUserData(name, config):
	"""
	Prepare the user-data script in cloud-init syntax.
	Return the script as a string.
	"""

	with open("cloud/aws_worker_cloud_init.template", 'r') as f:
		template = Template(f.read())
		values = {
			"hostname": name,
			"access_key": config.get("authentication", "accesskey"),
			"secret_access_key":
				config.get("authentication", "secretaccesskey"),
			"bucket_name": config.get("storage", "name"),
			"mount_point": config.get("storage", "mountpoint"),
			"guerilla_render_filename":
				config.get("storage", "guerillarenderfilename"),
			"coalition_filename":
				config.get("storage", "coalitionfilename"),
			"coalition_server_ip": config.get("coalition", "ip"),
			"coalition_server_port": config.get("coalition", "port"),}
	return template.substitute(values)


def _nameInstance(instanceid, name):
	"""Set the instance name via tag."""
	cmd = ["aws", "ec2", "create-tags", "--resources", instanceid,
		"--tags", "Key=Name,Value=%s" % name]
	return common._run_or_none(cmd)


def stopInstance(name):
	"""Run the aws command to terminate the instance."""
	cmd = ["aws", "ec2", "terminate-instances", "--instance-ids",
		_getInstanceIdByName(name)]
	return common._run_or_none(cmd)


def _getInstanceIdByName(name):
	"""Return instanceid from name."""
	cmd = ["aws", "ec2", "describe-instances"]
	output = common._run_or_none(cmd)
	if output:
		for resources in json.loads(output)["Reservations"]:
			instance = resources["Instances"][0]
			if instance.has_key("Tags"):
				for tags in instance["Tags"]:
					if tags["Key"] == "Name" and tags["Value"] == name:
						return instance["InstanceId"]
	return None

