var xmlrpc;
var service;
var timer;
var page = "jobs";
var viewJob = 0;
var logId = 0;
var jobs = {};
var workers = {};
var parents = {};
var jobsSortKey = "ID";
var jobsSortKeyToUpper = true;
var workersSortKey = "Name";
var workersSortKeyToUpper = true;
var selectionStart = 0;
var showTools = true;

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

function setWorkerKey (id)
{
	// Same key ?
	if (workersSortKey == id)
		workersSortKeyToUpper = !workersSortKeyToUpper;
	else
	{
		workersSortKey = id;
		workersSortKeyToUpper = true;
	}
	renderWorkers ();
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
	service = new xmlrpc.ServerProxy ("/xmlrpc", ["getjobs", "clearjobs", "clearjob", "getworkers", "clearworkers",
	                                              "getlog", "addjob", "resetjob", "startworker", "stopworker", "setjobpriority",
	                                              "updatejobs", "updateworkers", "pausejob"]);
	timerCB ();

	tools = new FloatLayer('tools',15,15,1);
    lay=document.getElementById('tools');
    lay.style.position = 'absolute';
    lay.style.top = 15;
    lay.style.right = 15;
    tools.initialize();
    tools.setFloatToRight();

    alignFloatLayers();
});

function showHideTools ()
{
    showTools = !showTools;
    updateTools ();
}

function updateTools ()
{
    if (!showTools)
    {
        $("#tools").show ();
        $("#jobtools").hide ();
        $("#workertools").hide ();
        $("#showhidetools").show ();
    }
    else if (page == "jobs")
    {
        $("#tools").show ();
        $("#jobtools").show ();
        $("#workertools").hide ();
        $("#showhidetools").hide ();
        alignFloatLayers();
    }
    else if (page == "workers")
    {
        $("#tools").show ();
        $("#jobtools").hide ();
        $("#workertools").show ();
        $("#showhidetools").hide ();
        alignFloatLayers();
    }
    else
    {
        $("#tools").hide ();
        $("#jobtools").hide ();
        $("#workertools").hide ();
        alignFloatLayers();
    }
}

function clearJobs ()
{
	if (confirm("Do you really want to clear all the jobs ?"))
	{
		service.clearjobs (viewJob);
		reloadJobs ();
	}
}

function clearJob (jobId)
{
	if (confirm("Do you really want to remove the job " + jobId + " ?"))
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
}

function resetJob (jobId)
{
	if (confirm("Do you really want to reset the job " + jobId + " ?"))
	{
	    service.resetjob (jobId);
	    reloadJobs ();
    }
}

function pauseJob (jobId)
{
    service.pausejob (jobId);
    reloadJobs ();
}

function goToJob (jobId)
{
    viewJob = jobId;
    reloadJobs ();
}

function renderLog (jobId)
{
	logId = jobId;
	$("#main").empty ();
	var _log = service.getlog (jobId);
	$("#main").append("<pre class='logs'><h2>Logs for job "+jobId+":</h2>"+_log+"</pre>");

	page = "logs";
	updateTools ();
}

