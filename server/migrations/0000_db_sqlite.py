# -*- coding: utf-8 -*-

# Initial database setup

steps = [
"""
CREATE TABLE IF NOT EXISTS WorkerAffinities(
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	worker_name TEXT,
	affinity BIGINT DEFAULT 0,
	ordering INT DEFAULT 0)
""",
"""
CREATE INDEX IF NOT EXISTS worker_name_index ON WorkerAffinities(worker_name)
""",
"""
CREATE TABLE IF NOT EXISTS Jobs(
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	parent INT DEFAULT 0,
	title TEXT DEFAULT "",
	command TEXT DEFAULT "",
	dir TEXT DEFAULT ".",
	environment TEXT DEFAULT "",
	state TEXT DEFAULT "WAITING",
	paused BOOLEAN DEFAULT 0,
	worker TEXT DEFAULT "",
	start_time INT DEFAULT 0,
	duration INT DEFAULT 0,
	run_done INT DEFAULT 0,
	timeout INT DEFAULT 0,
	priority UNSIGNED INT DEFAULT 8,
	affinity TEXT DEFAULT "",
	affinity_bits BIGINT DEFAULT 0,
	user TEXT DEFAULT "",
	finished INT DEFAULT 0,
	errors INT DEFAULT 0,
	working INT DEFAULT 0,
	total INT DEFAULT 0,
	total_finished INT DEFAULT 0,
	total_errors INT DEFAULT 0,
	total_working INT DEFAULT 0,
	url TEXT DEFAULT "",
	progress FLOAT,
	progress_pattern TEXT DEFAULT "",
	h_affinity BIGINT DEFAULT 0,
	h_priority UNSIGNED BIGINT DEFAULT 0,
	h_paused BOOLEAN DEFAULT 0,
	h_depth INT DEFAULT 0)
""",
"""
CREATE INDEX IF NOT EXISTS Parent_index ON Jobs(parent)
""",
"""
CREATE TABLE IF NOT EXISTS Dependencies(
	job_id Int,
	dependency INT)
""",
"""
CREATE INDEX IF NOT EXISTS JobId_index ON Dependencies(job_id)
""",
"""
CREATE INDEX IF NOT EXISTS Dependency_index ON Dependencies(dependency)
""",
"""
CREATE TABLE IF NOT EXISTS Workers(
	name TEXT,
	start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	ip TEXT,
	affinity TEXT DEFAULT "",
	state TEXT,
	finished INT,
	error INT,
	last_job INT,
	current_event INT,
	cpu TEXT,
	free_memory INT,
	total_memory int,
	active BOOLEAN)
""",
"""
CREATE UNIQUE INDEX IF NOT EXISTS Name_index ON Workers (name)
""",
"""
CREATE TABLE IF NOT EXISTS Events(
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	worker TEXT, job_id INT,
	job_title TEXT,
	state TEXT,
	start INT,
	duration INT)
""",
"""
CREATE INDEX IF NOT EXISTS Worker_index ON Events(worker)
""",
"""
CREATE INDEX IF NOT EXISTS JobID_index ON Events(job_id)
""",
"""
CREATE INDEX IF NOT EXISTS Start_index ON Events(start)
""",
"""
CREATE TABLE IF NOT EXISTS Affinities(
	id INTEGER,
	name TEXT)
"""
]

# vim: tabstop=4 noexpandtab shiftwidth=4 softtabstop=4 textwidth=79

