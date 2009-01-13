var xmlrpc;
var service;
var timer;
var page = "jobs";
var logId = 0;

function get_cookie ( cookie_name )
{
  var results = document.cookie.match ( '(^|;) ?' + cookie_name + '=([^;]*)(;|$)' );

  if ( results )
    return ( unescape ( results[2] ) );
  else
    return "";
}

$(document).ready(function()
{
	xmlrpc = imprt("xmlrpc");
	service = new xmlrpc.ServerProxy ("/xmlrpc", ["getjobs", "clearjobs", "clearjob", "getworkers", "clearworkers", "getlog", "addjobwithaffinity"]);
	timerCB ();
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

function renderLog (jobId)
{
	logId = jobId;
	$("#main").empty ();
	var _log = service.getlog (jobId);
	$("#main").append("<pre class='logs'><h2>Logs for jod "+jobId+":</h2>"+_log+"</pre>");

	page = "logs";
}

function clearWorkers ()
{
	service.clearworkers ();
	renderWorkers ();
}

function formatDuration (secondes)
{
	var days = Math.floor (secondes / (60*60*24));
	var hours = Math.floor ((secondes-days*60*60*24) / (60*60));
	var minutes = Math.floor ((secondes-days*60*60*24-hours*60*60) / 60);
	var secondes = Math.floor (secondes-days*60*60*24-hours*60*60-minutes*60);
	if (days > 0)	
		return days + " d " + hours + " h " + minutes + " m " + secondes + " s";
	if (hours > 0)	
		return hours + " h " + minutes + " m " + secondes + " s";
	if (minutes > 0)	
		return minutes + " m " + secondes + " s";
	return secondes + " s";
}

// Timer callback
function timerCB ()
{
	refresh ();

	// Fire a new time event
	// timer=setTimeout("timerCB ()",4000);
}

function refresh ()
{
	if (page == "jobs")
		renderJobs ();
	else if (page == "workers") 
		renderWorkers ();
	else if (page == "logs") 
		renderLog (logId);
}

function renderJobs ()
{
	$("#main").empty ();

	var jobs = service.getjobs ();
	var table = "<table id='jobs' border=0 cellspacing=1 cellpadding=0>";

	function renderButtons ()
	{
		$("#main").append("<input type='button' name='myButton' value='Clear All Jobs' onclick='clearJobs()'>\n");
	}
	renderButtons ();
	table += "<tr class='title'><th>ID</th><th>Title</th><th>User</th><th>State</th><th>Priority</th><th>Affinity</th><th>Worker</th><th>Duration</th><th>Try</th><th>Command</th><th>Directory</th><th>Tools</th></tr>\n";
	for (i=0; i < jobs.length; i++)
	{
		var job = jobs[i];
		table += "<tr class='entry"+(i%2)+"'><td>"+job.ID+"</td><td>"+job.Title+"</td><td>"+job.User+"</td><td class='"+job.State+"'>"+job.State+"</td><td>"+job.Priority+"</td><td>"+job.Affinity+"</td><td>"+job.Worker+"</td><td>"+formatDuration (job.Duration)+"</td><td>"+job.Try+"/"+job.Retry+"</td><td>"+job.Command+"</td><td>"+job.Dir+
		"</td><td><a href='javascript:renderLog("+job.ID+")'>Log</a> <a href='javascript:clearJob("+job.ID+")'>Remove</a></td></tr>\n";
	}
	table += "</table>";
	$("#main").append(table);
	renderButtons ();

	page = "jobs";
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
	table += "<tr class='title'><th>Name</th><th>State</th><th>Affinity</th><th>Load</th><th>LastJob</th><th>Finished</th><th>Error</th></tr>\n";
	for (i=0; i < workers.length; i++)
	{
		var worker = workers[i];
		table += "<tr class='entry"+(i%2)+"'><td>"+worker.Name+"</td><td class='"+worker.State+"'>"+worker.State+"</td><td>"+worker.Affinity+"</td><td>"+worker.Load+"</td><td>"+worker.LastJob+"</td><td>"+worker.Finished+"</td><td>"+worker.Error+"</td></tr>\n";
	}
	table += "</table>";
	$("#main").append(table);
	renderButtons ();

	page = "workers";
}