function clearWorkers ()
{
	if (confirm("Do you really want to clear all the workers?"))
	{
	    service.clearworkers ();
	    reloadWorkers ();
	}
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

function compareStrings (a,b,toupper)
{
	if (a < b)
		return toupper ? -1 : 1;
	if (a == b)
		return 0;
	return toupper ? 1 : -1;
}

function compareNumbers (a,b,toupper)
{
	return toupper ? a-b : b-a;
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
			return compareStrings (aValue, b[jobsSortKey], jobsSortKeyToUpper);
		else
			return compareNumbers (aValue, b[jobsSortKey], jobsSortKeyToUpper);
	}

	jobs.sort (_sort);

	for (i=0; i < parents.length; i++)
	{
		var parent = parents[i];
    	$("#main").append((i == 0 ? "" : " > ") + ("<a href='javascript:goToJob("+parent.ID+")'>" + parent.Title + "</a>"));
	}

	// Returns the HTML code for a job title column
	function addTitleHTMLEx (attribute, alias)
	{
		table += "<th>";
		var value = jobs[0];
		if (value && value[attribute] != null)
		{
			table += "<a href='javascript:setJobKey(\""+attribute+"\")'>"+alias;
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

	function addTitleHTML (attribute)
	{
	    addTitleHTMLEx (attribute, attribute)
	}

	table += "<tr class='title'>";
	//addTitleHTML ("Order");
	addTitleHTML ("ID");
	addTitleHTML ("Title");
	addTitleHTML ("User");
	addTitleHTML ("State");
	addTitleHTML ("Priority");
	addTitleHTMLEx ("TotalFinished", "Ok");
	addTitleHTMLEx ("TotalErrors", "Err");
	addTitleHTML ("Total");
	addTitleHTML ("Affinity");
	addTitleHTML ("TimeOut");
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
		//addTD (job.Order);
		addTD (job.ID);
		table += "<td><a href='javascript:goToJob("+job.ID+")'>" + job.Title + "</a></td>\n";
		//addTD (job.Title);
		addTD (job.User);
	    table += "<td class='"+job.State+"' onMouseDown='onClickList(event,"+i+")'>"+job.State+"</td>";
		addTD (job.Priority);
		if (job.Total > 0)
		{
		    table += "<td class='"+(job.TotalFinished > 0 ? "FINISHED" : "WAITING")+"' width=30 onMouseDown='onClickList(event,"+i+")'>"+job.TotalFinished+"</td>";
		    table += "<td class='"+(job.TotalErrors > 0 ? "ERROR" : "WAITING")+"' width=30 onMouseDown='onClickList(event,"+i+")'>"+job.TotalErrors+"</td>";
		    table += "<td class='"+(job.Total == job.TotalFinished ? "FINISHED" : "WAITING")+"' width=30 onMouseDown='onClickList(event,"+i+")'>"+job.Total+"</td>";
		}
		else
		{
		    addTD ("");
		    addTD ("");
		    addTD ("");
		}
		addTD (job.Affinity);
		addTD (job.TimeOut);
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
		table += "</td><td><a href='javascript:renderLog("+job.ID+")'>Log</a></td></tr>\n";
	}
	table += "</table>";
	$("#main").append(table);
    $("#main").append("<br/>");

	page = "jobs";
	updateTools ();
}

// Ask the server for the jobs and render them
function reloadJobs ()
{
    var result = service.getjobs (viewJob);
	jobs = result.Jobs;
	parents = result.Parents;
	resetjobprops ();
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

function startWorkers ()
{
	for (j=workers.length-1; j >= 0; j--)
	{
		var worker = workers[j];
		if (worker.Selected)
           	service.startworker (worker.Name);
	}
	reloadWorkers ();
}

function stopWorkers ()
{
	for (j=workers.length-1; j >= 0; j--)
	{
		var worker = workers[j];
		if (worker.Selected)
           	service.stopworker (worker.Name);
	}
	reloadWorkers ();
}






var MultipleSelection = {}
function checkSelectionProperties (list, props)
{
    var values = []

	for (i = 0; i < list.length; i++)
	{
		var item = list[i];
		if (item.Selected)
		{
    		for (j = 0; j < props.length; ++j)
    		{
    		    var value = item[props[j][0]];
    		    if (values[j] != null && values[j] != value)
    		        values[j] = MultipleSelection;
    		    else
    		        values[j] = value;
    		}
		}
	}

    for (i = 0; i < props.length; ++i)
    {
        if (values[i] == MultipleSelection)
        {
            // different values
            $('#'+props[i][1]).css("background-color", "orange");
            $('#'+props[i][1]).attr("value", "");
        }
        else if (values[i] == null)
        {
            // default value
            $('#'+props[i][1]).css("background-color", "white");
            $('#'+props[i][1]).attr("value", props[i][2]);
        }
        else
        {
            // unique values
            $('#'+props[i][1]).css("background-color", "white");
            $('#'+props[i][1]).attr("value", values[i]);
        }
    }
    return values;
}

function updateSelectionProp (values, props, prop)
{
    for (i = 0; i < props.length; ++i)
        if (props[i][1] == prop)
        {
            values[i] = true;
            $('#'+props[i][1]).css("background-color", "greenyellow");
            break;
        }
}

function sendSelectionPropChanges (list, id, values, props, command)
{
    var uplist = [];
	for (j=list.length-1; j >= 0; j--)
	{
		var item = list[j];
		if (item.Selected)
		    uplist.push (item[id]);
	}

    for (i = 0; i < props.length; ++i)
        if (values[i] == true)
        {
            var value = $('#'+props[i][1]).attr("value");
            service[command] (uplist, props[i][0], value);
            props[i][2] = value;
        }
}

function setSelectionDefaultProperties (props)
{
    for (i = 0; i < props.length; ++i)
        props[i][2] = $('#'+props[i][1]).attr("value");
}

var WorkerProps =
[
    [ "Affinity", "waffinity", "" ],
];
var updatedWorkerProps = {}

function resetworkerprops ()
{
    updatedWorkerProps = checkSelectionProperties (workers, WorkerProps);
}

function onchangeworkerprop (prop)
{
    updateSelectionProp (updatedWorkerProps, WorkerProps, prop);
}

function updateworkers ()
{
    sendSelectionPropChanges (workers, 'Name', updatedWorkerProps, WorkerProps, 'updateworkers');
    reloadWorkers ();
}

function reloadWorkers ()
{
    var result = service.getworkers ();
	workers = result;
	resetworkerprops ();
	renderWorkers ();
}

function renderWorkers ()
{
	$("#main").empty ();

	var table = "<table id='workers'>";

	$("#main").append("<br>");
	table += "<tr class='title'>\n";

	// Returns the HTML code for a worker title column
	function addTitleHTML (attribute)
	{
		table += "<th>";
		var value = workers[0];
		if (value && value[attribute] != null)
		{
			table += "<a href='javascript:setWorkerKey(\""+attribute+"\")'>"+attribute;
			if (attribute == workersSortKey && workersSortKeyToUpper)
				table += " &#8595;";
			if (attribute == workersSortKey && !workersSortKeyToUpper)
				table += " &#8593;";
			table += "</a>";
		}
		else
			table += attribute;
		table += "</th>";
	}

    addTitleHTML ("Name");
    addTitleHTML ("Active");
    addTitleHTML ("State");
    addTitleHTML ("Affinity");
    addTitleHTML ("Load");
    addTitleHTML ("LastJob");
    addTitleHTML ("Finished");
    addTitleHTML ("Error");

	table += "</tr>\n";

	function _sort (a,b)
	{
		var aValue = a[workersSortKey];
		if (typeof aValue == 'string')
			return compareStrings (aValue, b[workersSortKey], workersSortKeyToUpper);
		else
			return compareNumbers (aValue, b[workersSortKey], workersSortKeyToUpper);
	}

	workers.sort (_sort);

	for (i=0; i < workers.length; i++)
	{
		var worker = workers[i];
		table += "<tr id='table"+i+"' class='entry"+(i%2)+(worker.Selected?"Selected":"")+"'>"+
		         "<td onMouseDown='onClickList(event,"+i+")'>"+worker.Name+"</td>"+
		         "<td class='Active"+worker.Active+"' onMouseDown='onClickList(event,"+i+")'>"+worker.Active+"</td>"+
		         "<td class='"+worker.State+"' onMouseDown='onClickList(event,"+i+")'>"+worker.State+"</td>"+
		         "<td onMouseDown='onClickList(event,"+i+")'>"+worker.Affinity+"</td>"+
		         "<td onMouseDown='onClickList(event,"+i+")'>"+worker.Load+"</td>"+
		         "<td onMouseDown='onClickList(event,"+i+")'>"+worker.LastJob+"</td>"+
		         "<td onMouseDown='onClickList(event,"+i+")'>"+worker.Finished+"</td>"+
		         "<td onMouseDown='onClickList(event,"+i+")'>"+worker.Error+"</td>"+
		         "</tr>\n";
	}
	table += "</table>";
	$("#main").append(table);
	$("#main").append("<br>");

	page = "workers";
	updateTools ();
}

var JobProps =
[
    [ "Command", "cmd", "" ],
    [ "Dir", "dir", "." ],
    [ "Priority", "priority", "1000" ],
    [ "Affinity", "affinity", "" ],
    [ "TimeOut", "timeout", "0" ]
];
var updatedJobProps = {}

function resetjobprops ()
{
    updatedJobProps = checkSelectionProperties (jobs, JobProps);
}

function onchangejobprop (prop)
{
    updateSelectionProp (updatedJobProps, JobProps, prop);
}

function updatejobs ()
{
    sendSelectionPropChanges (jobs, 'ID', updatedJobProps, JobProps, 'updatejobs');
    reloadJobs ();
}

function addjob ()
{
        service.addjob(viewJob,
                       $('#title').attr("value"), 
                       $('#cmd').attr("value"),
                       $('#dir').attr("value"), 
                       $('#priority').attr("value"), 
                       $('#retry').attr("value"),
                       $('#timeout').attr("value"),
                       $('#affinity').attr("value"),
		               $('#dependencies').attr("value"));
		setSelectionDefaultProperties (JobProps);
        reloadJobs ();
}

// List selection handler
function onClickList (event, i)
{
    var thelist;
    if (page == "jobs")         thelist = jobs;
    else if (page == "workers") thelist = workers;
    
	// Unselect if not ctrl keys
	if (!event.ctrlKey)
	{
		for (j=0; j < thelist.length; j++)
		{
			var item = thelist[j];
			item.Selected = false;
		}
	}

	var begin = event.shiftKey ? Math.min (selectionStart, i) : i
	var end = event.shiftKey ? Math.max (selectionStart, i) : i

	selectionStart = event.shiftKey ? selectionStart : i;

	for (j = begin; j <= end; j++)
	{
		var item = thelist[j];
		if (item)
			item.Selected = event.ctrlKey ? !item.Selected : true;
	}
	if (page == "jobs")         { renderJobs (); resetjobprops (); }
    else if (page == "workers") { renderWorkers (); resetworkerprops (); }
}

function selectAll (state)
{
    var thelist
    if (page == "jobs")
        thelist = jobs;
    else if (page == "workers")
        thelist = workers;
    else
        return;
        
	for (j=0; j < thelist.length; j++)
	{
		var item = thelist[j];
		item.Selected = state;
	}

	if (page == "jobs")         { renderJobs (); resetjobprops (); }
    else if (page == "workers") { renderWorkers (); resetworkerprops (); }
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

function pauseSelection ()
{
	for (j=jobs.length-1; j >= 0; j--)
	{
		var job = jobs[j];
		if (job.Selected)
			service.pausejob (job.ID);
	}
	reloadJobs ();
}
