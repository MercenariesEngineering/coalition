var xmlrpc
var service
$(document).ready(function()
{
	xmlrpc = imprt("xmlrpc");
	service = new xmlrpc.ServerProxy ("/xmlrpc", ["getjobs", "clearjobs", "clearjob", "getworkers", "clearworkers"]);
	renderJobs ();
});

function clearJobs ()
{
	service.clearjobs ();
	renderJobs ();
}

function clearJob (jobId)
{
	service.clearjob (jobId);
	renderJobs ();
}

function clearWorkers ()
{
	service.clearworkers ();
	renderWorkers ();
}

function renderJobs ()
{
	$("#main").empty ();

	var jobs = service.getjobs ();
	var table = "<table id='jobs'>";

	function renderButtons ()
	{
		$("#main").append("<input type='button' name='myButton' value='Clear All Jobs' onclick='clearJobs()'>\n");
	}
	renderButtons ();
	table += "<tr id='jobtitle'><th>ID</th><th>Title</th><th>State</th><th>Worker</th><th>Try</th><th>Command</th></tr>\n";
	for (i=0; i < jobs.length; i++)
	{
		var job = jobs[i];
		table += "<tr id='job'><td>"+job.ID+"</td><td>"+job.Title+"</td><td>"+job.State+"</td><td>"+job.Worker+"</td><td>"+job.Try+"</td><td>"+job.Command+"</td><td><a href='javascript:clearJob("+job.ID+")'>Remove</a></td></tr>\n";
	}
	table += "</table>";
	$("#main").append(table);
	renderButtons ();
}

function renderWorkers ()
{
	$("#main").empty ();

	var workers = service.getworkers ();
	var table = "<table id='workers'>";

	function renderButtons ()
	{
		$("#main").append("<input type='button' name='myButton' value='Clear All Workers' onclick='clearWorkers()'>\n");
	}
	renderButtons ();
	table += "<tr id='workertitle'><th>Name</th><th>State</th><th>LastJob</th><th>Finished</th><th>Error</th></tr>\n";
	for (i=0; i < workers.length; i++)
	{
		var worker = workers[i];
		table += "<tr id='worker'><td>"+worker.Name+"</td><td>"+worker.State+"</td><td>"+worker.LastJob+"</td><td>"+worker.Finished+"</td><td>"+worker.Error+"</td></tr>\n";
	}
	table += "</table>";
	$("#main").append(table);
	renderButtons ();
}

