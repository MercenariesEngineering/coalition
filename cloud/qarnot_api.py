# -*- coding: utf-8 -*-

"""
This module provides functions used for qarnot cloud service.
"""

from cloud import common
import qarnot
import subprocess
import tempfile
from string import Template
from multiprocessing import Process
import os


def startInstance(name, config):
    """Use qarnot API to start a worker instance. Instances are started by task creation."""
    startup_script_file = tempfile.NamedTemporaryFile(delete=True)
    startup_script_file.write(_getStartupScript(name, config))
    startup_script_file.flush()
    os.fsync(startup_script_file.fileno())
    startup_script_file.seek(0)

    connection = qarnot.connection.Connection("cloud_qarnot.ini")
    # We need internet access and start one instance at time
    task = connection.create_task(name, 'docker-network', 1)
    task.constants["DOCKER_REPO"] = config.get("worker", "docker_repo")
    task.constants["DOCKER_TAG"] = config.get("worker", "docker_tag")
    task.constants["DOCKER_HOST"] = common.createWorkerInstanceName(config.get("worker", "nameprefix"))
    task.constants["DOCKER_CMD"] = startup_script_file.read()
    p = Process(target=task.run)
    p.start()

def stopInstance(name, config):
    """Use qarnot API to terminate the instance."""

    connection = qarnot.connection.Connection("cloud_qarnot.ini")
    tasks = connection.tasks()
    task = [t for t in tasks if t.name == name][0]
    task.delete()

def _getStartupScript(name, config):
    """Build the workers startup script."""

    with open(config.get("authentication", "keyfile"), 'r') as f:
        key_id_data = f.read()

    with open("cloud/qarnot_worker_startup_script.template", 'r') as f:
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

