# -*- coding: utf-8 -*-

"""
This module provides functions used for aws service.
"""


from cloud import common
import subprocess
import json
from string import Template
from base64 import encodestring


def startInstance(name, config):
    """
    Run the aws command to start a worker instance.
    Return the created instanceid in case of dedicated ec2 instance or the spotinstancerequestid
    in case of a spot instance.
    """

    if config.get("worker", "spot"):
        cmd = ["aws", "ec2", "request-spot-instances",
                "--spot-price", config.get("spot", "spotprice"),
                "--instance-count", config.get("spot", "instancecount"),
                "--type", config.get("spot", "type"),
                "--launch-specification", _getLaunchSpecification(name, config),]
    else:
        cmd = ["aws", "ec2", "run-instances",
                "--key-name", config.get("authentication", "keyname"),
                "--image-id", config.get("worker", "imageid"),
                "--instance-type", config.get("worker", "instancetype"),
                "--subnet-id", config.get("worker", "subnetid"),
                "--security-group-ids",
                    config.get("worker", "securitygroupid"),
                "--iam-instance-profile",
                    "Arn=%s" % config.get("worker", "iaminstanceprofile"),
                "--user-data", _getUserData(name, config),]
    common._run_or_none(cmd)


def stopInstance(name, config):
    """Run the aws command to terminate the instance."""
    cmd = ["aws", "ec2", "terminate-instances", "--instance-ids",
            _getInstanceIdByName(name)]
    common._run_or_none(cmd)


def _getLaunchSpecification(name, config):
    with open("cloud/aws_worker_spot_launchspecification.json.template", 'r') as f:
        template = Template(f.read())
        values = {
            "image_id": config.get("worker", "imageid"),
            "keyname": config.get("authentication", "keyname"),
            "security_group_id": config.get("worker", "securitygroupid"),
            "instance_type": config.get("worker", "instancetype"),
            "user_data": encodestring(_getUserData(name, config)), }
        return template.substitute(values).replace('\n', '')


def _getUserData(name, config):
    """
    Prepare the user-data script in cloud-init syntax.
    Return the script as a string.
    """

    with open("cloud/aws_worker_cloud_init.template", 'r') as f:
        template = Template(f.read())
        values = {
            "hostname": name,
            "region": config.get("authentication", "region"),
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


def _getInstanceIdByName(name):
    """Return instanceid from name."""
    cmd = ["aws", "ec2", "describe-instances"]
    output = common._check_output_or_none(cmd)
    if output:
        for resources in json.loads(output)["Reservations"]:
            instance = resources["Instances"][0]
            if instance.has_key("Tags"):
                for tags in instance["Tags"]:
                    if tags["Key"] == "Name" and tags["Value"] == name:
                        return instance["InstanceId"]
    return None

# vim: tabstop=4 noexpandtab shiftwidth=4 softtabstop=4 textwidth=79

