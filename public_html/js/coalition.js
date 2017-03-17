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
var MultipleSelection = {}
var workers = [];
var parents = [];
var activities = [];
var affinities = [];
var configJobFilter = [];
var configJobSqlFilterParameters = ["id", "title", "user", "state", "priority", "progress", "affinity", "worker", "start_time", "command", "dependencies"];
var jobsSortKey = "id";
var jobsSortKeyToUpper = true;
var workersSortKey = "name";
var workersSortKeyToUpper = true;
var activitiesSortKey = "start";
var activitiesSortKeyToUpper = false;
var selectionStart = 0;
var showTools = true;
var controlKeyPressed = false;
var JobProps =
  [
    [ "title", "title", "" ],
    [ "command", "cmd", "" ],
    [ "dir", "dir", "." ],
    [ "priority", "priority", "127" ],
    [ "affinity", "affinity", "" ],
    [ "timeout", "timeout", "0" ],
    [ "dependencies", "dependencies", "" ],
    [ "user", "user", "" ],
    [ "url", "url", "" ],
    [ "environment", "env", "" ]
  ];
var updatedJobProps = {}
var WorkerProps = [ [ "affinity", "waffinity", "" ], ];
var updatedWorkerProps = {}
var jobsTheadBuilt = false;

/* On document ready */
$(document).ready(function() {
  reloadJobs ();
  reloadWorkers ();
  reloadActivities ();
  showPage ("jobs");
  timer=setTimeout(timerCB,4000);
  // prevent page reload during ajax request
  $("#job-sql-search").on("submit", function(e) {
    e.preventDefault();
    getSqlWhereJobs($(this));
  });
});

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
  renderJobs (jobs);
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

var tabs =
  [
    [ "jobs", "#jobsTab", "jobtab" ],
    [ "workers", "#workersTab", "workertab" ],
    [ "activities", "#activitiesTab", "activitytab" ],
    [ "logs", "#logsTab", "logtab" ],
    [ "affinities", "#affinitiesTab", "affinitytab" ]
  ]

function showTab (tab)
{
  for (i=0; i<tabs.length; ++i)
  {
    tabdef = tabs[i];
    if (tabdef[0] == tab)
    {
      $(tabdef[1]).show ();
      $("#"+tabdef[2]).addClass("activetab");
      $("#"+tabdef[2]).removeClass("unactivetab");
    }
    else
    {
      $(tabdef[1]).hide ();
      $("#"+tabdef[2]).addClass("unactivetab");
      $("#"+tabdef[2]).removeClass("activetab");
    }
  }
}

function showPage (thepage)
{
  page = thepage;
  showTab (page);
  updateTools ();
}

function clearLog ()
{
  $("#logs").empty ();
}

function renderLog (jobId)
{
  showPage ("logs");
  logId = jobId;
  $.ajax({ type: "GET", url: "/api/jobs/"+jobId+"/log", dataType: "json", success: 
    function (data) 
    {
      $("#logs").empty();
      $("#logs").append("<pre class='logs'><h2>Logs for job "+jobId+":</h2>"+data+"</pre>");

      page = "logs";
      updateTools ();
      //document.getElementById("refreshbutton").className = "refreshbutton";
    }
  });
}

function getSelectedWorkers ()
{
  var data = [];
  for (j=workers.length-1; j >= 0; j--)
  {
    var name = workers[j].name;
    if (selectedWorkers[name])
      data.push (name);
  }
  return data;
}

