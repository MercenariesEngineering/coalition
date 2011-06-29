var xmlrpc;
var timer;
var page = "jobs";
var viewJob = 0;
var logId = 0;
var jobs = [];
var selectedJobs = {};
var cutJobs = {};
var selectedWorkers = {};
var selectedActivities = {};
var workers = [];
var parents = {};
var activities = [];
var jobsSortKey = "ID";
var jobsSortKeyToUpper = true;
var workersSortKey = "Name";
var workersSortKeyToUpper = true;
var activitiesSortKey = "Start";
var activitiesSortKeyToUpper = false;
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

function setActivityKey (id)
{
	// Same key ?
	if (activitiesSortKey == id)
		activitiesSortKeyToUpper = !activitiesSortKeyToUpper;
	else
	{
		activitiesSortKey = id;
		activitiesSortKeyToUpper = true;
	}
	renderActivities ();
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
	reloadJobs ();
	reloadWorkers ();
	reloadActivities ();
	showJobs ();
	timer=setTimeout(timerCB,4000);
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
    }
    else if (page == "workers")
    {
        $("#tools").show ();
        $("#jobtools").hide ();
        $("#workertools").show ();
    }
    else
    {
        $("#tools").hide ();
        $("#jobtools").hide ();
        $("#workertools").hide ();
    }
}

function goToJob (jobId)
{
    viewJob = jobId;
    reloadJobs ();
}

function showLog ()
{
	$("#jobsTab").hide ();
	$("#workersTab").hide ();
	$("#activitiesTab").hide ();
	$("#logsTab").show ();
	document.getElementById("jobtab").className = "unactivetab";
	document.getElementById("workertab").className = "unactivetab";
	document.getElementById("activitytab").className = "unactivetab";
	document.getElementById("logtab").className = "activetab";

	page = "logs";
	updateTools ();
}

function clearLog ()
{
	$("#logs").empty ();
}

function renderLog (jobId)
{
    showLog ();
	logId = jobId;

    $.ajax({ type: "GET", url: "/json/getlog", data: "id="+str(jobId), dataType: "json", success: 
        function (data) 
        {
	        $("#logs").empty();
	        $("#logs").append("<pre class='logs'><h2>Logs for job "+jobId+":</h2>"+data+"</pre>");

	        page = "logs";
	        updateTools ();
            document.getElementById("refreshbutton").className = "refreshbutton";
        }
    });
}

function clearWorkers ()
{
	if (confirm("Do you really want to clear all the workers?"))
	{
	    var _data = "";
		for (j=workers.length-1; j >= 0; j--)
		{
			var worker = workers[j];
			if (selectedWorkers[worker.Name])
			    _data += "id="+str(worker.Name)+"&";
		}
        $.ajax({ type: "GET", url: "/json/clearworkers", data: _data, dataType: "json", success: 
            function () 
            {
    	        selectedWorkers = {}
	            reloadWorkers ();
    	        updateWorkerProps ();
            }
        });
	}
}

function formatDate (_date)
{
	var date = new Date(_date*1000)
    return date.getFullYear() + '/' + (date.getMonth()+1) + '/' + date.getDate() + ' ' + date.getHours () + ':' + date.getMinutes () + ':' + date.getSeconds();
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
    if (document.getElementById("autorefresh").checked)
	    refresh ();

	// Fire a new time event
	timer=setTimeout(timerCB,4000);
}

