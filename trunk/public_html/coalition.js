var xmlrpc;
var service;
var timer;
var page = "jobs";
var logId = 0;
var jobs = {};
var jobsSortKey = "Order";
var jobsSortKeyToUpper = true;
var selectionStart = 0;

function setJobKey (id)
{
	// Same key ?
	if (jobsSortKey == id)
		jobsSortKeyToUpper = !jobsSortKeyToUpper;
	else
	{
		jobsSortKey = id;
		jobsSortKeyToUpper = true;
	}
	renderJobs ();
}

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
	service = new xmlrpc.ServerProxy ("/xmlrpc", ["getjobs", "clearjobs", "clearjob", "getworkers", "clearworkers", "getlog", "addjob", "resetjob", "startworker", "stopworker", "setjobpriority"]);
	timerCB ();
});

function clearJobs ()
{
	if (confirm("Do you really want to clear all the jobs present in the server ?"))
	{
		service.clearjobs ();
		reloadJobs ();
	}
}

function clearJob (jobId)
{
	service.clearjob (jobId);

	// Remove from the job list
	for (i=0; i < jobs.length; i++)
	{
		var job = jobs[i];
		if (job.ID == jobId)
		{
			jobs.splice (i,1);
			break;
		}
	}
	
	// Remove from the DOM
	$("#table"+i).remove();

	// reloadJobs ();
}

function resetJob (jobId)
{
	service.resetjob (jobId);
	reloadJobs ();
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
	reloadWorkers ();
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
		reloadJobs ();
	else if (page == "workers") 
		reloadWorkers ();
	else if (page == "logs") 
		renderLog (logId);
}

function compareStrings (a,b)
{
	if (a < b)
		return jobsSortKeyToUpper ? -1 : 1;
	if (a == b)
		return 0;
	return jobsSortKeyToUpper ? 1 : -1;
}

function compareNumbers (a,b)
{
	return jobsSortKeyToUpper ? a-b : b-a;
}

// Render the current jobs
function renderJobs ()
{
	$("#main").empty ();
	var table = "<table id='jobs' border=0 cellspacing=1 cellpadding=0>";

	function _sort (a,b)
	{
		var aValue = a[jobsSortKey];
		if (typeof aValue == 'string')
			return compareStrings (aValue, b[jobsSortKey]);
		else
			return compareNumbers (aValue, b[jobsSortKey]);
	}

	jobs.sort (_sort);

	function renderButtons ()
	{
		$("#main").append("<input type='button' name='myButton' value='Clear All Jobs' onclick='clearJobs()'>\n");
		$("#main").append("<input type='button' name='myButton' value='Remove Selection' onclick='removeSelection()'>\n");
		$("#main").append("<input type='button' name='myButton' value='Reset Selection' onclick='resetSelection()'>\n");
	}
	renderButtons ();
	$("#main").append("<br/><input size=8 type='edit' id='setPriority' name='setPriority' value='1000'> <input type='button' name='myButton' value='Set Selection Priority' onclick='setPriority()'>");
	
	// Returns the HTML code for a job title column
	function addTitleHTML (attribute)
	{
		table += "<th>";
		var value = jobs[0];
		if (value && value[attribute] != null)
		{
			table += "<a href='javascript:setJobKey(\""+attribute+"\")'>"+attribute;
			if (attribute == jobsSortKey && jobsSortKeyToUpper)
				table += " &#8595;";
			if (attribute == jobsSortKey && !jobsSortKeyToUpper)
				table += " &#8593;";
			table += "</a>";
		}
		else
			table += attribute;
		table += "</th>";
	}

	table += "<tr class='title'>";
	addTitleHTML ("Order");
	addTitleHTML ("ID");
	addTitleHTML ("Title");
	addTitleHTML ("User");
	addTitleHTML ("State");
	addTitleHTML ("Priority");
	addTitleHTML ("Affinity");
	addTitleHTML ("Worker");
	addTitleHTML ("Duration");
	addTitleHTML ("Try");
	addTitleHTML ("Command");
	addTitleHTML ("Dir");
	addTitleHTML ("Dependencies");
	addTitleHTML ("Tools");
	table += "</tr>\n";

	for (i=0; i < jobs.length; i++)
	{
		var job = jobs[i];

		table += "<tr id='table"+i+"' class='entry"+(i%2)+(job.Selected?"Selected":"")+"'>";
		function addTD (attr)
		{
			table += "<td onMouseDown='onClickList(event,"+i+")'>" + attr + "</td>";
		}
		addTD (job.Order);
		addTD (job.ID);
		addTD (job.Title);
		addTD (job.User);
		table += "<td class='"+job.State+"'>"+job.State+"</td>";
		addTD (job.Priority);
		addTD (job.Affinity);
		addTD (job.Worker);
		addTD (formatDuration (job.Duration));
		addTD (job.Try+"/"+job.Retry);
		addTD (job.Command);
		addTD (job.Dir);
		// Compute the dependencies
		var deps = "";
		var j;
		for (j = 0; j < job.Dependencies.length; j++)
		{
			deps += job.Dependencies[j] + " ";
		}
		addTD (deps);
		table += "</td><td><a href='javascript:renderLog("+job.ID+")'>Log</a> <a href='javascript:clearJob("+job.ID+")'>Remove</a> <a href='javascript:resetJob("+job.ID+")'>Reset</a></td></tr>\n";
	}
	table += "</table>";
	$("#main").append(table);
	renderButtons ();

	page = "jobs";
}