function clearWorkers ()
{
  if (confirm("Do you really want to delete the selected workers?"))
  {
    $.ajax({ type: "DELETE", url: "/api/workers", data: JSON.stringify(getSelectedWorkers ()), dataType: "json", success: 
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
  //document.getElementById("refreshbutton").className = "refreshing";
  if (page == "jobs")
    reloadJobs ();
  else if (page == "workers") 
    reloadWorkers ();
  else if (page == "activities") 
    reloadActivities ();
  else if (page == "logs") 
    renderLog (logId);
  else if (page == "affinities") 
    renderAffinities ();
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

function renderParents ()
{
  $("#parents").empty ();
  for (i=0; i < parents.length; i++)
  {
    var parent = parents[i];
    $("#parents").append((i == 0 ? "" : " > ") + ("<a href='javascript:goToJob("+parent.id+")'>" + parent.title + "</a>"));
  }
}

// Render the current jobs
function renderJobs (jobsCurrent=[]) {
  if (jobsCurrent.length) jobs = jobsCurrent;
  
  var table = '<table id="jobsTable">';

  function _sort (a,b) {
    if (jobsSortKey == "Progress")
    {
      var progressA = a.progress;
      var progressB = b.progress;
      return compareNumbers (progressA, progressB, jobsSortKeyToUpper);
    }
    else
    {
      var aValue = a[jobsSortKey];
      if (typeof aValue == "string")
        return compareStrings (aValue, b[jobsSortKey], jobsSortKeyToUpper);
      else
        return compareNumbers (aValue, b[jobsSortKey], jobsSortKeyToUpper);
    }
  }

  if (jobs.length) jobs.sort (_sort);

  // Returns the HTML code for a job title column
  function addTitleHTMLEx (attribute, alias, input, min, max) {
    console.log(attribute, alias);
    table += '<th class="headerCell" data-key=\''+attribute+'\'>';
    table += '<div class="flex-column">';
		table += '<div class="flex-row">';
    table += '<label onclick="setJobKey(\''+attribute+'\')">';
    var value = jobs[0];
    if (value) {
      table += alias+'</label>';
      if (attribute == jobsSortKey && jobsSortKeyToUpper)
        table += '<div class="sort-arrow">&#8595;</div></div>';
      if (attribute == jobsSortKey && !jobsSortKeyToUpper)
        table += '<div class="sort-arrow">&#8593;</div></div>';
    } else {
      table += alias+"</label></div>";
    }
    if (input) {
      var nodeSelector = '.headerCell[data-key=\''+attribute+'\']>div.flex-column';
      switch (input) {
        case "search":
          table += buildInputForField(nodeSelector, "job-sql-search", attribute, input);
          break;
        case "checkbox":
          var select = buildSelectForField(nodeSelector, "job-sql-search", attribute, input);
          if (select) {
            table += select; // otherwise it's filled by ajax
          }
          break;
        case "datetime-local":
          buildDatetimeForField(nodeSelector, "job-sql-search", attribute, input);
          break;
        case "range":
          buildRangeForField(nodeSelector, "jobs-sql-search", attribute, input);
          attachRangeEventForField(nodeSelector, attribute, min, max);
          break;
        default:
          break;
      }
    }
    table += "</th>";
  }

  function addTitleHTML (attribute, alias, input=null, min=0, max=0) {
    addTitleHTMLEx (attribute, alias, input, min, max)
  }

  table += "<thead>";
  table += "<tr class='title'>";
  //addTitleHTML ("Order");
  addTitleHTML ("id", "id", "search");
  addTitleHTML ("title", "title", "search");
  addTitleHTML ("url", "url");
  addTitleHTML ("user", "user", "checkbox");
  addTitleHTML ("state", "state", "checkbox");
  addTitleHTML ("priority", "priority", "search");
  addTitleHTMLEx ("total_finished", "ok");
  addTitleHTMLEx ("total_working", "wrk");
  addTitleHTMLEx ("total_errors", "err");
  addTitleHTML ("total", "total");
  addTitleHTML ("progress", "progress", "range", "0", "100");
  addTitleHTML ("affinity", "affinity", "search");
  addTitleHTML ("timeout", "timeout");
  addTitleHTML ("worker", "worker", "search");
  addTitleHTML ("start_time", "start time", "datetime-local");
  addTitleHTML ("duration", "duration");
  addTitleHTML ("run", "run");
  addTitleHTML ("command", "command", "search");
  addTitleHTML ("dir", "dir");
  addTitleHTML ("dependencies", "dependencies", "search");
  table += "</tr>";
  table += "</thead>";

  table += "<tbody>";
  for (i=0; i < jobs.length; i++) {
    var job = jobs[i];

    var mouseDownEvent = 'onMouseDown="onClickList(event,'+i+')" onDblClick="onDblClickList(event,'+i+')"';

    table += '<tr id="jobtable'+i+'" '+mouseDownEvent+' class="entry'+(i%2)+(selectedJobs[job.id]?'Selected':'')+'">';
    function addTD (attr) {
      table += "<td>" + attr + "</td>";
    }
    //addTD (job.Order);
    addTD (job.id);
    table += "<td>" + job.title + "</td>\n";

    // url
    if (job.url != "")
      addTD ('<a href="'+job.url+'">Open</a>')
    else
      addTD ("")

    // check group state!
    var	mystate = job.paused ? "PAUSED" : job.state;

    addTD (job.user);
    table += '<td class="'+mystate+'">'+mystate+'</td>';
    addTD (job.priority);
    if (job.total > 0)
    {
      table += '<td class="'+(job.total_finished > 0 ? 'FINISHED' : 'WAITING')+'" width=30>'+job.total_finished+'</td>';
      table += '<td class="'+(job.total_working > 0 ? 'WORKING' : 'WAITING')+'" width=30>'+job.total_working+'</td>';
      table += '<td class="'+(job.total_errors > 0 ? 'ERROR' : 'WAITING')+'" width=30>'+job.total_errors+'</td>';
      table += '<td class="'+(job.total == job.total_finished ? 'FINISHED' : 'WAITING')+'" width=30>'+job.total+'</td>';
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
    var _progress = job.progress
    _progress = Math.floor(_progress*100.0);

    // A bar div
    progress = '<div class="progress">';
    progress += '<div class="lprogressbar" style="width:' + _progress + '%" />';
    progress += '<div class="progresslabel">' + _progress + '%</div>';
    progress += '</div>';

    addTD (progress);
    addTD (job.affinity);
    addTD (job.timeout);
    addTD (job.worker);
    addTD (job.start_time > 0 ? formatDate (job.start_time) : "");
    addTD (formatDuration (job.duration));
    addTD (job.run_done);
    addTD (job.command);
    addTD (job.dir);
    addTD (job.dependencies);

    table += "</td></tr>\n";
  }
  table += "</tbody>";

  // Footer
  table += "<tfoot>";
  table += '<tr class="title">';
  table += addSumEmpty ();
  table += addSumSimple (jobs);
  table += addSumEmpty ();
  table += addSumEmpty ();
  table += addSumFinished (jobs, "state");
  table += addSumEmpty ();
  table += addSum (jobs, "total_finished");
  table += addSum (jobs, "total_working");
  table += addSum (jobs, "total_errors");
  table += addSum (jobs, "total");
  table += addSumEmpty ();
  table += addSumEmpty ();
  table += addSumEmpty ();
  table += addSumEmpty ();
  table += addSumEmpty ();
  table += addSumAvgDuration (jobs, "duration");
  table += addSumEmpty ();
  table += addSumEmpty ();
  table += addSumEmpty ();
  table += addSumEmpty ();
  table += "</tr>";
  table += "</tfoot>";
  table += "</table>";

  $.when($("#jobs").html(table)).then(function () {
    configLoad("job-filter");
    jobsTheadBuilt = true;
  });
}

function logSelection ()
{
  for (j=jobs.length-1; j >= 0; j--)
  {
    var job = jobs[j];
    if (selectedJobs[job.id])
      renderLog (job.id);
  }
}

// Set the global variable 'jobs' variable
// filters for state, affinity and title are removed since the sql search is implemented.
function reloadJobs () {
  parents = [];
  switch (viewJob) {
    case 0: // Root job
      jobs = getSqlWhereJobs();
      break;
    default: // Show viewJob children 
      $.ajax({ type: "GET", url: "/api/jobs/"+viewJob+"/children", dataType: "json", success: 
        function(jobs) {
          jobs = jobs;
          var	idtojob = {}
          for (i=0; i<jobs.length; ++i) {
            var job = jobs[i];
            idtojob[job.id] = job;
            job.dependencies = [];
          }
          $.ajax({ type: "GET", url: "/api/jobs/"+viewJob+"/childrendependencies", dataType: "json", success: 
            function(data) {
              for (var i=0; i<data.length; ++i) {
                var	job = idtojob[data[i].id];
                if (job)
                  job.dependencies.push(data[i].dependency);
              }
              for (var i=0; i<jobs.length; ++i) {
                var	job = jobs[i];
                job.dependencies = job.dependencies.join (",");
              }
              renderJobs (jobs);
            }
          });
        }
      });
      break;
  }

  function getParent(id) {
    if (id == 0) {
      parents.unshift({id:0,title:"Root"});
      renderParents();
    } else {
      $.ajax({ type: "GET", url: "/api/jobs/"+id, dataType: "json", success: 
        function(data) 
        { 
          parents.unshift(data);
          getParent(data.parent);
        }
      });
    }
  }
  getParent (viewJob)
}

function startWorkers ()
{
  $.ajax({ type: "POST", url: "/api/startworkers", data: JSON.stringify(getSelectedWorkers ()), dataType: "json", success: 
    function () 
    {
      reloadWorkers ();
    }
  });
}

function stopWorkers ()
{
  $.ajax({ type: "POST", url: "/api/stopworkers", data: JSON.stringify(getSelectedWorkers ()), dataType: "json", success: 
    function () 
    {
      reloadWorkers ();
    }
  });
}

function workerActivity ()
{
  for (j=workers.length-1; j >= 0; j--)
  {
    var worker = workers[j];
    if (selectedWorkers[worker.name])
    {
      title:$('#activityWorker').attr("value", worker.name)
      title:$('#activityJob').attr("value", "")
      break;
    }
  }

  reloadActivities ()
  page = "activities"
  showPage ("activities")
}

function terminateWorkers ()
{
  if (confirm("Do you really want to terminate the selected worker instances?"))
  {
    $.ajax({ type: "POST", url: "/api/terminateworkers", data: JSON.stringify(getSelectedWorkers ()), dataType: "json", success: 
      function () 
      {
        reloadWorkers ();
      }
    });
  }
}

function jobActivity ()
{
  for (j=jobs.length-1; j >= 0; j--)
  {
    var job = jobs[j];
    if (selectedJobs[job.id])
    {
      title:$('#activityWorker').attr("value", "")
      title:$('#activityJob').attr("value", job.id)
      break;
    }
  }

  reloadActivities ()
  page = "activities"
  showPage ("activities")
}

function checkSelectionProperties (list, props, selectedList, idName)
{
  var values = [];

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
      $('#'+props[i][1]).val("");
    }
    else if (values[i] == null)
    {
      // default value
      $('#'+props[i][1]).css("background-color", "white");
      $('#'+props[i][1]).attr("value", props[i][2]);
      $('#'+props[i][1]).val(props[i][2]);
    }
    else
    {
      // unique values
      $('#'+props[i][1]).css("background-color", "white");
      $('#'+props[i][1]).attr("value", values[i]);
      $('#'+props[i][1]).val(values[i]);
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

function sendSelectionPropChanges (list, idName, values, props, objects, selectedList, func)
{
  if (!props.length)
    return;

  var data = {};
  var idsN = 0;
  for (j=list.length-1; j >= 0; j--)
  {
    var id = list[j][idName];
    if (selectedList[id]) {
      var _props = {};
      for (i = 0; i < props.length; ++i)
        if (values[i] == true) {
          var prop = props[i][0];
          // var value = $('#'+props[i][1]).attr("value");
          var value = $('#'+props[i][1]).val();
          if (prop == "dependencies")
            value = value.split(",");
          _props[prop] = value;
        }
      data[id] = _props;
      idsN++;
    }
  }
  if (!idsN)
    return;

  // One single call
  $.ajax({ type: "POST", url: "/api/"+objects.toLowerCase(), data: JSON.stringify(data), dataType: "json", success:
    function ()
    {
      for (i = 0; i < props.length; ++i)
        if (values[i] == true)
        {
          props[i][2] = value;
        }
      func (jobs);
    }
  });
}

function setSelectionDefaultProperties (props)
{
  for (i = 0; i < props.length; ++i)
    props[i][2] = $('#'+props[i][1]).attr("value");
}

function updateWorkerProps ()
{
  updatedWorkerProps = checkSelectionProperties (workers, WorkerProps, selectedWorkers, "name");
}

function onchangeworkerprop (prop)
{
  updateSelectionProp (updatedWorkerProps, WorkerProps, prop);
}

function updateworkers ()
{
  sendSelectionPropChanges (workers, 'name', updatedWorkerProps, WorkerProps, "Workers", selectedWorkers,
    function ()
    {
      reloadWorkers ();
    }
  );
}

function reloadWorkers ()
{
  $.ajax({ type: "GET", url: "/api/workers", dataType: "json", success: 
    function (data) 
    {
      workers = data;
      renderWorkers ();
      //document.getElementById("refreshbutton").className = "refreshbutton";
    }
  });
}

function renderWorkers ()
{
  $("#workers").empty ();

  var table = "<table id='workersTable'>";
	table += "<thead>";
  table += "<tr class='title'>\n";

  // Returns the HTML code for a worker title column
  function addTitleHTML (attribute)
  {
    table += '<th class="headerCell">';	
		table += '<div class="flex-column">';
		table += '<div class="flex-row">';
    table += '<label onclick="setWorkerKey(\''+attribute+'\')">';
    var value = workers[0];
    if (value && value[attribute] != null)
    {
      table += attribute+"</label>";
      if (attribute == workersSortKey && workersSortKeyToUpper)
        table += '<div class="sort-arrow">&#8595;</div></div>';
      if (attribute == workersSortKey && !workersSortKeyToUpper)
        table += '<div class="sort-arrow">&#8593;</div></div>';
    }
    else
      table += attribute+"</label>";
    table += '</div>';
    table += "</th>";
  }

  addTitleHTML ("name");
  addTitleHTML ("active");
  addTitleHTML ("state");
  addTitleHTML ("affinity");
  addTitleHTML ("ping_time");
  addTitleHTML ("cpu");
  addTitleHTML ("memory");
  addTitleHTML ("last_job");
  addTitleHTML ("finished");
  addTitleHTML ("error");
  addTitleHTML ("ip");

  table += "</tr>";
  table += "</thead>";
  table += "<tbody>";

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
    // Add each cpu load
    var loadValue = 0;
    try
    {
      var workerload = JSON.parse (worker.cpu)
      for (j=0; j < workerload.length; ++j)
      {
        load += "<div class='loadbar' style='width:" + workerload[j] + "%;height:" + 16/workerload.length + "' />";
        loadValue += workerload[j];
      }
      Math.floor(loadValue/workerload.length);
    }
    catch (err)
    {
      loadValue = 0;
    }
    // Add the numerical value of the load
    load += "<div class='loadlabel'>" + loadValue + "%</div>";
    load += "</div>";

    // *** Build the memory tab for this worker		
    var memory = "<div class='mem'>";
    memory += "<div class='membar' style='width:" + 100*(worker.total_memory-worker.free_memory)/worker.total_memory + "%' />";

    function formatMem (a)
    {
      if (a > 1024)
        return Math.round(a/1024*100)/100 + " GB";
      else
        return a + " Mo";
    }

    memLabel = formatMem (worker.total_memory-worker.free_memory);
    memLabel += " / ";
    memLabel += formatMem (worker.total_memory);

    // Add the numerical value of the mem
    memory += "<div class='memlabel'>" + memLabel + "</div>";
    memory += "</div>";

    table += "<tr id='workertable"+i+"' class='flex-row entry"+(i%2)+(selectedWorkers[worker.name]?"Selected":"")+"'>"+
      "<td onMouseDown='onClickList(event,"+i+")'>"+worker.name+"</td>"+
      "<td class='active"+worker.active+"' onMouseDown='onClickList(event,"+i+")'>"+worker.active+"</td>"+
      "<td class='"+worker.state+"' onMouseDown='onClickList(event,"+i+")'>"+worker.state+"</td>"+
      "<td class='worker_affinities' onMouseDown='onClickList(event,"+i+")'>"+worker.affinity+"</td>"+
      "<td onMouseDown='onClickList(event,"+i+")'>"+formatDate (worker.ping_time)+"</td>"+
      "<td onMouseDown='onClickList(event,"+i+")'>"+load+"</td>"+
      "<td onMouseDown='onClickList(event,"+i+")'>"+memory+"</td>"+
      "<td onMouseDown='onClickList(event,"+i+")'>"+worker.last_job+"</td>"+
      "<td onMouseDown='onClickList(event,"+i+")'>"+worker.finished+"</td>"+
      "<td onMouseDown='onClickList(event,"+i+")'>"+worker.error+"</td>"+
      "<td>"+worker.ip+"</td>"+
      "</tr>\n";
  }
  table += "</tbody>";
  table += "</table>";
  $("#workers").append(table);
}

function reloadActivities ()
{
  var data = {}
  var job = $('#activityJob').prop("value")
  if (job != "")
    data.job = job
  var worker = $('#activityWorker').prop("value")
  if (worker != "")
    data.worker = worker
  data.howlong = $('#howlong').prop("value")
  $.ajax({ type: "GET", url: "/api/events", data: data, dataType: "json", success: 
    function (data) 
    {
      activities = data;
      renderActivities ();
      //document.getElementById("refreshbutton").className = "refreshbutton";
    }
  });
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

  addTitleHTML ("start");
  addTitleHTML ("job_id");
  addTitleHTML ("job_title");
  addTitleHTML ("state");
  addTitleHTML ("worker");
  addTitleHTML ("duration");

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

    date = formatDate (activity.start);
    dura = formatDuration (activity.duration);

    var mouseDownEvent = "onMouseDown='onClickList(event,"+i+")' onDblClick='onDblClickList(event,"+i+")'";
    table += "<tr id='activitytable"+i+"' "+mouseDownEvent+" class='entry"+(i%2)+(selectedActivities[activity.id]?"Selected":"")+"'>"+
      // table += "<tr id='activitytable"+i+"' class='entry"+(i%2)+(selectedActivities[activity.id]?"Selected":"")+"'>"+
      "<td>"+date+"</td>"+
      "<td>"+activity.job_id+"</td>"+
      "<td>"+activity.job_title+"</td>"+
      "<td class='"+activity.state+"'>"+activity.state+"</td>"+
      "<td>"+activity.worker+"</td>"+
      "<td>"+dura+"</td>"+
      "</tr>\n";
  }

  // Footer
  table += "<tr class='title'>";
  table += addSumEmpty ();
  table += addSumSimple (activities);
  table += addSumEmpty ();
  table += addSumFinished (activities, "state");
  table += addSumEmpty ();
  table += addSumAvgDuration (activities, "duration");
  table += "</tr>\n";

  table += "</table>";
  $("#activities").append(table);
  $("#activities").append("<br>");
}

function renderAffinities ()
{
  $("#affinities").empty ();

  var table = "<table id='affinitiesTable'>";
	table += "<thead>";
  table += "<tr class='title'>";

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

  addTitleHTML ("id");
  addTitleHTML ("name");

  table += "</tr>\n";
	table += "</thead><tbody>";

  for (i = 1; i <= 63; ++i)
  {
    table += "<tr>";
    table += "<td width='50px'>"+i+"</td><td width='200px'><input type='edit' class='ttedit' id='affinity"+i+"' name='affinity' value='' onchange='onchangeaffinityprop ("+i+")'></td>"
    table += "</tr>\n";
  }

  updateAffinities ();

  table += "</tbody></table>";
  $("#affinities").append(table);
  $("#affinities").append("<br>");
}

function onchangeaffinityprop (affinity)
{
  $('#affinity'+affinity).css("background-color", "greenyellow");
}

function updateAffinities ()
{
  $.ajax({ type: "GET", url: "/api/affinities", dataType: "json", success: 
    function (data) 
    {
      affinities = data;
      for (i = 1; i <= 63; ++i)
      {
        var def = affinities[i];
        if (def)
          $("#affinity"+i).attr("value", def);
        $("#affinity"+i).css("background-color", "white");
      }
      //document.getElementById("refreshbutton").className = "refreshbutton";
    }
  });
}

function sendAffinities ()
{
  var affinities = {};
  for (i = 1; i <= 63; ++i)
  {
    var affinity = $("#affinity"+i).val();
    if (affinity != null)
      affinities[i] = affinity;
  }

  var data = JSON.stringify(affinities)
  $.ajax({ type: "POST", url: "/api/affinities", data: data, dataType: "json", success: 
    function (data) 
    {
      updateAffinities ();
    }
  });
}

function onchangejobprop (prop)
{
  updateSelectionProp (updatedJobProps, JobProps, prop);
}

function updatejobs ()
{
  sendSelectionPropChanges (jobs, 'id', updatedJobProps, JobProps, "Jobs", selectedJobs,
    function (jobs)
    {
      reloadJobs ();
      updateJobProps (jobs);
    }
  );
}

function addjob ()
{
  dependencies = $.trim($('#dependencies').attr("value"));
  dependencies = dependencies.split(',')
  dependencies = dependencies != "" ? dependencies : []
  var data = {
    title:$('#title').attr("value"),
    command:$('#cmd').attr("value"),
    dir:$('#dir').attr("value"), 
    env:$('#env').attr("value"), 
    priority:$('#priority').attr("value"), 
    timeout:$('#timeout').attr("value"),
    affinity:$('#affinity').attr("value"),
    dependencies:dependencies,
    user:$('#user').attr("value"),
    url:$('#url').attr("value"),
    parent:viewJob
  };
  $.ajax({ type: "PUT", url: "/api/jobs", data: JSON.stringify(data), dataType: "json", success: 
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
  if (page == "activities") {
    var activity = activities[i];
    renderLog (activity.job_id);
  } else {
    var job = jobs[i];
    job.command != "" ? renderLog (job.id) : goToJob (job.id);
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
    idName = "id";
    tableId = "jobtable";
  }
  else if (page == "workers")
  {
    thelist = workers;
    selectedList = selectedWorkers;
    idName = "name";
    tableId = "workertable";
  }
  else if (page == "activities")
  {
    thelist = activities;
    selectedList = selectedActivities;
    idName = "id";
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

  if (page == "jobs") {
    updateJobProps (jobs);
  } else if (page == "workers") {
    updateWorkerProps ();
  }

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
    idName = "id";
    tableId = "jobtable";
  }
  else if (page == "workers")
  {
    thelist = workers;
    selectedWorkers = {};
    selectedList = selectedWorkers;
    idName = "name";
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
      if (filter == null || item.state == filter)
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

  if (page == "jobs") {
    updateJobProps (jobs);
  } else if (page == "workers") {
    updateWorkerProps ();
  }
}

function removeSelection ()
{
  if (confirm("Do you really want to remove the selected jobs ?"))
  {
    var data = [];
    for (j=jobs.length-1; j >= 0; j--)
    {
      var job = jobs[j];
      if (selectedJobs[job.id])
        data.push (job.id);
    }
    $.ajax({ type: "DELETE", url: "/api/jobs", data: JSON.stringify(data), dataType: "json", success: 
      function () 
      {
        selectedJobs = {};
        reloadJobs ();
        updateJobProps (jobs);
      }
    });
  }
}

function startSelection ()
{
  var data = [];
  for (j=jobs.length-1; j >= 0; j--)
  {
    var job = jobs[j];
    if (selectedJobs[job.id])
      data.push (job.id);
  }
  $.ajax({ type: "POST", url: "/api/startjobs", data: JSON.stringify(data), dataType: "json", success: 
    function () 
    {
      reloadJobs ();
    }
  });
}

function viewSelection()
{
  for (j=jobs.length-1; j >= 0; j--)
  {
    var job = jobs[j];
    if (selectedJobs[job.id] && job.url)
      window.open(job.url);
  }
}

function resetSelection ()
{
  if (confirm("Do you really want to reset the selected jobs and all their children jobs ?"))
  {
    var data = [];
    for (j=jobs.length-1; j >= 0; j--)
    {
      var job = jobs[j];
      if (selectedJobs[job.id])
        data.push (job.id);
    }
    $.ajax({ type: "POST", url: "/api/resetjobs", data: JSON.stringify(data), dataType: "json", success: 
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
    var data = [];
    for (j=jobs.length-1; j >= 0; j--)
    {
      var job = jobs[j];
      if (selectedJobs[job.id])
        data.push (job.id);
    }
    $.ajax({ type: "POST", url: "/api/reseterrorjobs", data: JSON.stringify(data), dataType: "json", success: 
      function () 
      {
        reloadJobs ();
      }
    });
  }
}

function pauseSelection ()
{
  var data = [];
  for (j=jobs.length-1; j >= 0; j--)
  {
    var job = jobs[j];
    if (selectedJobs[job.id])
      data.push (job.id);
  }
  $.ajax({ type: "POST", url: "/api/pausejobs", data: JSON.stringify(data), dataType: "json", success: 
    function () 
    {
      reloadJobs ();
    }
  });
}

function updateJobProps (jobs)
{
  updatedJobProps = checkSelectionProperties (jobs, JobProps, selectedJobs, "id");
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
    if (selectedJobs[job.id])
    {
      cutJobs[job.id] = true
    }
  }
  selectAll (false)
}

function pasteSelection ()
{
  var count = 0;
  var data = {}
  for (var id in cutJobs)
    data[id] = {parent:viewJob}
  $.ajax({ type: "POST", url: "/api/jobs", data: JSON.stringify(data), dataType: "json", success: 
    function () 
    {
      reloadJobs ();
    }
  });
}

/* Jobs SQL requests */

function buildInputForField(nodeSelector, form, field, type, min, max) {
  switch (type) {
    case "number":
      //var content = '<input form="'+form+'" class="sql-input" id="job-filter-'+field+'" type="'+type+'" value="'+values'" data-min="'+min+'" data-max="'+max+'" onKeyDown="checkJobSqlInputChange(\''+field+'\', event)">';
      //case "datetime":
      //var content = '<div id="datepair">
      //<input 'form="'+form+'" type="text" id="job-filter-start-date" class="date start"/>\
      //<input 'form="'+form+'" type="text" id="job-filter-start-time" class="time start"/> to \
      //<input 'form="'+form+'" type="text" id="job-filter-end-date" class="date end"/>\
      //<input 'form="'+form+'" type="text" id="job-filter-end-time" class="time end"/>\
      //</div>';
    default:
      //var content = '<input form="'+form+'" class="sql-input" id="job-filter-'+field+'" type="'+type+'" value="'+values+'" onKeyDown="checkJobSqlInputChange(\''+field+'\', event)">';
      var content = '<input form="'+form+'" class="sql-input" id="job-filter-'+field+'" type="'+type+'" onKeyDown="checkJobSqlInputChange(\''+field+'\', event)">';
  }
  return '<div class="job-sql-search-field">'+content+'</div>';
}

function buildSelectForField(nodeSelector, form, field, type) {
  // Prevent ajax if head has been previously built
  if (jobsTheadBuilt) {
    return '<div class="job-sql-search-field">'+$(nodeSelector+" .job-sql-search-field").html()+'</div>';
  }

  var items;
  switch (field) {
    case "user":
      ajax = getAjaxJobsUsers();
      break;
    case "state":
      ajax = getAjaxJobsStates();
      break;
  }
  ajax.done(function(items) {
    var content = '<select form="'+form+'" class="sql-input" id="job-filter-'+field+'"';
    content += ' form="sql-select" multiple';
    content += ' onclick="checkJobSqlInputChange(\''+field+'\', event)"';
    content += ' onkeydown="checkJobSqlInputChange(\''+field+'\', event)"';
    content += ' onkeyup="checkJobSqlInputChange(\''+field+'\', event)">';
    for (i=0; i < items.length; i++) {
      var item = items[i][field];
      content += '<option value="'+item+'">'+item+'</option>';
    }   
    content += '</select>';
    //$(nodeSelector).append('<div class="job-sql-search-field" onmouseenter="toggleSearchField(this)" onmouseleave="toggleSearchField(this)">'+content+'</div>');
    $(nodeSelector).append('<div class="job-sql-search-field">'+content+'</div>');
  });
  return false;
}

function buildDatetimeForField(nodeSelector, form, field, type) {
  content = "";
  return '<div class="job-sql-search-field">'+content+'</div>';
}

function buildRangeForField(nodeSelector, form, field, type, min, max) {
  content = '<input form="'+form+'" id="job-filter-'+field+'" type="'+type+'">';
  content += '<div id="job-filter-'+field+'-values"></div>';
  return '<div class="job-sql-search-field">'+content+'</div>';
}

function attachRangeEventForField(nodeSelector, field, min, max) {
  $(nodeSelector).slider({
    range: true,
    min: min,
    max: max,
    values: [min, max],
    slide: function(event, ui) {
      $('job-filter-'+field+'-values').val($(nodeSelector).slider("values", 0)+'-'+$(nodeSelector).slider("values", 1));
    }
  });
}

function toggleSearchField(node) {
  var node = $(node).children(".job-sql-search-field");
  if (node.css("visibility") == "hidden") {
    node.css("visibility", "visible");
    node.children("select, input").focus();
  } else {
    node.css("visibility", "hidden");
    node.children("select, input").blur();
  }
}

function checkJobSqlInputChange(field, event) {
  var keyCodeEnter = 13;
  var keyCodeControl = 17;
  switch (event.type) {
    case "click":
      if (!controlKeyPressed) // single selection
        $("#job-sql-search").submit();
      break;
    case "keydown":
      switch (event.keyCode) {
        case keyCodeEnter:
          $("#job-sql-search").submit();
          break;
        case keyCodeControl:
          controlKeyPressed = true;
          break;
      }
      break;
    case "keyup":
      // multiple selection
      if (event.keyCode != keyCodeControl) break; // not <control>
      controlKeyPressed = false;
      var itemName = "#job-filter-"+field;
      var values = $(itemName).val();
      if (values != configGet(itemName)) // the selection changed
        $("#job-sql-search").submit();
      break;
  }
}

function getAjaxJobsUsers() {
  return $.ajax({
    type: "GET",
    url: "/api/jobs/users/",
    dataType: "json",
  })
}

function getAjaxJobsStates() {
  return $.ajax({
    type: "GET",
    url: "/api/jobs/states/",
    dataType: "json",
  })
}

function getAjaxSqlWhereCountJobs(where_clause) {
  return $.ajax({
    type: "GET",
    url: "/api/jobs/count/where/",
    data: {where_clause: where_clause},
    dataType: "json",
  })
}

function getAjaxSqlWhereJobs(data) {
  return $.ajax({
    type: "GET",
    url: "/api/jobs/where/",
    data: data,
    datatype: "json",
  })
}

function getSqlWhereJobs() {
  if (jobsTheadBuilt) configSave();
  else configLoad();
  // Limit search to children of viewJob
  var sql = "(parent = "+viewJob+")";

  for (i in configJobFilter) {
    key = configJobFilter[i][0];
    values = configJobFilter[i][1];
    if (typeof(values) == "string") values = [values]
    // build sql clause
    switch (key) {
      case "id":
      case "priority":
      case "dependencies":
        if (values[0] == "" && values.length == 1) break;
        sql += " and (";
        for (j in values) {
          var value = values[j];
          if (!value) continue;
          sql += key+"="+value;
          if (j+1<values.length) sql += " or ";
        }
        sql += ")";
        break;
      case "user":
      case "state":
        if (values.length == 0 || values[0] == undefined) break;
        sql += " and (";
        for (j in values) {
          var value = values[j];
          sql += key+"='"+value+"'";
          if (j+1<values.length) sql += " or ";
        }
        sql += ")";
        break;
      case "progress":
        values = data[i].value;
        break;
      case "affinity":
      case "title":
      case "worker":
      case "command":
        if (values[0] == "" && values.length == 1) break;
        sql += " and (";
        for (j in values) {
          var value = values[j].trim();
          if (!value) continue;
          sql += key+" like '%"+value+"%'"
          if (j+1<values.length) sql += " or ";
        }
        sql += ")";
        break;
      case "start_time":
        values = data[i].value;
        break;
    }
  }
  getAjaxSqlWhereCountJobs(sql).done(function(total) {
    if (total) {
      //if (total <= max_batch) {
      if (true) {
        data = {where_clause: sql, min: 0, max: 1000000000};
        getAjaxSqlWhereJobs(data).done(function(jobs) {
          jobs = JSON.parse(jobs);
          renderJobs(jobs);
        });
      } else {
        var batches = Math.round(total / max_batch);
        for (i = 0; i <= batches; i++) {
          min = i * max_batch;
          max = (i + 1) * max_batch - 1;
          data = {where_clause: sql, min: min, max: max};
          button = '<button type="button" onclick="getSqlWhereJobs($(this).data())">'+min+'-'+max+'</button>'
          $("#pagination").append(button);
          $("#pagination button").last().data(data);
          getAjaxSqlWhereJobs(data).done(function(jobs) {
            dataViewjobs.setItems(JSON.parse(jobs));
          });
        }
      }
    } else {
      jobs = [];
      renderJobs(jobs);
    }
  })
}


/* localstorage functions */
function configSave(category="job-filter") {
  // Save configuration in browser local storage
  switch (category) {
    case "job-filter":
      configJobFilter = [];
      for (i in configJobSqlFilterParameters) {
        var param = configJobSqlFilterParameters[i];
        var nodeId = category+'-'+param;
        var value = $('#'+nodeId).val();
        localStorage.setItem(nodeId, value);
        if (value) configJobFilter.push([param, value]);
      }
  }
}

function configGet(itemName) {
  // Get stored item 
  config = localStorage.getItem(itemName);
  return (config != "undefined") ? config : "";
}

function configLoad(category="job-filter") {
  switch (category) {
    case "job-filter":
      configJobFilter = [];
      for (i in configJobSqlFilterParameters) {
        var param = configJobSqlFilterParameters[i];
        var value = configGet(category+'-'+param);
        if (value) {
          value = value.split(",");
          var nodeId = category+'-'+param;
          $('#'+nodeId).val(value);
          configJobFilter.push([param, value]);
        }
      }
      break;
  }
  return false;
}

function configDefinedFor(category="job-filter") {
  // return true if the configuration is not empty for the provided category
  switch (category) {
    case "job-filter":
      for (i in configJobSqlFilterParameters) {
        var param = configJobSqlFilterParameters[i];
        var value = configGet(category+'-'+param);
        if (value) {
          return true;
        }
      }
      break;
  }
  return false;
}

function configReset() {
  localStorage.clear();
}

function resetSqlFilter() {
  // Empty form filter data and save configuration
  jobsTheadBuilt = false;
  configJobFilter = false;
  form = $("#job-sql-search")[0];
  form.reset();
  for (i = 0; i < form.length; i++) {
    form[i].value = null;
  }
  configSave();
} 