function refresh ()
{
    document.getElementById("refreshbutton").className = "refreshing";
	if (page == "jobs")
		reloadJobs ();
	else if (page == "workers") 
		reloadWorkers ();
	else if (page == "activities") 
		reloadActivities ();
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

function showJobs ()
{
	$("#jobsTab").show ();
	$("#workersTab").hide ();
	$("#activitiesTab").hide ();
	$("#logsTab").hide ();
	document.getElementById("jobtab").className = "activetab";
	document.getElementById("workertab").className = "unactivetab";
	document.getElementById("activitytab").className = "unactivetab";
	document.getElementById("logtab").className = "unactivetab";

	page = "jobs";
	updateTools ();
}

// Returns the HTML code for a job title column
function addSumEmpty (str)
{
	if (str == undefined)
		return "<td></td>";
	else
		return "<td class='headerCell'>" + str + "</td>";
}

// Returns the HTML code for a job title column
function addSum (inputs, attribute)
{
	var sum = 0;
	for (i=0; i < inputs.length; i++)
	{
		var job = inputs[i];
		sum += job[attribute];
	}
	return "<td class='headerCell'>" + sum + "</td>";
}

// Returns the HTML code for a job title column
function addSumFinished (inputs, attribute)
{
	var sum = 0;
	for (i=0; i < inputs.length; i++)
	{
		var job = inputs[i];
		if (job[attribute] == "FINISHED")
		    sum ++;
	}
	return "<td class='headerCell'>" + sum + " FINISHED</td>";
}

// Average
function addSumAvgDuration (inputs, attribute)
{
	var sum = 0;
	var count = 0;
	for (i=0; i < inputs.length; i++)
	{
		var job = inputs[i];
		sum += job[attribute];
		count++;
	}
	if (count > 0)
	    return "<td class='headerCell'>Avg " + formatDuration (sum/count) + "</td>";
    else
        return "<td class='headerCell'></td>";
}

// Returns the HTML code for a job title column
function addSumSimple (inputs)
{
	return "<td class='headerCell'>" + inputs.length + " jobs</td>";
}

// Render the current jobs
function renderJobs ()
{
	$("#jobs").empty ();
	$("#parents").empty ();
	var table = "<table id='jobsTable'>";

    function getJobProgress (job)
    {
	    if (job.Total > 0)
	    {
            // A bar div
            lProgress = job.TotalFinished / job.Total;
            gProgress = job.TotalFinished / job.Total;
	    }
	    else
	    {
	        gProgress = job.State == "FINISHED"  ? 
	                        1.0 :
	                        ( 
		                            job.GlobalProgress == null ? 
		                                0.0 : 
		                                parseFloat(job.GlobalProgress)
                            );
	        lProgress = job.State == "FINISHED"  ? 
	                        1.0 :
	                        ( 
		                            job.LocalProgress == null ? 
		                                gProgress : 
		                                parseFloat(job.LocalProgress)
                            );
        }
        return lProgress, gProgress;
    }
    
	function _sort (a,b)
	{
		if (jobsSortKey == "Progress")
		{
		    var lProgressA, gProgressA = getJobProgress (a);
		    var lProgressB, gProgressB = getJobProgress (b);
		    return compareNumbers (gProgressA, gProgressB, jobsSortKeyToUpper);
	    }
	    else
	    {
		    var aValue = a[jobsSortKey];
		    if (typeof aValue == 'string')
    			return compareStrings (aValue, b[jobsSortKey], jobsSortKeyToUpper);
		    else
    			return compareNumbers (aValue, b[jobsSortKey], jobsSortKeyToUpper);
    	}
	}

	jobs.sort (_sort);

	for (i=0; i < parents.length; i++)
	{
		var parent = parents[i];
    	$("#parents").append((i == 0 ? "" : " > ") + ("<a href='javascript:goToJob("+parent.ID+")'>" + parent.Title + "</a>"));
	}

	// Returns the HTML code for a job title column
	function addTitleHTMLEx (attribute, alias)
	{
		table += "<th class='headerCell' onclick='"+"setJobKey(\""+attribute+"\")'>";
		var value = jobs[0];
		if (value)
		{
			table += alias;
			if (attribute == jobsSortKey && jobsSortKeyToUpper)
				table += " &#8595;";
			if (attribute == jobsSortKey && !jobsSortKeyToUpper)
				table += " &#8593;";
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
	addTitleHTML ("URL");
	addTitleHTML ("User");
	addTitleHTML ("State");
	addTitleHTML ("Priority");
	addTitleHTMLEx ("TotalFinished", "Ok");
	addTitleHTMLEx ("TotalWorking", "Wrk");
	addTitleHTMLEx ("TotalErrors", "Err");
	addTitleHTML ("Total");
	addTitleHTML ("Progress");
	addTitleHTML ("Affinity");
	addTitleHTML ("TimeOut");
	addTitleHTML ("Worker");
	addTitleHTML ("StartTime");
	addTitleHTML ("Duration");
	addTitleHTML ("Try");
	addTitleHTML ("Command");
	addTitleHTML ("Dir");
	addTitleHTML ("Dependencies");
	table += "</tr>\n";

	for (i=0; i < jobs.length; i++)
	{
		var job = jobs[i];

        var mouseDownEvent = "onMouseDown='onClickList(event,"+i+")' onDblClick='onDblClickList(event,"+i+")'";
        
		table += "<tr id='jobtable"+i+"' "+mouseDownEvent+" class='entry"+(i%2)+(selectedJobs[job.ID]?"Selected":"")+"'>";
		function addTD (attr)
		{
			table += "<td>" + attr + "</td>";
		}
		//addTD (job.Order);
		addTD (job.ID);
		table += "<td>" + job.Title + "</td>\n";

        // URL
		if (job.URL != "")
		    addTD ("<a href='"+job.URL+"'>Open</a>")
        else
            addTD ("")
		
		addTD (job.User);
	    table += "<td class='"+job.State+"'>"+job.State+"</td>";
		addTD (job.Priority);
		if (job.Total > 0)
		{
		    table += "<td class='"+(job.TotalFinished > 0 ? "FINISHED" : "WAITING")+"' width=30>"+job.TotalFinished+"</td>";
		    table += "<td class='"+(job.TotalWorking > 0 ? "WORKING" : "WAITING")+"' width=30>"+job.TotalWorking+"</td>";
		    table += "<td class='"+(job.TotalErrors > 0 ? "ERROR" : "WAITING")+"' width=30>"+job.TotalErrors+"</td>";
		    table += "<td class='"+(job.Total == job.TotalFinished ? "FINISHED" : "WAITING")+"' width=30>"+job.Total+"</td>";
		}
		else
		{
		    addTD ("");
		    addTD ("");
		    addTD ("");
		    addTD ("");
		}
		
		// *** Progress bar
        var progress = ""
        var lProgress, gProgress = getJobProgress (job)
        lProgress = Math.floor(lProgress*100.0);
        gProgress = Math.floor(gProgress*100.0);

        // A bar div
        progress = "<div class='progress'>";
        progress += "<div class='lprogressbar' style='width:" + lProgress + "%' />";
        progress += "<div class='progresslabel'>" + gProgress + "%</div>";
        progress += "</div>";
        		
		addTD (progress);
		addTD (job.Affinity);
		addTD (job.TimeOut);
		addTD (job.Worker);
		addTD (formatDate (job.StartTime));
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

		table += "</td></tr>\n";
	}

	// Footer
	table += "<tr class='title'>";

	table += addSumEmpty ("TOTAL");
	table += addSumSimple (jobs);
	table += addSumEmpty ();
	table += addSumEmpty ();
	table += addSumFinished (jobs, "State");
	table += addSumEmpty ();
	table += addSum (jobs, "TotalFinished");
	table += addSum (jobs, "TotalWorking");
	table += addSum (jobs, "TotalErrors");
	table += addSum (jobs, "Total");
	table += addSumEmpty ();
	table += addSumEmpty ();
	table += addSumEmpty ();
	table += addSumEmpty ();
	table += addSumEmpty ();
	table += addSumAvgDuration (jobs, "Duration");
	table += addSumEmpty ();
	table += addSumEmpty ();
	table += addSumEmpty ();
	table += addSumEmpty ();
	table += "</tr>\n";

	table += "</table></div>";
	$("#jobs").append(table);
}

function logSelection ()
{
	for (j=jobs.length-1; j >= 0; j--)
	{
		var job = jobs[j];
		if (selectedJobs[job.ID])
			renderLog (job.ID);
	}
}

// Ask the server for the jobs and render them
function reloadJobs ()
{
    var tag = document.getElementById("filterJobs").value;
    tag = tag == "NONE" ? "" : tag;
    $.ajax({ type: "GET", url: "/json/getjobs", data: "filter="+tag+"&id="+str(viewJob), dataType: "json", success: 
        function(data) 
        {
	        jobs = []
	        for (j = 0; j < data.Jobs.length; ++j)
	        {
	            var job = data.Jobs[j];
	            var nj = {};
	            for (i = 0; i < data.Vars.length; ++i)
	            {
	                nj[data.Vars[i]] = job[i];
	            }
	            jobs.push (nj);
	        }
	        parents = data.Parents;
	        renderJobs ();
            document.getElementById("refreshbutton").className = "refreshbutton";
        },
        error : 
        function (jqXHR, textStatus, errorThrown) 
        { 
            alert("JQuery error : " + textStatus); 
        }
    });
}

function startWorkers ()
{
    var _data = "";
	for (j=workers.length-1; j >= 0; j--)
	{
		var worker = workers[j];
		if (selectedWorkers[worker.Name])
           	_data += "id="+worker.Name+"&";
	}
    $.ajax({ type: "GET", url: "/json/startworkers", data: _data, dataType: "json", success: 
        function () 
        {
        	reloadWorkers ();
        }
    });
}

function stopWorkers ()
{
    var _data = "";
	for (j=workers.length-1; j >= 0; j--)
	{
		var worker = workers[j];
		if (selectedWorkers[worker.Name])
           	_data += "id="+worker.Name+"&";
	}
    $.ajax({ type: "GET", url: "/json/stopworkers", data: _data, dataType: "json", success: 
        function () 
        {
        	reloadWorkers ();
        }
    });
}

function workerActivity ()
{
    var _data = "";
	for (j=workers.length-1; j >= 0; j--)
	{
		var worker = workers[j];
		if (selectedWorkers[worker.Name])
		{
		    title:$('#activityWorker').attr("value", worker.Name)
		    title:$('#activityJob').attr("value", "")
           	break;
        }
	}

    reloadActivities ()
	page = "activities"
	showActivities ()
}

function jobActivity ()
{
    var _data = "";
	for (j=jobs.length-1; j >= 0; j--)
	{
		var job = jobs[j];
		if (selectedJobs[job.ID])
		{
		    title:$('#activityWorker').attr("value", "")
		    title:$('#activityJob').attr("value", job.ID)
           	break;
        }
	}

    reloadActivities ()
	page = "activities"
	showActivities ()
}

var MultipleSelection = {}
function checkSelectionProperties (list, props, selectedList, idName)
{
    var values = []

	for (i = 0; i < list.length; i++)
	{
		var item = list[i];
		if (selectedList[item[idName]])
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

function sendSelectionPropChanges (list, idName, values, props, _url, selectedList, func)
{
    var _data = "";
	for (j=list.length-1; j >= 0; j--)
	{
		var id = list[j][idName];
		if (selectedList[id])
		    _data += "id="+str(id)+"&";
	}

    for (i = 0; i < props.length; ++i)
        if (values[i] == true)
        {
            var prop = props[i][0];
            var value = $('#'+props[i][1]).attr("value");
            _data += "prop="+prop+"&value="+value+"&";
        }

    // One single call
    $.ajax({ type: "GET", url: _url, data: _data, dataType: "json", success:
        function () 
        {
            for (i = 0; i < props.length; ++i)
                if (values[i] == true)
                {
                    props[i][2] = value;
                }
            func ();
        }
    });
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

function updateWorkerProps ()
{
    updatedWorkerProps = checkSelectionProperties (workers, WorkerProps, selectedWorkers, "Name");
}

function onchangeworkerprop (prop)
{
    updateSelectionProp (updatedWorkerProps, WorkerProps, prop);
}

function updateworkers ()
{
    sendSelectionPropChanges (workers, 'Name', updatedWorkerProps, WorkerProps, "/json/updateworkers", selectedWorkers,
        function ()
        {
            reloadWorkers ();
        }
    );
}

function reloadWorkers ()
{
    $.ajax({ type: "GET", url: "/json/getworkers", dataType: "json", success: 
        function (data) 
        {
	        workers = [];
	        for (j = 0; j < data.Workers.length; ++j)
	        {
	            var worker = data.Workers[j];
	            var nw = {};
	            for (i = 0; i < data.Vars.length; ++i)
	            {
	                nw[data.Vars[i]] = worker[i];
	            }
	            workers.push (nw);
	        }
	        renderWorkers ();
            document.getElementById("refreshbutton").className = "refreshbutton";
        }
    });
}

function showWorkers ()
{
	$("#jobsTab").hide ();
	$("#workersTab").show ();
	$("#activitiesTab").hide ();
	$("#logsTab").hide ();
	document.getElementById("jobtab").className = "unactivetab";
	document.getElementById("workertab").className = "activetab";
	document.getElementById("activitytab").className = "unactivetab";
	document.getElementById("logtab").className = "unactivetab";

	page = "workers";
	updateTools ();
}

function renderWorkers ()
{
	$("#workers").empty ();

	var table = "<table id='workersTable'>";
	table += "<tr class='title'>\n";

	// Returns the HTML code for a worker title column
	function addTitleHTML (attribute)
	{
        table += "<th class='headerCell' onclick='"+"setWorkerKey(\""+attribute+"\")'>";	
		var value = workers[0];
		if (value && value[attribute] != null)
		{
			table += attribute;
			if (attribute == workersSortKey && workersSortKeyToUpper)
				table += " &#8595;";
			if (attribute == workersSortKey && !workersSortKeyToUpper)
				table += " &#8593;";
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
    addTitleHTML ("Memory");
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

        // *** Build the load tab for this worker		
        // A global div
	    var load = "<div class='load'>";
	        // Add each CPU load
	        var loadValue = 0;
    	    for (j=0; j < worker.Load.length; j++)
    	    {
        	    load += "<div class='loadbar' style='width:" + worker.Load[j] + "%;height:" + 16/worker.Load.length + "' />";
    	        loadValue += worker.Load[j]
            }

            // Add the numerical value of the load
   	        load += "<div class='loadlabel'>" + Math.floor(loadValue/worker.Load.length) + "%</div>";
	    load += "</div>";
    
        // *** Build the memory tab for this worker		
	    var memory = "<div class='mem'>";
   	    memory += "<div class='membar' style='width:" + 100*(worker.TotalMemory-worker.FreeMemory)/worker.TotalMemory + "%' />";

        function formatMem (a)
        {
            if (a > 1024)
                return Math.round(a/1024*100)/100 + " GB";
            else
                return str(a) + " Mo";
        }
        
        memLabel = formatMem (worker.TotalMemory-worker.FreeMemory);
        memLabel += " / ";
        memLabel += formatMem (worker.TotalMemory);

        // Add the numerical value of the mem
        memory += "<div class='memlabel'>" + memLabel + "</div>";
	    memory += "</div>";
	    
		table += "<tr id='workertable"+i+"' class='entry"+(i%2)+(selectedWorkers[worker.Name]?"Selected":"")+"'>"+
		         "<td onMouseDown='onClickList(event,"+i+")'>"+worker.Name+"</td>"+
		         "<td class='Active"+worker.Active+"' onMouseDown='onClickList(event,"+i+")'>"+worker.Active+"</td>"+
		         "<td class='"+worker.State+"' onMouseDown='onClickList(event,"+i+")'>"+worker.State+"</td>"+
		         "<td onMouseDown='onClickList(event,"+i+")'>"+worker.Affinity+"</td>"+
		         "<td onMouseDown='onClickList(event,"+i+")'>"+load+"</td>"+
		         "<td onMouseDown='onClickList(event,"+i+")'>"+memory+"</td>"+
		         "<td onMouseDown='onClickList(event,"+i+")'>"+worker.LastJob+"</td>"+
		         "<td onMouseDown='onClickList(event,"+i+")'>"+worker.Finished+"</td>"+
		         "<td onMouseDown='onClickList(event,"+i+")'>"+worker.Error+"</td>"+
		         "</tr>\n";
	}
	table += "</table>";
	$("#workers").append(table);
	$("#workers").append("<br>");
}

function reloadActivities ()
{
    var _data = {}
    var job = $('#activityJob').attr("value")
    if (job != "")
        _data.job = job
    var worker = $('#activityWorker').attr("value")
    if (worker != "")
        _data.worker = worker
    _data.howlong = $('#howlong').attr("value")
    $.ajax({ type: "GET", url: "/json/getactivities", data: _data, dataType: "json", success: 
        function (data) 
        {
	        activities = [];
	        for (j = 0; j < data.Activities.length; ++j)
	        {
	            var _activities = data.Activities[j];
	            var nw = {};
	            for (i = 0; i < data.Vars.length; ++i)
	            {
	                nw[data.Vars[i]] = _activities[i];
	            }
	            activities.push (nw);
	        }
	        renderActivities ();
            document.getElementById("refreshbutton").className = "refreshbutton";
        }
    });
}

function showActivities ()
{
	$("#jobsTab").hide ();
	$("#workersTab").hide ();
	$("#activitiesTab").show ();
	$("#logsTab").hide ();
	document.getElementById("jobtab").className = "unactivetab";
	document.getElementById("workertab").className = "unactivetab";
	document.getElementById("activitytab").className = "activetab";
	document.getElementById("logtab").className = "unactivetab";

	page = "activities";
	updateTools ();
}

function renderActivities ()
{
	$("#activities").empty ();

	var table = "<table id='activitiesTable'>";
	table += "<tr class='title'>\n";

	// Returns the HTML code for a worker title column
	function addTitleHTML (attribute)
	{
        table += "<th class='headerCell' onclick='"+"setActivityKey(\""+attribute+"\")'>";	
		var value = activities[0];
		if (value && value[attribute] != null)
		{
			table += attribute;
			if (attribute == activitiesSortKey && activitiesSortKeyToUpper)
				table += " &#8595;";
			if (attribute == activitiesSortKey && !activitiesSortKeyToUpper)
				table += " &#8593;";
		}
		else
			table += attribute;
		table += "</th>";
	}

    addTitleHTML ("Start");
    addTitleHTML ("JobID");
    addTitleHTML ("JobTitle");
    addTitleHTML ("State");
    addTitleHTML ("Worker");
    addTitleHTML ("Duration");

	table += "</tr>\n";

	function _sort (a,b)
	{
		var aValue = a[activitiesSortKey];
		if (typeof aValue == 'string')
			return compareStrings (aValue, b[activitiesSortKey], activitiesSortKeyToUpper);
		else
			return compareNumbers (aValue, b[activitiesSortKey], activitiesSortKeyToUpper);
	}

	activities.sort (_sort);

	for (i=0; i < activities.length; i++)
	{
		var activity = activities[i];

		date = formatDate (activity.Start);
		dura = formatDuration (activity.Duration);

        var mouseDownEvent = "onMouseDown='onClickList(event,"+i+")' onDblClick='onDblClickList(event,"+i+")'";
		table += "<tr id='activitytable"+i+"' "+mouseDownEvent+" class='entry"+(i%2)+(selectedActivities[activity.ID]?"Selected":"")+"'>"+
		// table += "<tr id='activitytable"+i+"' class='entry"+(i%2)+(selectedActivities[activity.ID]?"Selected":"")+"'>"+
		         "<td>"+date+"</td>"+
		         "<td>"+activity.JobID+"</td>"+
		         "<td>"+activity.JobTitle+"</td>"+
		         "<td class='"+activity.State+"'>"+activity.State+"</td>"+
		         "<td>"+activity.Worker+"</td>"+
		         "<td>"+dura+"</td>"+
		         "</tr>\n";
	}

	// Footer
	table += "<tr class='title'>";
	table += addSumEmpty ("TOTAL");
	table += addSumSimple (activities);
	table += addSumEmpty ();
	table += addSumFinished (activities, "State");
	table += addSumEmpty ();
	table += addSumAvgDuration (activities, "Duration");
	table += "</tr>\n";

	table += "</table>";
	$("#activities").append(table);
	$("#activities").append("<br>");
}

var JobProps =
[
    [ "Title", "title", "" ],
    [ "Command", "cmd", "" ],
    [ "Dir", "dir", "." ],
    [ "Priority", "priority", "1000" ],
    [ "Affinity", "affinity", "" ],
    [ "TimeOut", "timeout", "0" ],
    [ "Dependencies", "dependencies", "" ],
    [ "Retry", "retry", "10" ],
    [ "User", "user", "" ],
    [ "URL", "url", "" ]
];
var updatedJobProps = {}

function onchangejobprop (prop)
{
    updateSelectionProp (updatedJobProps, JobProps, prop);
}

function updatejobs ()
{
    sendSelectionPropChanges (jobs, 'ID', updatedJobProps, JobProps, "/json/updatejobs", selectedJobs,
        function ()
        {
            reloadJobs ();
            updateJobProps ();
        }
    );
}

function addjob ()
{
    var _data = {
        title:$('#title').attr("value"),
        cmd:$('#cmd').attr("value"),
        dir:$('#dir').attr("value"), 
        priority:$('#priority').attr("value"), 
        retry:$('#retry').attr("value"),
        timeout:$('#timeout').attr("value"),
        affinity:$('#affinity').attr("value"),
        dependencies:$('#dependencies').attr("value"),
        user:$('#user').attr("value"),
        url:$('#url').attr("value"),
        parent:viewJob
    };
    $.ajax({ type: "GET", url: "/xmlrpc/addjob", data: _data, dataType: "json", success: 
        function () 
        {
    		setSelectionDefaultProperties (JobProps);
            reloadJobs ();
        }
    });
}

function selectJobs ()
{
    var tag = document.getElementById("selectJobs").value;
    if (tag == "CUSTOM")
        ;
    else if (tag == "NONE")
        selectAll (false);
    else if (tag == "ALL")
        selectAll (true);
    else
        selectAll (true, tag);
}

function onDblClickList (e, i)
{
    if (page == "activities")
    {
        var activity = activities[i];
	    renderLog (activity.JobID);
    }
    else
    {
        var job = jobs[i];
	    job.Command != "" ? renderLog (job.ID) : goToJob (job.ID);
	}
}

// List selection handler
function onClickList (e, i)
{
    if (!e) var e = window.event
    
    document.getElementById("selectJobs").value = "CUSTOM";
    
	// Unselect if not ctrl keys
	if (!e.ctrlKey)
	{
        if (page == "jobs")
        {
            selectedJobs = {};
        }
        else if (page == "workers")
            selectedWorkers = {};
        else if (page == "activities")
            selectedActivities = {};
    }

    var thelist;
    var selectedList;
    var idName;
    var tableId;
    if (page == "jobs")
    {
        thelist = jobs;
        selectedList = selectedJobs;
        idName = "ID";
        tableId = "jobtable";
    }
    else if (page == "workers")
    {
        thelist = workers;
        selectedList = selectedWorkers;
        idName = "Name";
        tableId = "workertable";
    }
    else if (page == "activities")
    {
        thelist = activities;
        selectedList = selectedActivities;
        idName = "ID";
        tableId = "activitytable";
    }
    else
        return;
    
	// Unselect if not ctrl keys
	if (!e.ctrlKey)
	{
		for (j=0; j < thelist.length; j++)
			document.getElementById(tableId+j).className = "entry"+(j%2);
	}

	var begin = e.shiftKey ? Math.min (selectionStart, i) : i
	var end = e.shiftKey ? Math.max (selectionStart, i) : i

	selectionStart = e.shiftKey ? selectionStart : i;

	for (j = begin; j <= end; j++)
	{
		var item = thelist[j];
		if (item)
		{
			var selected = e.ctrlKey ? !selectedList[item[idName]] : true;
			selectedList[item[idName]] = selected;
			document.getElementById(tableId+j).className = "entry"+(j%2)+(selected?"Selected":"");
		}
	}
	
    if (page == "jobs")         { updateJobProps (); }
    else if (page == "workers") { updateWorkerProps (); }

    // Remove selection
    window.getSelection ().removeAllRanges();
}

function selectAll (state, filter)
{
    var thelist;
    var selectedList;
    var idName;
    var tableId;
    if (page == "jobs")
    {
        thelist = jobs;
        selectedJobs = {};
        selectedList = selectedJobs;
        idName = "ID";
        tableId = "jobtable";
    }
    else if (page == "workers")
    {
        thelist = workers;
        selectedWorkers = {};
        selectedList = selectedWorkers;
        idName = "Name";
        tableId = "workertable";
    }
    else
        return;
        
    if (!state)
    {
	    for (j=0; j < thelist.length; j++)
   			document.getElementById(tableId+j).className = "entry"+(j%2);
    }
    else
    {        
	    for (j=0; j < thelist.length; j++)
	    {
		    var item = thelist[j];
		    if (filter == null || item.State == filter)
		    {
		        selectedList[item[idName]] = true;
   			    document.getElementById(tableId+j).className = "entry"+(j%2)+"Selected";
   			}
   			else
   			{
		        selectedList[item[idName]] = false;
   			    document.getElementById(tableId+j).className = "entry"+(j%2);
   			}
	    }
    }
    
    if (page == "jobs")         { updateJobProps (); }
    else if (page == "workers") { updateWorkerProps (); }
}

function removeSelection ()
{
	if (confirm("Do you really want to remove the selected jobs ?"))
	{
	    var _data = "";
		for (j=jobs.length-1; j >= 0; j--)
		{
			var job = jobs[j];
			if (selectedJobs[job.ID])
			    _data += "id="+str(job.ID)+"&";
		}
        $.ajax({ type: "GET", url: "/json/clearjobs", data: _data, dataType: "json", success: 
            function () 
            {
        		selectedJobs = {};
        	    reloadJobs ();
        	    updateJobProps ();
            }
        });
	}
}

function startSelection ()
{
    var _data = "";
	for (j=jobs.length-1; j >= 0; j--)
	{
		var job = jobs[j];
		if (selectedJobs[job.ID])
		    _data += "id="+str(job.ID)+"&";
	}
    $.ajax({ type: "GET", url: "/json/startjobs", data: _data, dataType: "json", success: 
        function () 
        {
    	    reloadJobs ();
        }
    });
}

function viewSelection()
{
    var _data = "";
	for (j=jobs.length-1; j >= 0; j--)
	{
		var job = jobs[j];
		if (selectedJobs[job.ID] && job.URL)
		    window.open(job.URL);
	}
}

function resetSelection ()
{
	if (confirm("Do you really want to reset the selected jobs and all their children jobs ?"))
	{
	    var _data = "";
		for (j=jobs.length-1; j >= 0; j--)
		{
			var job = jobs[j];
			if (selectedJobs[job.ID])
			    _data += "id="+str(job.ID)+"&";
		}
        $.ajax({ type: "GET", url: "/json/resetjobs", data: _data, dataType: "json", success: 
            function () 
            {
        	    reloadJobs ();
            }
        });
	}
}

function resetErrorSelection ()
{
	if (confirm("Do you really want to reset the selected jobs and all their children jobs tagged in ERROR ?"))
	{
	    var _data = "";
		for (j=jobs.length-1; j >= 0; j--)
		{
			var job = jobs[j];
			if (selectedJobs[job.ID])
			    _data += "id="+str(job.ID)+"&";
		}
        $.ajax({ type: "GET", url: "/json/reseterrorjobs", data: _data, dataType: "json", success: 
            function () 
            {
        	    reloadJobs ();
            }
        });
	}
}

function pauseSelection ()
{
    var _data = "";
	for (j=jobs.length-1; j >= 0; j--)
	{
		var job = jobs[j];
		if (selectedJobs[job.ID])
		    _data += "id="+str(job.ID)+"&";
	}
    $.ajax({ type: "GET", url: "/json/pausejobs", data: _data, dataType: "json", success: 
        function () 
        {
    	    reloadJobs ();
        }
    });
}

function updateJobProps ()
{
    updatedJobProps = checkSelectionProperties (jobs, JobProps, selectedJobs, "ID");
}

function exportCSV()
{
	window.open('csv.html?id=' + viewJob);
}

function cutSelection ()
{
    cutJobs = {}
	for (j=jobs.length-1; j >= 0; j--)
	{
		var job = jobs[j];
		if (selectedJobs[job.ID])
		{
		    cutJobs[job.ID] = true
        }
	}
	selectAll (false)
}

function pasteSelection ()
{
    var _data = "dest="+str(viewJob)+"&";
    var count = 0;
	for (var id in cutJobs)
	{
	    _data += "id="+str(id)+"&";
    }

    $.ajax({ type: "GET", url: "/json/movejobs", data: _data, dataType: "json", success: 
        function () 
        {
    	    reloadJobs ();
        }
    });
}
