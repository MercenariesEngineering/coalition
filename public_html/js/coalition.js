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
var configJobSqlFilterParameters = ["id", "title", "user", "state", "priority", "progress", "affinity", "worker", "start_time", "command", "dependencies"];
var jobsSortKey = "id";
var jobsSortKeyToUpper = false;
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
var tabs = [
    [ "jobs", "#jobsTab", "jobtab" ],
    [ "workers", "#workersTab", "workertab" ],
    [ "activities", "#activitiesTab", "activitytab" ],
    [ "logs", "#logsTab", "logtab" ],
    [ "affinities", "#affinitiesTab", "affinitytab" ]
  ]

/* On document ready */
$(document).ready(function() {
  configTableGetConfigFromUrl();
  reloadActivities ();
  showPage ("jobs");
  timer=setTimeout(timerCB,4000);
  renderLogoutButton();
});

function setSortKey(event, id) {
  var table = configTableGetActiveTable();
  var sortKey = configTableGetSortKeyFromStorage(table);
  var th = event.target.parentElement.parentElement.parentElement;
  // Prevent sorting jobstable by dependencies
  if (table.id === "jobsTable" && th.dataset.key === "dependencies") {
    return;
  }
  if (sortKey["sortKey"] === th.dataset.key) {
    if (sortKey["sortKeyToUpper"]) {
      var config = configTableSetConfig(table, th.dataset.key, "sortkey", "down");
    } else {
      var config = configTableSetConfig(table, th.dataset.key, "sortkey", "up");
    }
  } else {
    var config = configTableSetConfig(table, th.dataset.key, "sortkey", "down");
  }
  configTableSetConfigToStorage(table, config);
  document.getElementById("submit-sql-search-"+table.id).click();
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

function showTab (tab)
{
  for (i=0; i<tabs.length; ++i)
  {
    tabdef = tabs[i];
    if (tabdef[0] == tab)
    {
      $(tabdef[1]).show ();
      $(tabdef[1]).addClass("active-tab-content");
      $("#"+tabdef[2]).addClass("activetab");
      $("#"+tabdef[2]).removeClass("unactivetab");
    }
    else
    {
      $(tabdef[1]).hide ();
      $(tabdef[1]).removeClass("active-tab-content");
      $("#"+tabdef[2]).addClass("unactivetab");
      $("#"+tabdef[2]).removeClass("activetab");
    }
  }
  if (tab === "affinities") {
    refresh();
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
  $.ajax({ type: "GET", url: "/api/webfrontend/jobs/"+jobId+"/log", dataType: "json", success:
    function (data)
    {
      $("#logs").empty();
      $("#logs").append("<pre class='logs'><h2>Logs for job "+jobId+":</h2>"+data+"</pre>");
      page = "logs";
      updateTools ();
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
        $.ajax({ type: "DELETE", url: "/api/webfrontend/workers", data: JSON.stringify(getSelectedWorkers ()), dataType: "json", success:
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
  return date.getUTCFullYear() + '-' + (date.getUTCMonth()+1) + '-' + date.getUTCDate() + ' ' + date.getUTCHours () + ':' + date.getUTCMinutes () + ':' + date.getUTCSeconds();
}

function formatDuration (secondes)
{
  var days = Math.floor (secondes / (60*60*24));
  var hours = Math.floor ((secondes-days*60*60*24) / (60*60));
  var minutes = Math.floor ((secondes-days*60*60*24-hours*60*60) / 60);
  var secondes = Math.floor (secondes-days*60*60*24-hours*60*60-minutes*60);
  if (days > 0)
    return days + "d " + hours + "h " + minutes + "m " + secondes + "s";
  if (hours > 0)
    return hours + "h " + minutes + "m " + secondes + "s";
  if (minutes > 0)
    return minutes + "m " + secondes + "s";
  return secondes + "s";
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
  document.getElementById("refreshbutton").className = "refreshing button";
  if (page == "jobs") {
    reloadJobs ();
  } else if (page == "workers") {
    reloadWorkers ();
  } else if (page == "activities") {
    reloadActivities ();
  } else if (page == "logs") {
    renderLog (logId);
  } else if (page == "affinities") {
    renderAffinities ();
  }
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
function addSumEmpty (str, order)
{
  if (str == undefined)
    return "<td style='order: "+order+"'></td>";
  else
    return "<td style='order: "+order+"'>" + str + "</td>";
}

// Returns the HTML code for a job title column
function addSum (inputs, attribute, order)
{
  var sum = 0;
  for (i=0; i < inputs.length; i++)
  {
    var job = inputs[i];
    sum += job[attribute];
  }
  return "<td style='order: "+order+"'>" + sum + "</td>";
}

// Returns the HTML code for a job title column
function addSumFinished (inputs, attribute, order)
{
  var sum = 0;
  for (i=0; i < inputs.length; i++)
  {
    var job = inputs[i];
    if (job[attribute] == "FINISHED")
      sum ++;
  }
  return "<td style='order: "+order+"'>" + sum + " FINISHED</td>";
}

// Average
function addSumAvgDuration (inputs, attribute, order)
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
    return "<td style='order: "+order+"'>Avg " + formatDuration (sum/count) + "</td>";
  else
    return "<td style='order: "+order+"'></td>";
}

// Returns the HTML code for a job title column
function addSumSimple (inputs, order)
{
  return "<td style='order: "+order+"'>" + inputs.length + " jobs</td>";
}

function renderParents ()
{
  $("#parents").empty ();
  if (parents.lenght === 0) {
    document.getElementById("parents").innerHTML = '<a href="javascript:goToJob(0)">Root</a>';
    return;
  }
  for (i=0; i < parents.length; i++)
  {
    var parent = parents[i];
    $("#parents").append((i == 0 ? "" : " > ") + ("<a href='javascript:goToJob("+parent.id+")'>" + parent.title + "</a>"));
  }
}

// Render the current jobs
function renderJobs (jobsCurrent=[]) {
  if (jobsCurrent.length) jobs = jobsCurrent;

  // Returns the HTML code for a job title column
  function addTitleHTML ({attribute="", alias=null, order=0, input=null, min=0, max=100, defaultValue=0}={}) {
    if (alias == null) var alias = attribute;
    table += '\
             <th data-key="'+attribute+'" style="order: '+order+';">\
             <div class="flex-row" draggable="true" title="Drag and drop column header to reorganize them" ondragstart="columnDragStart(event)" ondrag="columnDrag(event)">\
             <div class="flex-row flex-grow dropzone side-left"\
             ondragenter="columnDragEnter(event)"\
             ondrop="columnDrop(event, \'left\')"\
             ondragover="columnDragOver(event)"\
             ondragleave="columnDragLeave(event)">\
             <label class="dropzone" onclick="setSortKey(event, \''+attribute+'\')">'+alias+'</label>\
             </div>\
             <div class="flex-row flex-grow dropzone side-right"\
             ondragenter="columnDragEnter(event)"\
             ondrop="columnDrop(event, \'right\')"\
             ondragover="columnDragOver(event)"\
             ondragleave="columnDragLeave(event)">\
             <div class="flex-column resizable"\
             onmousedown="columnResizeStart(event)">\
             </div>\
             </div>\
             </div>';

    if (input) {
      var nodeSelector = '#jobsTable th[data-key=\''+attribute+'\']';
      switch (input) {
        case "search":
          table += buildInputForField(nodeSelector, "sql-search-job", attribute);
          break;
        case "select":
          table += buildSelectForField(nodeSelector, "sql-search-job", attribute);
          break;
        case "datetime-local":
          table += buildDatetimeForField(nodeSelector, "sql-search-job", attribute, input, min, max, defaultValue);
          break;
        case "range":
          table += buildRangeForField(nodeSelector, "sql-search-job", attribute, input, min, max, defaultValue);
          break;
        case "number":
          table += buildInputNumberForField(nodeSelector, "sql-search-job", attribute, min);
          break;
        default:
          break;
      }
    }
    table += '</div></th>';
  }

  var table = '<table id="jobsTable">';
  table += "<thead>";
  table += "<tr>";
  addTitleHTML ({"attribute": "id", "order":0, "input": "search"});
  addTitleHTML ({"attribute": "title", "order": 1, "input": "search"});
  addTitleHTML ({"attribute": "url", "order": 2, "input": "search"});
  addTitleHTML ({"attribute": "user", "order": 3, "input": "select"});
  addTitleHTML ({"attribute": "state", "order": 4, "input": "select"});
  addTitleHTML ({"attribute": "priority", "order": 5, "input": "number", "min": 0});
  addTitleHTML ({"attribute": "total_finished", "alias": "ok", "order": 6, "input": "number", "min": 0});
  addTitleHTML ({"attribute": "total_working", "alias": "wrk", "order": 7, "input": "number", "min": 0});
  addTitleHTML ({"attribute": "total_errors", "alias": "err", "order": 8, "input": "number", "min": 0});
  addTitleHTML ({"attribute": "total", "order": 9, "input": "number", "min": 0});
  addTitleHTML ({"attribute": "progress", "alias": "progress &ge; 0%", "order": 10, "input": "range", "min": 0, "max": 100, "defaultValue": 0});
  addTitleHTML ({"attribute": "affinity", "order": 11, "input": "search"});
  addTitleHTML ({"attribute": "timeout", "order": 12, "input": "number", "min": 0});
  addTitleHTML ({"attribute": "worker", "order": 13, "input": "search"});
  addTitleHTML ({"attribute": "start_time", "alias": "start time", "order": 14, "input": "datetime-local", "min": "", "max": "", "defaultValue": "2017-01-01T00:00:01"});
  addTitleHTML ({"attribute": "duration", "order": 15, "input": "number", "min": 0});
  addTitleHTML ({"attribute": "run_done", "alias": "run", "order": 16, "input": "number", "min": 0});
  addTitleHTML ({"attribute": "command", "order": 17, "input": "search"});
  addTitleHTML ({"attribute": "dir", "order": 18, "input": "search"});
  addTitleHTML ({"attribute": "dependencies", "order": 19, "input": "search"});
  table += "</tr>";
  table += '<tr>';
  table += addSumSimple (jobs, 0);
  table += addSumEmpty (undefined, 1);
  table += addSumEmpty (undefined, 2);
  table += addSumEmpty (undefined, 3);
  table += addSumFinished (jobs, "state", 4);
  table += addSumEmpty (undefined, 5);
  table += addSum (jobs, "total_finished", 6);
  table += addSum (jobs, "total_working", 7);
  table += addSum (jobs, "total_errors", 8);
  table += addSum (jobs, "total", 9);
  table += addSumEmpty (undefined, 10);
  table += addSumEmpty (undefined, 11);
  table += addSumEmpty (undefined, 12);
  table += addSumEmpty (undefined, 13);
  table += addSumEmpty (undefined, 14);
  table += addSumAvgDuration (jobs, "duration", 15);
  table += addSumEmpty (undefined, 16);
  table += addSumEmpty (undefined, 17);
  table += addSumEmpty (undefined, 18);
  table += addSumEmpty (undefined, 19);
  table += "</tr>";
  table += "</thead>";
  table += "<tbody>";

  for (i=0; i < jobs.length; i++) {
    var job = jobs[i];
    var mouseDownEvent = 'onMouseDown="onClickList (event,'+i+')" onDblClick="onDblClickList(event,'+i+')"';

    table += '<tr id="jobtable'+i+'" '+mouseDownEvent+' class="entry'+(i%2)+(selectedJobs[job.id]?'Selected':'')+'">';

    function addTDajax (attr, order, id) {
      table += "<td id='"+id+"' style='order: "+order+"' title='" + attr + "'>" + attr + "</td>";
    }

    function addTD (attr, order) {
      table += "<td style='order: "+order+"' title='" + attr + "'>" + attr + "</td>";
    }

    addTD (job.id, 0);
    addTD (job.title, 1);

    // url
    if (job.url != "") addTD ('<a title="'+job.url+'" target="_blank" href="'+job.url+'">Open</a>', 2)
    else addTD ("", 2)

    // check group state!
    var mystate = job.paused ? "PAUSED" : job.state;

    addTD (job.user, 3);
    table += '<td style="order: 4" class="'+mystate+'">'+mystate+'</td>';
    addTD (job.priority, 5);
    if (job.total > 0)
    {
      table += '<td style="order: 6" class="'+(job.total_finished > 0 ? 'FINISHED' : 'WAITING')+'">'+job.total_finished+'</td>';
      table += '<td style="order: 7" class="'+(job.total_working > 0 ? 'WORKING' : 'WAITING')+'">'+job.total_working+'</td>';
      table += '<td style="order: 8" class="'+(job.total_errors > 0 ? 'ERROR' : 'WAITING')+'">'+job.total_errors+'</td>';
      table += '<td style="order: 9" class="'+(job.total == job.total_finished ? 'FINISHED' : 'WAITING')+'">'+job.total+'</td>';
    }
    else
    {
      addTD ("", 6);
      addTD ("", 7);id='"+id+"'
      addTD ("", 8);
      addTD ("", 9);
    }

    // *** Progress bar
    var progress = ""
    var _progress = job.progress
    _progress = Math.floor(_progress*100.0);

    // A bar div
    progress =  '<div class="progress">';
    progress += '<div class="lprogressbar" style="width:' + _progress + '%"></div>';
    progress += '<div class="progresslabel">' + _progress + '%</div>';
    progress += '</div>';

    addTD (progress, 10);
    addTD (job.affinity, 11);
    addTD (job.timeout, 12);
    addTD (job.worker, 13);
    if (job.start_time > 0) {
      addTD (formatDate(job.start_time), 14);
    } else {
      addTD ("", 14);
    }
    addTD (formatDuration (job.duration), 15);
    addTD (job.run_done, 16);
    addTD (job.command, 17);
    addTD (job.dir, 18);
    addTDajax (String(), 19, "dependencies-job-"+job.id);

    table += "</td></tr>";
  }
  table += "</tbody>";

  // Footer
  table += "<tfoot>";
  table += "</tfoot>";
  table += "</table>";

  var target = document.getElementById("jobs");
  target.innerHTML = table;

  // Ajax user select input
  var ajaxJobsUser = getAjaxJobsUsers();
  ajaxJobsUser.done(function(items) {
    var nodeSelector = '#jobsTable th[data-key=user]';
    var content = '<select form="sql-search-form" class="sql-input" id="job-filter-user" form="sql-select" multiple onclick="checkJobSqlInputChange(\'user\', event)" onkeydown="checkJobSqlInputChange(\'user\', event)" onkeyup="checkJobSqlInputChange(\'user\', event)">';
    for (i=0; i < items.length; i++) {
      var item = items[i]["user"];
      content += '<option value="'+item+'">'+item+'</option>';
    }
    content += '</select>';
    var element = document.createElement('div');
    element.classList.add("sql-search-field");
    element.innerHTML += content;
    element.title="Use <control> to (un)select options";
    var target = document.querySelector(nodeSelector);
    var targetInput = target.querySelector(".sql-search-field");
    target.replaceChild(element, targetInput);
    configTableApplyConfig(configTableGetConfigFromStorage(), force=true, sqlRefresh=false);
  });
  getParent (viewJob);
}

function getJobsDependencies() {
  // Ajax per job dependencies
  for (job of jobs) {
    getAjaxJobsDependencies(job.id).done(function(dependencies) {
      var html = String();
      for (var i = 0; i < dependencies.length; i++) {
        html += dependencies[i].id;
        if (i + 1 < dependencies.length) {
          html += ", ";
        }
        var target = document.getElementById("dependencies-job-"+this);
        target.innerHTML = html;
        target.title = html;
      }
    })
  }
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
function reloadJobs () {
  parents = [];
  switch (viewJob) {
    case 0: // Root job
      getSqlWhereJobs();
      break;
    default: // Show viewJob children
      $.ajax({ type: "GET", url: "/api/webfrontend/jobs/"+viewJob+"/children", dataType: "json", success:
        function(jobs) {
          jobs = jobs;
          var idtojob = {}
          for (i=0; i<jobs.length; ++i) {
            var job = jobs[i];
            idtojob[job.id] = job;
            job.dependencies = [];
          }
          $.ajax({ type: "GET", url: "/api/webfrontend/jobs/"+viewJob+"/childrendependencies", dataType: "json", success:
            function(data) {
              for (var i=0; i<data.length; ++i) {
                var job = idtojob[data[i].id];
                if (job)
                  job.dependencies.push(data[i].dependency);
              }
              for (var i=0; i<jobs.length; ++i) {
                var job = jobs[i];
                job.dependencies = job.dependencies.join (",");
              }
              renderJobs(jobs);
            }
          });
        }
      });
      break;
  }
}

function getParent(id) {
  if (id == 0) {
    parents.unshift({id:0,title:"Root"});
    renderParents();
  } else {
    $.ajax({ type: "GET", url: "/api/webfrontend/jobs/"+id, dataType: "json", success:
      function(data)
      {
        parents.unshift(data);
        getParent(data.parent);
      }
    });
  }
}

function startWorkers ()
{
  $.ajax({ type: "POST", url: "/api/webfrontend/startworkers", data: JSON.stringify(getSelectedWorkers ()), dataType: "json", success:
    function ()
    {
      reloadWorkers ();
    }
  });
}

function stopWorkers ()
{
  $.ajax({ type: "POST", url: "/api/webfrontend/stopworkers", data: JSON.stringify(getSelectedWorkers ()), dataType: "json", success:
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
    $.ajax({ type: "POST", url: "/api/webfrontend/terminateworkers", data: JSON.stringify(getSelectedWorkers ()), dataType: "json", success:
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

  // Toggle detail node
  for (let detail of document.querySelectorAll("details")) {
    detail.removeAttribute("open");
  }
  for (let i in selectedList) {
    if (selectedList[i] === true) {
      for (let detail of document.querySelectorAll("details")) {
        detail.setAttribute("open", null);
      }
      break;
    }
  }

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
      $('#'+props[i][1]).addClass("value-different");
      $('#'+props[i][1]).attr("value", "");
      $('#'+props[i][1]).val("");
    }
    else if (values[i] == null)
    {
      // default value
      $('#'+props[i][1]).removeClass("value-modified value-different");
      $('#'+props[i][1]).attr("value", props[i][2]);
      $('#'+props[i][1]).val(props[i][2]);
    }
    else
    {
      // unique values
      $('#'+props[i][1]).removeClass("value-modified value-different");
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
      $('#'+props[i][1]).addClass("value-modified");
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
          var value = $('#'+props[i][1]).val();
          if (prop === "dependencies")
            // Allows trailing spaces, several commas, etc.
            value = value.match(/\S+/g);
          _props[prop] = value;
        }
      data[id] = _props;
      idsN++;
    }
  }
  if (!idsN)
    return;

  // One single call
  $.ajax({ type: "POST", url: "/api/webfrontend/"+objects.toLowerCase(), data: JSON.stringify(data), dataType: "json", success:
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
  $.ajax({ type: "GET", url: "/api/webfrontend/workers", dataType: "json", success:
    function (data) {
      getSqlWhereWorkers();
    }
  });
}

function renderWorkers (workersCurrent=[])
{
  if (workersCurrent.length !== 0) workers = workersCurrent;
  else workers = [];
  var table = "<table id='workersTable'>";
  table += "<thead>";
  table += "<tr>";

  // Returns the HTML code for a worker title column
  function addTitleHTML ({attribute="", alias=null, order=0, input=null, min=0, max=100, defaultValue=0}={}) {
    if (alias == null) var alias = attribute;
    table += '\
             <th data-key="'+attribute+'" style="order: '+order+';">\
             <div class="flex-row" draggable="true" title="Drag and drop column header to reorganize them" ondragstart="columnDragStart(event)" ondrag="columnDrag(event)">\
             <div class="flex-row flex-grow dropzone side-left"\
             ondragenter="columnDragEnter(event)"\
             ondrop="columnDrop(event, \'left\')"\
             ondragover="columnDragOver(event)"\
             ondragleave="columnDragLeave(event)">\
             <label class="dropzone" onclick="setSortKey(event, \''+attribute+'\')">'+alias+'</label>\
             </div>\
             <div class="flex-row flex-grow dropzone side-right"\
             ondragenter="columnDragEnter(event)"\
             ondrop="columnDrop(event, \'right\')"\
             ondragover="columnDragOver(event)"\
             ondragleave="columnDragLeave(event)">\
             <div class="flex-column resizable"\
             onmousedown="columnResizeStart(event)">\
             </div>\
             </div>\
             </div>';

    if (input) {
      var nodeSelector = '#workersTable th[data-key=\''+attribute+'\']';
      switch (input) {
        case "search":
          table += buildInputForField(nodeSelector, "sql-search-worker", attribute);
          break;
        case "select":
          table += buildSelectForField(nodeSelector, "sql-search-worker", attribute);
          break;
        case "datetime-local":
          table += buildDatetimeForField(nodeSelector, "sql-search-worker", attribute, input, min, max, defaultValue);
          break;
        case "range":
          table += buildRangeForField(nodeSelector, "sql-search-worker", attribute, input, min, max, defaultValue);
          break;
        case "number":
          table += buildInputNumberForField(nodeSelector, "sql-search-worker", attribute, min, max);
          break;
        default:
          break;
      }
    }
    table += '</div></th>';
  }

  addTitleHTML ({"attribute": "name", "order": 0, "input": "search"});
  addTitleHTML ({"attribute": "active", "order": 1, "input": "search"});
  addTitleHTML ({"attribute": "state", "order": 2, "input": "select"});
  addTitleHTML ({"attribute": "affinity", "order": 3});
  addTitleHTML ({"attribute": "start_time", "alias": "start date", "order": 4, "input": "datetime-local", "min":"", "max": "", "defaultValue": "2017-01-01T00:00:01"});
  addTitleHTML ({"attribute": "cpu", "order": 5});
  addTitleHTML ({"attribute": "memory", "alias": "free memory", "order": 6});
  addTitleHTML ({"attribute": "last_job", "alias": "last job id", "order": 7, "input": "search"});
  addTitleHTML ({"attribute": "finished", "alias": "jobs finished", "order": 8, "input": "number", "min":0});
  addTitleHTML ({"attribute": "error", "order": 9});
  addTitleHTML ({"attribute": "ip", "alias": "ip address", "order": 10, "input": "search"});

  table += "</tr>";
  table += "</thead>";
  table += "<tbody>";

  //function _sort (a,b)
  //{
    //var aValue = a[workersSortKey];
    //if (typeof aValue == 'string')
      //return compareStrings (aValue, b[workersSortKey], workersSortKeyToUpper);
    //else
      //return compareNumbers (aValue, b[workersSortKey], workersSortKeyToUpper);
  //}

  //workers.sort (_sort);

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
        load += "<div class='loadbar' style='width:" + workerload[j] + "%'></div>";
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
      "<td style='order: 0' onMouseDown='onClickList(event,"+i+")'>"+worker.name+"</td>"+
      "<td style='order: 1' class='active"+worker.active+"' onMouseDown='onClickList(event,"+i+")'>"+worker.active+"</td>"+
      "<td style='order: 2' class='"+worker.state+"' onMouseDown='onClickList(event,"+i+")'>"+worker.state+"</td>"+
      "<td style='order: 3' class='worker_affinities' onMouseDown='onClickList(event,"+i+")'>"+worker.affinity+"</td>"+
      "<td style='order: 4' onMouseDown='onClickList(event,"+i+")'>"+worker.start_time+"</td>"+
      "<td style='order: 5' onMouseDown='onClickList(event,"+i+")'>"+load+"</td>"+
      "<td style='order: 6' onMouseDown='onClickList(event,"+i+")'>"+memory+"</td>"+
      "<td style='order: 7' onMouseDown='onClickList(event,"+i+")'>"+worker.last_job+"</td>"+
      "<td style='order: 8' onMouseDown='onClickList(event,"+i+")'>"+worker.finished+"</td>"+
      "<td style='order: 9' onMouseDown='onClickList(event,"+i+")'>"+worker.error+"</td>"+
      "<td style='order: 10'>"+worker.ip+"</td>"+
      "</tr>";
  }
  table += "</tbody>";
  table += "</table>";
  var target = document.getElementById("workers");
  target.innerHTML = table;
}

function reloadActivities ()
{
  var data = {};
  var job = $('#activityJob').prop("value")
  if (job != "")
    data.job = job
  var worker = $('#activityWorker').prop("value")
  if (worker != "")
    data.worker = worker
  data.howlong = $('#howlong').prop("value")
  $.ajax({ type: "GET", url: "/api/webfrontend/events", data: data, dataType: "json", success:
    function (data)
    {
      activities = data;
      renderActivities ();
    }
  });
}

function renderActivities ()
{
  $("#activities").empty ();

  var table = "<table id='activitiesTable'>";
  table += "<thead>";

  // Returns the HTML code for an activitiy title column
  function addTitleHTML (attribute)
  {
    table += "<th data-key='"+attribute+"' onclick='"+"setActivityKey(\""+attribute+"\")'>";
    var value = activities[0];
    table += "<label>"+attribute;
    if (value && value[attribute] != null)
    {
      if (attribute == activitiesSortKey && activitiesSortKeyToUpper)
        table += " &#8595;";
      if (attribute == activitiesSortKey && !activitiesSortKeyToUpper)
        table += " &#8593;";
    }
    table += "</label></th>";
  }

  addTitleHTML ("start");
  addTitleHTML ("job_id");
  addTitleHTML ("job_title");
  addTitleHTML ("state");
  addTitleHTML ("worker");
  addTitleHTML ("duration");

  table += "</thead>";

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
      "<td>"+date+"</td>"+
      "<td>"+activity.job_id+"</td>"+
      "<td>"+activity.job_title+"</td>"+
      "<td class='"+activity.state+"'>"+activity.state+"</td>"+
      "<td>"+activity.worker+"</td>"+
      "<td>"+dura+"</td>"+
      "</tr>";
  }

  // Footer
  table += "<tfoot>";
  table += addSumEmpty ();
  table += addSumSimple (activities);
  table += addSumEmpty ();
  table += addSumFinished (activities, "state");
  table += addSumEmpty ();
  table += addSumAvgDuration (activities, "duration");
  table += "</tfoot>";

  table += "</table>";
  $("#activities").append(table);
  $("#activities").append("<br>");
}

function renderAffinities ()
{
  $("#affinities").empty ();

  var table = "<table id='affinitiesTable'>";
  table += "<thead>";
  table += "<tr>";

  function addTitleHTML (attribute)
  {
    table += "<th onclick='"+"setActivityKey(\""+attribute+"\")'>";
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

  table += "</tr></thead><tbody>";

  for (i = 1; i <= 63; ++i)
  {
    table += "<tr>";
    table += "<td>"+i+"</td><td><input type='edit' class='ttedit' id='affinity"+i+"' name='affinity' value='' onchange='onchangeaffinityprop ("+i+")'></td>"
    table += "</tr>";
  }

  updateAffinities ();

  table += "</tbody></table>";
  $("#affinities").append(table);
  $("#affinities").append("<br>");
}

function onchangeaffinityprop (affinity)
{
  $('#affinity'+affinity).addClass("value-modified");
}

function updateAffinities ()
{
  $.ajax({ type: "GET", url: "/api/webfrontend/affinities", dataType: "json", success:
    function (data)
    {
      affinities = data;
      for (i = 1; i <= 63; ++i)
      {
        var def = affinities[i];
        if (def)
          $("#affinity"+i).attr("value", def);
      }
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
  $.ajax({ type: "POST", url: "/api/webfrontend/affinities", data: data, dataType: "json", success:
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
    title:$('#title')[0].value,
    command:$('#cmd')[0].value,
    dir:$('#dir')[0].value,
    env:$('#env')[0].value,
    priority:$('#priority')[0].value,
    timeout:$('#timeout')[0].value,
    affinity:$('#affinity')[0].value,
    dependencies:$("#dependencies")[0].value,
    user:$('#user')[0].value,
    url:$('#url')[0].value,
    parent:viewJob
  };
  $.ajax({ type: "PUT", url: "/api/webfrontend/jobs", data: JSON.stringify(data), dataType: "json", success:
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
    $.ajax({ type: "DELETE", url: "/api/webfrontend/jobs", data: JSON.stringify(data), dataType: "json", success:
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
  $.ajax({ type: "POST", url: "/api/webfrontend/startjobs", data: JSON.stringify(data), dataType: "json", success:
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
    $.ajax({ type: "POST", url: "/api/webfrontend/resetjobs", data: JSON.stringify(data), dataType: "json", success:
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
    $.ajax({ type: "POST", url: "/api/webfrontend/reseterrorjobs", data: JSON.stringify(data), dataType: "json", success:
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
  $.ajax({ type: "POST", url: "/api/webfrontend/pausejobs", data: JSON.stringify(data), dataType: "json", success:
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
  $.ajax({ type: "POST", url: "/api/webfrontend/jobs", data: JSON.stringify(data), dataType: "json", success:
    function ()
    {
      reloadJobs ();
    }
  });
}

/* logout functions */
function renderLogoutButton() {
  var userName = getCookie("authenticated_user");
  if ( userName != "" )
    $("#logout-button").html('<input type="button" class="button" onClick="onLogout()" value="Logout '+userName+'"/>');
}

function onLogout() {
  /* Set the auth user to "logout" and get a 401 error response to reset the cached crendentials */
  $.ajax({
    type: "POST",
    url: "/api/webfrontend/logout",
    username: "logout",
    error: function() {
      window.location = "/";
      /* expiration time set to 0 to delete the cookie */
      setCookie("authenticated_user", "", 0);
    }
  })
}

/* Cookie functions */
function setCookie(cname, cvalue, exp) {
    var d = new Date();
    d.setTime(exp);
    var expires = "expires="+d.toUTCString();
    document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
}

function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for(var i = 0; i < ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) == ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}

/* Jobs SQL requests */

function buildInputForField(nodeSelector, form, field) {
  switch (form) {
    case "sql-search-job":
      return '<div class="sql-search-field"><input form="'+form+'" class="sql-input" id="job-filter-'+field+'" type="search" title="Comma separated values. Press <enter> to confirm."  onKeyDown="checkJobSqlInputChange(\''+field+'\', event)"></div>';
    case "sql-search-worker":
      return '<div class="sql-search-field"><input form="'+form+'" class="sql-input" id="worker-filter-'+field+'" type="search" title="Comma separated values. Press <enter> to confirm."  onKeyDown="checkJobSqlInputChange(\''+field+'\', event)"></div>';
  }
}

function buildInputNumberForField(nodeSelector, form, field, min=0, max=null) {
  switch (form) {
    case "sql-search-job":
      if (max) {
        return '<div class="sql-search-field"><input form="'+form+'" class="sql-input" id="job-filter-'+field+'" type="number" title="Set minimum value. Press <enter> to confirm." min="'+min+'" max="'+max+'" onKeyDown="checkJobSqlInputChange(\''+field+'\', event)"></div>';
      } else {
        return '<div class="sql-search-field"><input form="'+form+'" class="sql-input" id="job-filter-'+field+'" type="number" title="Set minimum value. Press <enter> to confirm." min="'+min+'" onKeyDown="checkJobSqlInputChange(\''+field+'\', event)"></div>';
      }
    case "sql-search-worker":
      if (max) {
        return '<div class="sql-search-field"><input form="'+form+'" class="sql-input" id="worker-filter-'+field+'" type="number" title="Set minimum value. Press <enter> to confirm." min="'+min+'" max="'+max+'" onKeyDown="checkJobSqlInputChange(\''+field+'\', event)"></div>';
      } else {
        return '<div class="sql-search-field"><input form="'+form+'" class="sql-input" id="worker-filter-'+field+'" type="number" title="Set minimum value. Press <enter> to confirm." min="'+min+'" onKeyDown="checkJobSqlInputChange(\''+field+'\', event)"></div>';
      }
  }
}

function buildSelectForField(nodeSelector, form, field) {
  var items;
  switch (field) {
    case "user":
      return('<div class="sql-search-field"></div>');
    case "state":
      switch (form) {
        case "sql-search-job":
          content = getSelectForFieldStatesStatic(form, field);
          break;
        case "sql-search-worker":
          content = getSelectForFieldWorkersStatesStatic(form, field);
          break;
      }
      return('<div class="sql-search-field">'+content+'</div>');
  }
}

function buildDatetimeForField(nodeSelector, form, field, type, min, max, defaultValue) {
  switch (form) {
    case "sql-search-job":
      content = '<input form="'+form+'" id="job-filter-'+field+'" class="sql-input" type="datetime-local" step="1" value="'+defaultValue+'" pattern="[0-9]{4}-([0-9]{2}|[1-9])-([0-9]{2}|[1-9])T([0-9]{2}|[0-9]):([0-9]{2}|[0-9]):([0-9]{2}|[0-9])" title="Like 2017-01-25T12:30:00" step="1" XXXonkeydown="checkJobSqlInputChange(\''+field+'\', event)" onchange="checkJobSqlInputChange(\''+field+'\', event)">';
      break;
    case "sql-search-worker":
      content = '<input form="'+form+'" id="worker-filter-'+field+'" class="sql-input" type="datetime-local" step="1" value="'+defaultValue+'" pattern="[0-9]{4}-([0-9]{2}|[1-9])-([0-9]{2}|[1-9])T([0-9]{2}|[0-9]):([0-9]{2}|[0-9]):([0-9]{2}|[0-9])" title="Like 2017-01-25T12:30:00" step="1" XXXonkeydown="checkJobSqlInputChange(\''+field+'\', event)" onchange="checkJobSqlInputChange(\''+field+'\', event)">';
      break;
  }
  return '<div class="sql-search-field">'+content+'</div>';
}

function buildRangeForField(nodeSelector, form, field, type, min, max, defaultValue) {
  switch (form) {
    case "sql-search-job":
      content = '<input form="'+form+'" id="job-filter-'+field+'" class="sql-input" type="'+type+'" value="'+defaultValue+'" min="'+min+'" max="'+max+'" oninput="onRangeInput(event)" onchange="checkJobSqlInputChange(\''+field+'\', event)">';
      content += '<div id="job-filter-'+field+'-values"></div>';
      break;
    case "sql-search-worker":
      content = '<input form="'+form+'" id="job-filter-'+field+'" class="sql-input" type="'+type+'" value="'+defaultValue+'" min="'+min+'" max="'+max+'" oninput="onRangeInput(event)" onchange="checkJobSqlInputChange(\''+field+'\', event)">';
      content += '<div id="job-filter-'+field+'-values"></div>';
      break;
  }
  return '<div class="sql-search-field">'+content+'</div>';
}

function onRangeInput(event) {
  var value = event.target.value;
  var label = event.target.parentNode.parentNode.querySelector("label");
  label.innerHTML = label.innerHTML.replace(/\d+/, value);
}

function toggleSearchField(node) {
  var node = $(node).children(".sql-search-field");
  if (node.css("visibility") == "hidden") {
    node.css("visibility", "visible");
    node.children("select, input").focus();
  } else {
    node.css("visibility", "hidden");
    node.children("select, input").blur();
  }
}

function checkJobSqlInputChange(column, event) {
  var table = configTableGetActiveTable();
  var keyCodeEnter = 13;
  var keyCodeControl = 17;
  var value = event.target.value;
  switch (event.type) {
    case "click":
      if (!event.ctrlKey) {
        var config = configTableSetConfig(table, column, "sql", Array(value));
        configTableApplyConfig(configTableSetConfigToStorage(table, config), force=true, sqlRefresh=true);
      }
      break;
    case "keydown":
      switch (event.keyCode) {
        case keyCodeEnter:
          var config = configTableSetConfig(table, column, "sql", value);
          configTableApplyConfig(configTableSetConfigToStorage(table, config), force=true, sqlRefresh=true);
          break;
      }
      break;
    case "keyup":
      if (event.keyCode === keyCodeControl) {
        var config = configTableSetConfig(table, column, "sql", configTableGetConfig(table)[column][4]);
        configTableApplyConfig(configTableSetConfigToStorage(table, config), force=true, sqlRefresh=true);
      }
      break;
    case "change":
      var config = configTableSetConfig(table, column, "sql", value);
      configTableApplyConfig(configTableSetConfigToStorage(table, config), force=true, sqlRefresh=true);
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

function getAjaxJobsDependencies(jobId) {
  return $.ajax({
    type: "GET",
    url: "/api/jobs/"+jobId+"/dependencies",
    dataType: "json",
    context: jobId,
  })
}

function getSelectForFieldStatesStatic(form, field) {
    var content = '<select form="'+form+'" class="sql-input" id="job-filter-'+field+'"';
    content += ' form="sql-select" multiple';
    content += ' title="Use <control> to (un)select options"';
    content += ' onclick="checkJobSqlInputChange(\''+field+'\', event)"';
    content += ' onkeydown="checkJobSqlInputChange(\''+field+'\', event)"';
    content += ' onkeyup="checkJobSqlInputChange(\''+field+'\', event)">';
    items = ["WORKING", "ERROR", "WAITING", "FINISHED", "PAUSED", "CUSTOM"];
    for (i=0; i < items.length; i++) {
      var item = items[i];
      content += '<option value="'+item+'">'+item+'</option>';
    }
    content += '</select>';
  return content;
}

function getSelectForFieldWorkersStatesStatic(form, field) {
    var content = '<select form="'+form+'" class="sql-input" id="worker-filter-'+field+'"';
    content += ' form="sql-select" multiple';
    content += ' title="Use <control> to (un)select options"';
    content += ' onclick="checkJobSqlInputChange(\''+field+'\', event)"';
    content += ' onkeydown="checkJobSqlInputChange(\''+field+'\', event)"';
    content += ' onkeyup="checkJobSqlInputChange(\''+field+'\', event)">';
    items = ["WAITING", "WORKING", "TIMEOUT", "STARTING", "TERMINATED"];
    for (i=0; i < items.length; i++) {
      var item = items[i];
      content += '<option value="'+item+'">'+item+'</option>';
    }
    content += '</select>';
  return content;
}

function getAjaxSqlWhereCountJobs(data) {
  return $.ajax({
    type: "GET",
    url: "/api/jobs/count/where/",
    data: data,
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

function getAjaxSqlWhereWorkers(data) {
  return $.ajax({
    type: "GET",
    url: "/api/workers/where/",
    data: data,
    datatype: "json",
  })
}

function onSqlSearchFormSubmit(event) {
  event.preventDefault();
  table = configTableGetActiveTable();
  switch (table.id) {
    case "jobsTable":
      getSqlWhereJobs();
      break;
    case "workersTable":
      getSqlWhereWorkers();
      break;
  }
};

function getSqlWhereJobs() {
  // Limit search to children of viewJob
  var sql = "(parent = "+viewJob+")";
  var sqlSortBy = "";
  var data = Object();
  var table = configTableGetActiveTable();
  var innerJoinTable = "";

  if (table) {
    var config = configTableGetConfigFromStorage()[table.id];
    for (let i in config) {

      let value = config[i][4];
      if (value !== null && String(value).length) {
        data[i] = value;
      }
    }
    var sortBy = configTableGetSortKeyFromStorage(table);
    if (sortBy["sortKey"] !== "") {
      var direction = (sortBy["sortKeyToUpper"]) ? "ASC" : "DESC";
      sqlSortBy += " ORDER BY " + sortBy["sortKey"] + " " + direction;
    }
  }

  for (let key in data) {
    var values = data[key];
    // Build sql clause
    switch (key) {
      case "id":
      case "parent":
        if (values[0] == ""  && values.length == 1) break;
        sql += " and (";
        // Comma separated values with optional surrounding spaces
        var splittedValues = values.split(RegExp(" *, *"));
        for (let j in splittedValues) {
          sql += key+" = "+splittedValues[j];
          if (Number(j) + 1 < splittedValues.length) sql += " or ";
        }
        sql += ")";
        break;
      case "title":
      case "dir":
      case "environment":
      case "worker":
      case "affinity":
      case "url":
      case "command":
        if (values[0] == ""  && values.length == 1) break;
        sql += " and (";
        // Comma separated values with optional surrounding spaces
        var splittedValues = values.split(RegExp(" *, *"));
        for (let j in splittedValues) {
          // Regex match
          sql += key+" LIKE '%"+splittedValues[j]+"%'";
          if (Number(j) + 1 < splittedValues.length) sql += " or ";
        }
        sql += ")";
        break;
      case "user":
        sql += " and (";
        for (let i = 0; i < values.length; i++) {
          sql += key+" = '"+values[i]+"'";
          if (Number(i) + 1 < values.length) {
            sql += " or ";
          }
        }
        sql += ")";
        break;
      case "state":
        if (values.length == 0 || values[0] == undefined) break;
        sql += " and (";
        for (j in values) {
          var value = values[j];
          if (value == "WAITING" && (values.indexOf("PAUSED") < 0) ) {
            sql_exclude_paused = " and paused = 0";
          } else {
            sql_exclude_paused = "";
          }
          if (value == "PAUSED") {
              key = "paused";
              value = 1;
          }
          sql += key+"='"+value+"'";
          if (Number(j)+1<values.length) {
            sql += " or ";
          } else {
            sql += ")";
          }
        }
        break;
      case "progress":
        if (values[0] == 0) sql += " and (progress is null or progress >= 0)";
        else sql += " and (progress > "+Number(values[0])/100+")";
        break;
      case "start_time":
        var date = values.split(RegExp("-| |:|T"));
        values = Date.UTC(date[0], date[1] - 1, date[2], date[3], date[4], date[5])/1000;
        if (isNaN(values)) {
          break;
        }
        sql += " and (start_time >= "+values+")";
        break;
      case "priority":
      case "total_finished":
      case "total_working":
      case "total_errors":
      case "total":
      case "timeout":
      case "duration":
      case "run_done":
        sql += " and ("+key+" >= "+Number(values)+")";
        break;
      case "dependencies":
        innerJoinTable = "Dependencies";
        sql += " and (Jobs.id = Dependencies.job_id) and (";
        // Comma separated values with optional surrounding spaces
        var splittedValues = values.split(RegExp(" *, *"));
        for (let j in splittedValues) {
          sql += "Dependencies.dependency = "+splittedValues[j];
          if (Number(j) + 1 < splittedValues.length) sql += " or ";
        }
        sql += ")";
        break;
    }
  }
  sql += sqlSortBy;
  data = {where_clause: sql, inner_join_table: innerJoinTable};
  getAjaxSqlWhereCountJobs(data).done(function(total) {
    if (total) {
      //if (total <= max_batch) {
      if (true) {
        data = {where_clause: sql, inner_join_table: innerJoinTable, min: 0, max: 100000};
        getAjaxSqlWhereJobs(data).done(function(jobs) {
          jobs = JSON.parse(jobs);
          renderJobs(jobs);
        });
      } else {
        var batches = Math.round(total / max_batch);
        for (i = 0; i <= batches; i++) {
          min = i * max_batch;
          max = (i + 1) * max_batch - 1;
          data = {where_clause: sql, inner_join_table: innerJoinTable, min: min, max: max};
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

function getSqlWhereWorkers() {
  var sql = "1";
  var sqlSortBy = "";
  var innerJoinTable = String();
  var data = Object();
  var table = configTableGetActiveTable();

  if (table) {
    var config = configTableGetConfigFromStorage()[table.id];
    for (let i in config) {

      let value = config[i][4];
      if (value !== null && String(value).length) {
        data[i] = value;
      }
    }
    var sortBy = configTableGetSortKeyFromStorage(table);
    if (sortBy["sortKey"] !== "") {
      var direction = (sortBy["sortKeyToUpper"]) ? "ASC" : "DESC";
      sqlSortBy += " ORDER BY " + sortBy["sortKey"] + " " + direction;
    }
  }

  for (let key in data) {
    var values = data[key];
    // Build sql clause
    switch (key) {
      case "name":
      case "active":
      case "last_job":
      case "ip":
        if (values[0] == ""  && values.length == 1) break;
        sql += " and (";
        // Comma separated values with optional surrounding spaces
        var splittedValues = values.split(RegExp(" *, *"));
        for (let j in splittedValues) {
          // Regex match
          sql += "Workers."+key+" LIKE '%"+splittedValues[j]+"%'";
          if (Number(j) + 1 < splittedValues.length) sql += " or ";
        }
        sql += ")";
        break;
      case "state":
        if (values.length == 0 || values[0] == undefined) break;
        sql += " and (";
        for (j in values) {
          var value = values[j];
          if (value == "WAITING" && (values.indexOf("PAUSED") < 0) ) {
            sql_exclude_paused = " and paused = 0";
          } else {
            sql_exclude_paused = "";
          }
          if (value == "PAUSED") {
              key = "paused";
              value = 1;
          }
          sql += key+"='"+value+"'";
          if (Number(j)+1<values.length) {
            sql += " or ";
          } else {
            sql += ")";
          }
        }
        break;
      case "cpu":
        if (values[0] == 0) sql += " and (cpu is null or cpu >= 0)";
        else sql += " and (cpu > "+Number(values[0])/100+")";
        break;
      case "start_time":
        var date = values.split(RegExp("-| |:|T"));
        values = Date.UTC(date[0], date[1] - 1, date[2], date[3], date[4], date[5])/1000;
        if (isNaN(values)) {
          break;
        }
        sql += " and (start_time >= "+values+")";
        break;
      case "finished":
      case "errors":
      case "free_memory":
        sql += " and ("+key+" >= "+Number(values)+")";
        break;
    }
  }
  sql += sqlSortBy;
  data = {where_clause: sql, inner_join_table: innerJoinTable, min: 0, max: 100000};
  getAjaxSqlWhereWorkers(data).done(function(workers) {
    workers = JSON.parse(workers);
    renderWorkers(workers);
    configTableApplyConfig(configTableGetConfigFromStorage(), force=true, sqlRefresh=false);
  });
}