// Ask the server for the jobs and render them
function reloadJobs ()
{
	jobs = service.getjobs ();
	renderJobs ();
}

function startWorker (workerName)
{
	service.startworker (workerName);
	reloadWorkers ();
}

function stopWorker (workerName)
{
	service.stopworker (workerName);
	reloadWorkers ();
}

function reloadWorkers ()
{
	$("#main").empty ();

	var workers = service.getworkers ();
	var table = "<table id='workers'>";

	function renderButtons ()
	{
		$("#main").append("<input type='button' name='myButton' value='Clear All Workers' onclick='clearWorkers()'>\n");
	}
	renderButtons ();
	table += "<tr class='title'><th>Name</th><th>Active</th><th>State</th><th>Affinity</th><th>Load</th><th>LastJob</th><th>Finished</th><th>Error</th><th>Tools</th></tr>\n";
	for (i=0; i < workers.length; i++)
	{
		var worker = workers[i];
		table += "<tr class='entry"+(i%2)+"'><td>"+worker.Name+"</td><td class='Active"+worker.Active+"'>"+worker.Active+"</td><td class='"+worker.State+"'>"+worker.State+"</td><td>"+worker.Affinity+"</td><td>"+worker.Load+"</td><td>"+worker.LastJob+"</td><td>"+worker.Finished+"</td><td>"+worker.Error+"</td><td><a href='javascript:startWorker(\""+worker.Name+"\")'>Start</a> <a href='javascript:stopWorker(\""+worker.Name+"\")'>Stop</a></td></tr>\n";
	}
	table += "</table>";
	$("#main").append(table);
	renderButtons ();

	page = "workers";
}

function addjob ()
{
        service.addjob($('#title').attr("value"), 
                $('#cmd').attr("value"),
                $('#dir').attr("value"), 
                $('#priority').attr("value"), 
                $('#retry').attr("value"),
                $('#affinity').attr("value"),
		$('#dependencies').attr("value"));
        reloadJobs ();
}

// List selection handler
function onClickList (event, i)
{
	// Unselect if not ctrl keys
	if (!event.ctrlKey)
	{
		for (j=0; j < jobs.length; j++)
		{
			var job = jobs[j];
			job.Selected = false;
		}
	}

	var begin = event.shiftKey ? Math.min (selectionStart, i) : i
	var end = event.shiftKey ? Math.max (selectionStart, i) : i

	selectionStart = event.shiftKey ? selectionStart : i;

	for (j = begin; j <= end; j++)
	{
		var job = jobs[j];
		if (job)
			job.Selected = event.ctrlKey ? !job.Selected : true;
	}
	renderJobs ();
	return false;
//	if (event.shiftKey)
}

function removeSelection ()
{
	if (confirm("Do you really want to remove the selected jobs ?"))
	{
		for (j=jobs.length-1; j >= 0; j--)
		{
			var job = jobs[j];
			if (job.Selected)
				service.clearjob (job.ID);
		}
	}
	reloadJobs ();
}

function resetSelection ()
{
	if (confirm("Do you really want to reset the selected jobs ?"))
	{
		for (j=jobs.length-1; j >= 0; j--)
		{
			var job = jobs[j];
			if (job.Selected)
				service.resetjob (job.ID);
		}
	}
	reloadJobs ();
}

function setPriority ()
{
	if (confirm("Do you really want to set the priority of the selected jobs ?"))
	{
		for (j=jobs.length-1; j >= 0; j--)
		{
			var job = jobs[j];
			if (job.Selected)
				service.setjobpriority (job.ID, $('#setPriority').attr("value"));
		}
	}
	reloadJobs ();
}

