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
var parents = [];
var activities = [];
var affinities = [];
var jobsSortKey = "id";
var jobsSortKeyToUpper = true;
var workersSortKey = "name";
var workersSortKeyToUpper = true;
var activitiesSortKey = "start";
var activitiesSortKeyToUpper = false;
var selectionStart = 0;
var showTools = true;
var gridjobs;
var dataViewjobs;
var columnpicker;
var MultipleSelection = {}
var updatedWorkerProps = {}
var updatedJobProps = {}
var tabs =
  [
    [ "jobs", "#jobsTab", "jobtab" ],
    [ "workers", "#workersTab", "workertab" ],
    [ "activities", "#activitiesTab", "activitytab" ],
    [ "logs", "#logsTab", "logtab" ],
    [ "affinities", "#affinitiesTab", "affinitytab" ]
  ]
var WorkerProps =
  [
    [ "affinity", "waffinity", "" ],
  ];
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


//function setJobKey(id) {
//// Same key ?
//if (jobsSortKey == id) {
//jobsSortKeyToUpper = !jobsSortKeyToUpper;
//} else {
//jobsSortKey = id;
//jobsSortKeyToUpper = true;
//}
//renderJobs();
//}

function setWorkerKey(id) {
  // Same key ?
  if (workersSortKey == id) {
    workersSortKeyToUpper = !workersSortKeyToUpper;
  } else {
    workersSortKey = id;
    workersSortKeyToUpper = true;
  }
  renderWorkers();
}

function setActivityKey(id) {
  // Same key ?
  if (activitiesSortKey == id) {
    activitiesSortKeyToUpper = !activitiesSortKeyToUpper;
  } else {
    activitiesSortKey = id;
    activitiesSortKeyToUpper = true;
  }
  renderActivities();
}

function get_cookie(cookie_name) {
  var results = document.cookie.match( '(^|;) ?' + cookie_name + '=([^;]*)(;|$)' );

  if (results) {
    return( unescape( results[2] ) );
  } else {
    return "";
  }
}

function updateQueryStringParameter(uri, key, value) {
  var re = new RegExp("([?&])" + key + "=.*?(&|$)", "i");
  var separator = uri.indexOf('?') !== -1 ? "&" : "?";
  if (uri.match(re)) {
    return uri.replace(re, '$1' + key + "=" + value + '$2');
  } else {
    return uri + separator + key + "=" + value;
  }
}

function getParameterByName(name, url) {
  if (!url) url = window.location.href;
  name = name.replace(/[\[\]]/g, "\\$&");
  var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
    results = regex.exec(url);
  if (!results) return null;
  if (!results[2]) return "";
  return decodeURIComponent(results[2].replace(/\+/g, " "));
}

function isvalidparam(param) {
  if (param==null) return false;
  if (param=='') return false;
  return true;
}

function showHideTools() {
  showTools = !showTools;
  updateTools();
}

function updateTools() {
  if (!showTools) {
    $("#tools").hide();
    $("#toggle-toolbar").show();
  } else if (page == "jobs") {
    $("#toggle-toolbar").show();
    $("#jobstools").show();
    $("#workertools").hide();
    $("#tools").show();
  } else if (page == "workers") {
    $("#toggle-toolbar").show();
    $("#jobstools").hide();
    $("#workertools").show();
    $("#tools").show();
  } else {
    $("#tools").hide();
    $("#toggle-toolbar").hide();
  }
}

function goToJob(jobId) {
  viewJob = jobId;
  reloadJobs();
}

function showTab(tab) {
  for (i = 0; i < tabs.length; ++i)
  {
    tabdef = tabs[i];
    if (tabdef[0] == tab) {
      $(tabdef[1]).show();
      document.getElementById(tabdef[2]).className = "activetab";
    } else {
      $(tabdef[1]).hide();
      document.getElementById(tabdef[2]).className = "unactivetab";
    }
  }
}

function showPage(thepage) {
  page = thepage;
  showTab(page);
  updateTools();
}

function clearLog() {
  $("#logs").empty();
}

function renderLog(jobId) {
  showPage("logs");
  logId = jobId;
  $.ajax({ type: "GET", url: "/api/jobs/"+jobId+"/log", dataType: "json", success: 
    function(data) {
      $("#logs").empty();
      $("#logs").append("<pre class='logs'><h2>Logs for job "+jobId+":</h2>"+data+"</pre>");
      page = "logs";
      updateTools();
      document.getElementById("refreshbutton").className = "refreshbutton";
    }
  });
}

function getSelectedWorkers() {
  var data = [];
  for (j=workers.length-1; j >= 0; j--) {
    var name = workers[j].name;
    if (selectedWorkers[name])
      data.push(name);
  }
  return data;
}

function clearWorkers() {
  if (confirm("Do you really want to delete the selected workers?")) {
    $.ajax({ type: "DELETE", url: "/api/workers", data: JSON.stringify(getSelectedWorkers()), dataType: "json", success: 
      function() {
        selectedWorkers = {}
        reloadWorkers();
        updateWorkerProps();
      }
    });
  }
}

function formatDate(_date) {
  var date = new Date(_date*1000)
  return date.getFullYear() + '/' + (date.getMonth()+1) + '/' + date.getDate() + ' ' + date.getHours() + ':' + date.getMinutes() + ':' + date.getSeconds();
}

function formatDuration(secondes) {
  var days = Math.floor(secondes / (60*60*24));
  var hours = Math.floor((secondes-days*60*60*24) / (60*60));
  var minutes = Math.floor((secondes-days*60*60*24-hours*60*60) / 60);
  var secondes = Math.floor(secondes-days*60*60*24-hours*60*60-minutes*60);
  if (days > 0)   
    return days + " d " + hours + " h " + minutes + " m " + secondes + " s";
  if (hours > 0)  
    return hours + " h " + minutes + " m " + secondes + " s";
  if (minutes > 0)    
    return minutes + " m " + secondes + " s";
  return secondes + " s";
}

// Timer callback
function timerCB() {
  if (document.getElementById("autorefresh").checked)
    refresh();
  // Fire a new time event
  timer=setTimeout(timerCB,4000);
}

function refresh() {
  document.getElementById("refreshbutton").className = "refreshing";
  if (page == "jobs")
    reloadJobs();
  else if (page == "workers") 
    reloadWorkers();
  else if (page == "activities") 
    reloadActivities();
  else if (page == "logs") 
    renderLog(logId);
  else if (page == "affinities") 
    renderAffinities();
}

function compareStrings(a, b, toupper) {
  if (a < b)
    return toupper ? -1 : 1;
  if (a == b)
    return 0;
  return toupper ? 1 : -1;
}

function compareNumbers(a, b, toupper) {
  return toupper ? a-b : b-a;
}

function addSumEmpty(str) {
  if (str == undefined)
    return "<td></td>";
  else
    return "<td class='headerCell'>" + str + "</td>";
}

function addSum(inputs, attribute) {
  var sum = 0;
  for (i=0; i < inputs.length; i++) {
    var job = inputs[i];
    sum += job[attribute];
  }
  return "<td class='headerCell'>" + sum + "</td>";
}

function addSumFinished(inputs, attribute) {
  var sum = 0;
  for (i=0; i < inputs.length; i++) {
    var job = inputs[i];
    if (job[attribute] == "FINISHED")
      sum ++;
  }
  return "<td class='headerCell'>" + sum + " FINISHED</td>";
}

function addSumAvgDuration(inputs, attribute) {
  var sum = 0;
  var count = 0;
  for (i=0; i < inputs.length; i++) {
    var job = inputs[i];
    sum += job[attribute];
    count++;
  }
  if (count > 0)
    return "<td class='headerCell'>Avg " + formatDuration(sum/count) + "</td>";
  else
    return "<td class='headerCell'></td>";
}

function addSumSimple(inputs) {
  return "<td class='headerCell'>" + inputs.length + " jobs</td>";
}

function renderParents() {
  $("#parents").empty();
  for (i=0; i < parents.length; i++) {
    var parent = parents[i];
    $("#parents").append((i == 0 ? "" : " > ") + ("<a href='javascript:goToJob("+parent.id+")'>" + parent.title + "</a>"));
  }
}

/* slick grid dom functions */

function buildInputForField({node, form, field, type, min, max}) {
  switch (type) {
    case "number":
      var content = '<input form="'+form+'" class="sql-input" id="grid-filter-'+field+'" type="'+type+'" min='+min+' max='+max+'>';
    //case "datetime":
      //var content = '<div id="datepair">
        //<input 'form="'+form+'" type="text" id="grid-filter-start-date" class="date start"/>\
        //<input 'form="'+form+'" type="text" id="grid-filter-start-time" class="time start"/> to \
        //<input 'form="'+form+'" type="text" id="grid-filter-end-date" class="date end"/>\
        //<input 'form="'+form+'" type="text" id="grid-filter-end-time" class="time end"/>\
      //</div>';
    default:
      var content = '<input form="'+form+'" class="sql-input" id="grid-filter-'+field+'" type="'+type+'">';
  }
  $(node).append(content);
  config = configGet("grid-filter-"+field);
  if (config) $("#grid-filter-"+field).val(config); 
}

function buildSelectForField({node, form, table, column, type}) {
  var items;
  switch (column) {
    case "user":
      ajax = getAjaxJobsUsers();
      break;
    case "state":
      ajax = getAjaxJobsStates();
      break;
  }
  ajax.done(function(items) {
    var content = '<select form="'+form+'" class="sql-input" id="grid-filter-'+column+'" form="sql-select" multiple>';
    for (i=0; i < items.length; i++) {
      var item = items[i][column];
      content += '<option value="'+item+'">'+item+'</option>';
    } 
    content += '</select>';
    $(node).append(content);
    config = configGet("grid-filter-"+column);
    if (config) $("#grid-filter-"+column).val(config.split(",")); 
  })
}

function formatterduration(row, cell, secondes, columnDef, dataContext) {
  if (isNaN(secondes)) { return ""; }
  return formatDuration(secondes);
}

function formatterdate(row, cell, timestamp, columnDef, dataContext) {
  return formatDate(timestamp);
}

function formatterstate(row, cell, value, columnDef, dataContext) {
  if (row == null)         
    var contents = value + ' FINISHED'; 
  else 
    var contents = '<div class="' + value +'">'+ (value ? value : '\n') + "</div>"; 
  return contents
}

function formattertitle(row, cell, value, columnDef, dataContext) {
  if (row == null)         
    var contents = value + ' Jobs'; 
  else 
    var contents = value; 
  return contents
}

function ProgressCompleteBarFormatter(row, cell, value, columnDef, dataContext) {
  if (value == null || value === "") {return "";}
  _value= Math.floor(value*100.0)
  return "<div class='progress-complete-bar lprogressbar' style='width:" + _value + "%'><span>"+_value+"%</span></div>";
}

/* slick grid initialization */
function initJobs() {

  var columns = configGet("gridJobsColumns");
  if (columns) {
    columns = JSON.parse(columns);
  } else {
    columns = [
      {id: "id", name: "ID", field: "id", sortable: true},
      {id: "title", name: "Title", field: "title", sortable: true, formatter:formattertitle, totalized: true, totalizationType:Slick.Controls.ColumnPicker.Countrows, totalizationvalue: 'ALL', editor: Slick.Editors.Text, validator: gridRequiredFieldValidator},
      {id: "url", name: "URL", field: "url"},
      {id: "user", name: "user", field: "user", sortable: true},
      {id: "state", name: "State", field: "state", sortable: true, formatter: formatterstate, totalized: true, totalizationType:Slick.Controls.ColumnPicker.Countrows, totalizationvalue: 'FINISHED', groupable: true},
      {id: "priority", name: "priority", field: "priority", sortable: true, cssClass: 'slick-right-align'},
      {id: "ok", name: "ok", field: "total_finished", sortable: true, cssClass: 'slick-right-align', totalized: true, totalizationType: Slick.Data.Aggregators.Sum},
      {id: "wrk", name: "wrk", field: "total_working", sortable: true, cssClass: 'slick-right-align', totalized: true, totalizationType: Slick.Data.Aggregators.Sum},
      {id: "err", name: "err", field: "total_errors", sortable: true, cssClass: 'slick-right-align', totalized: true, totalizationType: Slick.Data.Aggregators.Sum},
      {id: "total", name: "total", field: "total", sortable: true, cssClass: 'slick-right-align', totalized: true, totalizationType: Slick.Data.Aggregators.Sum},
      {id: "progress", name: "Progress", field: "progress", sortable: true, formatter:ProgressCompleteBarFormatter},
      {id: "affinity", name: "affinity", field: "affinity", sortable: true, cssClass: 'slick-right-align', groupable: true},
      {id: "timeout", name: "timeout", sortable: true, field: "timeout", cssClass: 'slick-right-align'},
      {id: "worker", name: "worker", field: "worker", sortable: true, groupable:true},
      {id: "start_time", name: "start_time", field: "start_time", sortable: true, cssClass: 'slick-right-align', formatter: formatterdate},
      {id: "duration", name: "Duration", field: "duration", cssClass: 'slick-right-align', sortable: true, formatter: formatterduration, totalized: true, totalizationType: Slick.Data.Aggregators.Avg},
      {id: "avgduration", name: "AVG Duration", field: "avgduration", cssClass: 'slick-right-align', sortable: true, formatter: formatterduration, totalized: true, totalizationType: Slick.Data.Aggregators.Avg},
      {id: "run", name: "run", field: "run", sortable: true},
      {id: "command", name: "command", field: "command", sortable: true},
      {id: "dir", name: "dir", field: "dir",  sortable: true},
      {id: "dependencies", name: "dependencies", field: "dependencies", sortable: true},
    ];
  }

  var options = {
    autoHeight: true,
    editable: false,
    asyncEditorLoading: true,
    topPanelHeight: 25,
    headerRowHeight: 10,
    enableCellNavigation: false,
    showTopPanel: true,
    showHeaderRow: true,
    showFooterRow: true,
    forceFitColumns: false,
    explicitInitialization: true,
  };

  var sortcol = "Title";
  var sortdir = 1;
  var percentCompleteThreshold = 0;
  var searchString = "";
  var h_runfilters = null;
  var columnFilters = {};
  var groupItemMetadataProvider = new Slick.Data.GroupItemMetadataProvider();

  dataViewjobs = new Slick.Data.DataView({groupItemMetadataProvider: groupItemMetadataProvider, inlineFilters: true});
  dataViewjobs.beginUpdate();
  dataViewjobs.endUpdate();

  gridjobs = new Slick.Grid("#jobs", dataViewjobs, columns, options);
  gridjobs.registerPlugin(groupItemMetadataProvider);
  gridjobs.setSelectionModel(new Slick.RowSelectionModel());

  //var pager = new Slick.Controls.Pager(dataViewjobs, gridjobs, $("#pager"));


  function gridRequiredFieldValidator(value) {
    if (value == null || value == undefined || !value.length) {
      return {valid: false, msg: "This is a required field"};
    }
    else {
      return {valid: true, msg: null};
    }
  }

  function filter(item) {
    for (var columnId in columnFilters) {
      if (columnId !== undefined && columnFilters[columnId] !== "") {
        var c = grid.getColumns()[grid.getColumnIndex(columnId)];
        if (item[c.field] != columnFilters[columnId]) {
          return false;
        }
      }
    }
    return true;
  }

  gridjobs.onHeaderRowCellRendered.subscribe(function(e, args) {
    var field = args.column.field;

    $(args.node).empty();
    // populate sql search fields
    switch (field) {
      case "id":
        buildInputForField({node: args.node, form:"sql-jobs", field: "id", type: "search"});
        break;
      case "title":
        buildInputForField({node: args.node, form:"sql-jobs", field: "title", type: "search"});
        break;
      case "user":
        buildSelectForField({node: args.node, form:"sql-jobs", table: "Jobs", column: "user", type: "checkbox"});
        break;
      case "state":
        buildSelectForField({node: args.node, form:"sql-jobs", table: "Jobs", column: "state", type: "checkbox"});
        break;
      case "priority":
        buildInputForField({node: args.node, form:"sql-jobs", field: "priority", type: "search"});
        break;
      case "affinity":
        buildInputForField({node: args.node, form:"sql-jobs", field: "affinity", type: "search"});
        break;
      case "worker":
        buildInputForField({node: args.node, form:"sql-jobs", field: "worker", type: "search"});
        break;
      case "start_time":
        buildInputForField({node: args.node, form:"sql-jobs", field: "start_time", type: "time"});
        break;
      case "command":
        buildInputForField({node: args.node, form:"sql-jobs", field: "command", type: "search"});
        break;
      case "dependencies":
        buildInputForField({node: args.node, form:"sql-jobs", field: "dependencies", type: "search"});
        break;
      default:
        return;
    }
  });

  //gridjobs.onCellChange.subscribe(function (e, args) {
    //dataViewjobs.updateItem(args.item.id, args.item);
  //});

  //gridjobs.onKeyDown.subscribe(function (e) {
    //// select all rows on ctrl-a
    //if (e.which != 65 || !e.ctrlKey) {
      //return false;
    //}
    //var rows = [];
    //for (var i = 0; i < dataViewjobs.getLength(); i++) {
      //rows.push(i);
    //}
    //gridjobs.setSelectedRows(rows);
    //e.preventDefault();
  //});

  gridjobs.onColumnsReordered.subscribe(function(e, args) {
    configSave();
  });

  gridjobs.onSort.subscribe(function(e, args) {
    var comparer = function(a, b) {
      return (a[args.sortCol.field] > b[args.sortCol.field]) ? 1 : -1;
    }
    // Delegate the sorting to DataView.
    // This will fire the change events and update the grid.
    dataViewjobs.sort(comparer, args.sortAsc);
    configSave();
  });

  //gridjobs.onClick.subscribe(function(e, args) {
    //document.getElementById("selectJobs").value = "CUSTOM";
    //var item = dataViewjobs.getItem(args.row);
  //});

  //gridjobs.onSelectedRowsChanged.subscribe(function(e, args) {
    //var Ljobid;
    //selectedJobs={};
    //for (i=0; i < gridjobs.getSelectedRows().length; i++)  {
      //Ljobid = dataViewjobs.getItem(gridjobs.getSelectedRows()[i]).id;
      //selectedJobs[Ljobid]=true;
    //}
    ////updateJobProps();
  //});

  gridjobs.onClick.subscribe(function(e, args) {
    // Toggle clicked row from jobs selection list on grid and on seletedJobs object.
    jobId = dataViewjobs.getItem(args["row"])["id"];
    selectedJobs[jobId] = selectedJobs[jobId] ? false : true;
    if (selectedJobs[jobId]) {
      var gridSelection = gridjobs.getSelectedRows();
      if (gridSelection.indexOf(args["row"]))
        gridSelection.push(args["row"]);
    } else {
      var gridSelection = gridjobs.getSelectedRows().pop(args["row"]);
    }
    console.log("greidselection:", gridSelection);
    gridjobs.setSelectedRows(gridSelection);
  });

  gridjobs.onDblClick.subscribe(function(e, args) {
    var item = dataViewjobs.getItem(args.row);
    item.command != "" ? renderLog(item.id) : goToJob(item.id);
  });

  
  dataViewjobs.onPagingInfoChanged.subscribe(function (e, pagingInfo) {
    var isLastPage = pagingInfo.pageNum == pagingInfo.totalPages - 1;
    var enableAddRow = isLastPage || pagingInfo.pageSize == 0;
    var options = gridjobs.getOptions();
    if (options.enableAddRow != enableAddRow) {
      gridjobs.setOptions({enableAddRow: enableAddRow});
    }
  });

  dataViewjobs.onRowsChanged.subscribe(function (e, args) {
    gridjobs.invalidateRows(args.rows);
    gridjobs.render();
  });

  $("#inlineFilterPanel")
    .appendTo(gridjobs.getTopPanel())
    .show();

  $(".grid-header .ui-icon")
    .addClass("ui-state-default ui-corner-all")
    .mouseover(function (e) {
      $(e.target).addClass("ui-state-hover")
    })
    .mouseout(function (e) {
      $(e.target).removeClass("ui-state-hover")
    });

  $("#inlineFilterPanel")
    .appendTo(gridjobs.getTopPanel())
    .show();

  $("#jobs").resizable();

  gridjobs.init();

  columnpicker = new Slick.Controls.ColumnPicker(columns, gridjobs, options);

  dataViewjobs.syncGridSelection(gridjobs, true);
}

/* localstorage functions */
function configSave() {
  // Save configuration in browser local storage
  
  localStorage.setItem("gridJobsColumns", JSON.stringify(gridjobs.getColumns()));
  localStorage.setItem("grid-filter-id", $("#grid-filter-id").val());
  localStorage.setItem("grid-filter-title", $("#grid-filter-title").val());
  localStorage.setItem("grid-filter-user", $("#grid-filter-user").val());
  localStorage.setItem("grid-filter-state", $("#grid-filter-state").val());
  localStorage.setItem("grid-filter-priority", $("#grid-filter-priority").val());
  localStorage.setItem("grid-filter-progress", $("#grid-filter-progress").val());
  localStorage.setItem("grid-filter-affinity", $("#grid-filter-affinity").val());
  localStorage.setItem("grid-filter-worker", $("#grid-filter-worker").val());
  localStorage.setItem("grid-filter-start_time", $("#grid-filter-start_time").val());
  localStorage.setItem("grid-filter-command", $("#grid-filter-command").val());
  localStorage.setItem("grid-filter-dependencies", $("#grid-filter-dependencies").val());
}

function configGet(itemName) {
  // Get stored item 
  return  localStorage.getItem(itemName);
}

function resetSqlFilter() {
  localStorage.clear();
  getSqlWhereJobs();
  localStorage.clear();
}

/* slickgrid functions */
function groupByaffinity(dataView) {
  dataView.setGrouping({
    getter: "affinity",
    formatter: function(g) {
      return "affinity:  " + g.value + "  <span style='color:green'>(" + g.count + " items)</span>";
    },
    aggregators: [],
    aggregateCollapsed: false,
    lazyTotalsCalculation: true
  });
}

function numberOfRowsDisplayed() {
  viewport = gridjobs.getViewport()
  return viewport["bottom"] - viewport["top"]
}

/* log tab functions */
function logSelection() {
  for (j=jobs.length-1; j >= 0; j--)
  {
    var job = jobs[j];
    if (selectedJobs[job.id])
      renderLog(job.id);
  }
}

/* reload functions */
function sendreloadJobs(emitter_id) {
  var newvalue = document.getElementById(emitter_id).value;
  var url = window.location.href;
  var newurl='';
  if (url.indexOf(emitter_id) >= 0) {
    newurl = updateQueryStringParameter(url, emitter_id, newvalue);
  }
  else {
    newurl = url + (url.split('?')[1] ? '&':'?') + emitter_id + '=' + encodeURIComponent(newvalue);
  }
  if (newurl!='') {
    window.history.replaceState({} , "Title", newurl);
  }
  reloadJobs()
}

/* render functions */
function renderJobs() {
  dataViewjobs.setItems(jobs);
  dataViewjobs.reSort();
  gridjobs.invalidate();

  items=gridjobs.getData().getItems();
  $.each(gridjobs.getColumns(), function() {
    if (this.totalized) {
      columnpicker.updateTotalizedColumns(items,this);
    }
  });

  var test = document.getElementById("selectJobs");
  if (test != undefined) 
    test.value = "NONE";
  gridjobs.setSelectedRows([]); 
}


/* ajax api functions */

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

function getSqlWhereJobs(data) {
  // Get Jobs matching the request using batch
  if (!data) data = [];
  configSave();
  // select all by default
  var sql = "1";
  // iter on form data
  for (var i=0; i<data.length; i++) {
    var data_len = data.length;
    var key = data[i].id.split("grid-filter-")[1];
    var values = [""];

    // build sql clause
    switch (key) {
      case "id":
      case "priority":
      case "dependencies":
        values = data[i].value.split(",");
        if (values[0] == "" && values.length == 1) break;
        sql += " and (";
        for (var j=0; j<values.length; j++) {
          var value = values[j];
          if (!value) continue;
          sql += key+"="+value;
          if (j+1<values.length) sql += " or ";
        }
        sql += ")";
        break;
      case "user":
      case "state":
        values = data[i].selectedOptions;
        if (values.length == 0) break;
        sql += " and (";
        for (var j=0; j<values.length; j++) {
          var value = values[j].value;
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
        values = data[i].value.split(",");
        if (values[0] == "" && values.length == 1) break;
        sql += " and (";
        for (var j=0; j<values.length; j++) {
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

  $("#pagination").empty();
  var max_batch = numberOfRowsDisplayed()
  if (max_batch < 10) max_batch = 10;

  getAjaxSqlWhereCountJobs(sql).done(function(total) {
    if (total) {
      //if (total <= max_batch) {
      if (true) {
        data = {where_clause: sql, min: 0, max: 1000000000};
        getAjaxSqlWhereJobs(data).done(function(jobs) {
          dataViewjobs.setItems(JSON.parse(jobs));
          gridjobs.invalidate();
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
      jobs = "[]";
      dataViewjobs.setItems(JSON.parse(jobs));
      gridjobs.invalidate();
    }
  })
}

// Ask the server for the jobs and render them
function reloadJobs() {
  parents = [];
  var tag_param = getParameterByName("filterJobs");
  var affinity_param = getParameterByName("filterJobsAffinity");
  var title_param = getParameterByName("filterJobsTitle");
  var tag = document.getElementById("filterJobs").value;
  var affinity = document.getElementById("filterJobsAffinity").value;
  var title = document.getElementById("filterJobsTitle").value;

  tag_param = tag_param == "NONE" ? "" : tag_param;
  tag = tag == "NONE" ? "" : tag;

  if (tag=='' ) {
    if (isvalidparam(tag_param)) {
      tag=tag_param;
      $("#filterJobs").val(tag);
    }
  }
  if (affinity=='') {
    if (isvalidparam(affinity_param)) {
      affinity=affinity_param;
      $("#filterJobsAffinity").val(affinity);
    }
  }
  if (title=='' ) {
    if (isvalidparam(title_param)) {
      title=title_param;
      $("#filterJobsTitle").val(title);
    }
  }

  var data = {filter:tag}
  $.ajax({ type: "GET", url: "/api/jobs/"+viewJob+"/children", data: JSON.stringify(data), dataType: "json", success: 
    function(data) {
      if (tag != "" || title != "" || affinity != "") {
        var newdata = [];
        for (i = 0; i < data.length; ++i) {
          var filtered = true;
          if (tag != "" && data[i].state != tag)
            filtered = false;
          if (title != "" && data[i].title.search(title) < 0)
            filtered = false;
          if (affinity != "" && data[i].affinity.search(affinity) < 0)
            filtered = false;
          if (filtered)
            newdata.push(data[i]);
        }
        data = newdata;
      }
      jobs = data;
      var idtojob = {}
      for (i = 0; i < jobs.length; ++i) {
        var job = jobs[i]
        idtojob[job.id] = job
        job.dependencies = []
        if (job.total_finished > 0)
          job.avgduration = Math.round(job.duration/job.total_finished); 
        else job.avgduration=job.duration;
      }

      $.ajax({ type: "GET", url: "/api/jobs/"+viewJob+"/childrendependencies", dataType: "json", success: 
        function(data) {
          for (var i = 0; i < data.length; ++i) {
            var job = idtojob[data[i].id];
            if (job)
              job.dependencies.push(data[i].dependency);
          }

          for (var i = 0; i < jobs.length; ++i) {
            var job = jobs[i];
            job.dependencies = job.dependencies.join(",");
          }
          renderJobs();
          document.getElementById("refreshbutton").className = "refreshbutton";
        }
      });
    }
  });

  function getParent(id) {
    if (id == 0) {
      parents.unshift({id:0,title:"Root"});
      renderParents();
    } else {
      $.ajax({ type: "GET", url: "/api/jobs/"+id, data: JSON.stringify(data), dataType: "json", success: 
        function(data) {
          parents.unshift(data);
          getParent(data.parent);
        }
      });
    }
  }
  getParent(viewJob);
}

function startWorkers() {
  $.ajax({ type: "POST", url: "/api/startworkers", data: JSON.stringify(getSelectedWorkers()), dataType: "json", success: 
    function() {
      reloadWorkers();
    }
  });
}

function stopWorkers() {
  $.ajax({ type: "POST", url: "/api/stopworkers", data: JSON.stringify(getSelectedWorkers()), dataType: "json", success: 
    function() {
      reloadWorkers();
    }
  });
}

function workerActivity() {
  for (j=workers.length-1; j >= 0; j--) {
    var worker = workers[j];
    if (selectedWorkers[worker.name]) {
      title:$('#activityWorker').attr("value", worker.name)
      title:$('#activityJob').attr("value", "")
      break;
    }
  }

  reloadActivities()
  page = "activities"
  showPage("activities")
}

function terminateWorkers() {
  if (confirm("Do you really want to terminate the selected worker instances?")) {
    $.ajax({ type: "POST", url: "/api/terminateworkers", data: JSON.stringify(getSelectedWorkers()), dataType: "json", success: 
      function() {
        reloadWorkers ();
      }
    });
  }
}

function jobActivity() {
  for (j=jobs.length-1; j >= 0; j--) {
    var job = jobs[j];
    if (selectedJobs[job.id]) {
      title:$('#activityWorker').attr("value", "")
      title:$('#activityJob').attr("value", job.id)
      break;
    }
  }

  reloadActivities()
  page = "activities"
  showPage("activities")
}

function checkSelectionProperties(list, props, selectedList, idName) {
  var values = []
  for (i = 0; i < list.length; i++) {
    var item = list[i];
    if (selectedList[item[idName]]) {
      for (j = 0; j < props.length; ++j) {
        var value = item[props[j][0]];
        if (values[j] != null && values[j] != value)
          values[j] = MultipleSelection;
        else
          values[j] = value;
      }
    }
  }

  for (i = 0; i < props.length; ++i) {
    if (values[i] == MultipleSelection) {
      // different values
      $('#'+props[i][1]).css("background-color", "orange");
      $('#'+props[i][1]).attr("value", "");
    }
    else if (values[i] == null) {
      // default value
      $('#'+props[i][1]).css("background-color", "white");
      $('#'+props[i][1]).attr("value", props[i][2]);
    } else {
      // unique values
      $('#'+props[i][1]).css("background-color", "white");
      $('#'+props[i][1]).attr("value", values[i]);
    }
  }
  return values;
}

function updateSelectionProp(values, props, prop) {
  for (i = 0; i < props.length; ++i) {
    if (props[i][1] == prop) {
      values[i] = true;
      $('#'+props[i][1]).css("background-color", "greenyellow");
      break;
    }
  }
}

function sendSelectionPropChanges(list, idName, values, props, objects, selectedList, func) {
  if (!props.length)
    return;

  var data = {};
  var idsN = 0;
  for (j=list.length-1; j >= 0; j--) {
    var id = list[j][idName];
    if (selectedList[id]) {
      var _props = {}
      for (i = 0; i < props.length; ++i) {
        if (values[i] == true) {
          var prop = props[i][0];
          var value = $('#'+props[i][1]).attr("value");
          if (prop == "dependencies")
            value = value.split(",");
          _props[prop] = value;
        }
      }
      data[id] = _props;
      idsN++;
    }
  }
  if (!idsN)
    return;

  // One single call
  $.ajax({ type: "POST", url: "/api/"+objects.toLowerCase(), data: JSON.stringify(data), dataType: "json", success:
    function() {
      for (i = 0; i < props.length; ++i) {
        if (values[i] == true) {
          props[i][2] = value;
        }
      }
      func();
    }
  });
}

function setSelectionDefaultProperties(props) {
  for (i = 0; i < props.length; ++i)
    props[i][2] = $('#'+props[i][1]).attr("value");
}

function updateWorkerProps() {
  updatedWorkerProps = checkSelectionProperties(workers, WorkerProps, selectedWorkers, "name");
}

function onchangeworkerprop(prop) {
  updateSelectionProp(updatedWorkerProps, WorkerProps, prop);
}

function updateworkers() {
  sendSelectionPropChanges(workers, 'name', updatedWorkerProps, WorkerProps, "Workers", selectedWorkers,
    function() {
      reloadWorkers();
    }
  );
}

function reloadWorkers() {
  $.ajax({ type: "GET", url: "/api/workers", dataType: "json", success: 
    function(data) {
      workers = data;
      renderWorkers();
      document.getElementById("refreshbutton").className = "refreshbutton";
    }
  });
}

function renderWorkers() {
  $("#workers").empty();

  var table = "<table id='workersTable'>";
  table += "<tr class='title'>\n";

  // Returns the HTML code for a worker title column
  function addTitleHTML(attribute) {
    table += "<th class='headerCell' onclick='"+"setWorkerKey(\""+attribute+"\")'>";    
    var value = workers[0];
    if (value && value[attribute] != null) {
      table += attribute;
      if (attribute == workersSortKey && workersSortKeyToUpper)
        table += " &#8595;";
      if (attribute == workersSortKey && !workersSortKeyToUpper)
        table += " &#8593;";
    } else
      table += attribute;
    table += "</th>";
  }

  addTitleHTML("name");
  addTitleHTML("active");
  addTitleHTML("state");
  addTitleHTML("affinity");
  addTitleHTML("ping_time");
  addTitleHTML("cpu");
  addTitleHTML("memory");
  addTitleHTML("last_job");
  addTitleHTML("finished");
  addTitleHTML("error");
  addTitleHTML("ip");

  table += "</tr>\n";

  function _sort(a,b) {
    var aValue = a[workersSortKey];
    if (typeof aValue == 'string')
      return compareStrings(aValue, b[workersSortKey], workersSortKeyToUpper);
    else
      return compareNumbers(aValue, b[workersSortKey], workersSortKeyToUpper);
  }

  workers.sort(_sort);

  for (i=0; i < workers.length; i++) {
    var worker = workers[i];
    // *** Build the load tab for this worker       
    // A global div
    var load = "<div class='load'>";
    // Add each cpu load
    var loadValue = 0;
    try {
      var workerload = JSON.parse(worker.cpu)
      for (j=0; j < workerload.length; ++j) {
        load += "<div class='loadbar' style='width:" + workerload[j] + "%;height:" + 16/workerload.length + "' />";
        loadValue += workerload[j];
      }
      Math.floor(loadValue/workerload.length);
    }
    catch(err) {
      loadValue = 0;
    }
    // Add the numerical value of the load
    load += "<div class='loadlabel'>" + loadValue + "%</div>";
    load += "</div>";

    // *** Build the memory tab for this worker     
    var memory = "<div class='mem'>";
    memory += "<div class='membar' style='width:" + 100*(worker.total_memory-worker.free_memory)/worker.total_memory + "%' />";

    function formatMem(a) {
      if (a > 1024)
        return Math.round(a/1024*100)/100 + " GB";
      else
        return a + " Mo";
    }

    memLabel = formatMem(worker.total_memory-worker.free_memory);
    memLabel += " / ";
    memLabel += formatMem(worker.total_memory);

    // Add the numerical value of the mem
    memory += "<div class='memlabel'>" + memLabel + "</div>";
    memory += "</div>";

    table += "<tr id='workertable"+i+"' class='entry"+(i%2)+(selectedWorkers[worker.name]?"Selected":"")+"'>"+
      "<td onMouseDown='onClickList(event,"+i+")'>"+worker.name+"</td>"+
      "<td class='active"+worker.active+"' onMouseDown='onClickList(event,"+i+")'>"+worker.active+"</td>"+
      "<td class='"+worker.state+"' onMouseDown='onClickList(event,"+i+")'>"+worker.state+"</td>"+
      "<td class='worker_affinities' onMouseDown='onClickList(event,"+i+")'>"+worker.affinity+"</td>"+
      "<td onMouseDown='onClickList(event,"+i+")'>"+formatDate(worker.ping_time)+"</td>"+
      "<td onMouseDown='onClickList(event,"+i+")'>"+load+"</td>"+
      "<td onMouseDown='onClickList(event,"+i+")'>"+memory+"</td>"+
      "<td onMouseDown='onClickList(event,"+i+")'>"+worker.last_job+"</td>"+
      "<td onMouseDown='onClickList(event,"+i+")'>"+worker.finished+"</td>"+
      "<td onMouseDown='onClickList(event,"+i+")'>"+worker.error+"</td>"+
      "<td>"+worker.ip+"</td>"+
      "</tr>\n";
  }
  table += "</table>";
  $("#workers").append(table);
  $("#workers").append("<br>");
}

function reloadActivities() {
  var data = {}
  var job = $('#activityJob').attr("value")
  if (job != "")
    data.job = job
  var worker = $('#activityWorker').attr("value")
  if (worker != "")
    data.worker = worker
  data.howlong = $('#howlong').attr("value")
  $.ajax({ type: "GET", url: "/api/events", data: data, dataType: "json", success: 
    function(data) {
      activities = data;
      renderActivities();
      document.getElementById("refreshbutton").className = "refreshbutton";
    }
  });
}

function renderActivities() {
  $("#activities").empty();

  var table = "<table id='activitiesTable'>";
  table += "<tr class='title'>\n";

  // Returns the HTML code for a worker title column
  function addTitleHTML(attribute) {
    table += "<th class='headerCell' onclick='"+"setActivityKey(\""+attribute+"\")'>";  
    var value = activities[0];
    if (value && value[attribute] != null) {
      table += attribute;
      if (attribute == activitiesSortKey && activitiesSortKeyToUpper)
        table += " &#8595;";
      if (attribute == activitiesSortKey && !activitiesSortKeyToUpper)
        table += " &#8593;";
    } else
      table += attribute;
    table += "</th>";
  }

  addTitleHTML("start");
  addTitleHTML("job_id");
  addTitleHTML("job_title");
  addTitleHTML("state");
  addTitleHTML("worker");
  addTitleHTML("duration");
  table += "</tr>\n";

  function _sort(a,b) {
    var aValue = a[activitiesSortKey];
    if (typeof aValue == 'string')
      return compareStrings(aValue, b[activitiesSortKey], activitiesSortKeyToUpper);
    else
      return compareNumbers(aValue, b[activitiesSortKey], activitiesSortKeyToUpper);
  }

  activities.sort(_sort);

  for (i=0; i < activities.length; i++) {
    var activity = activities[i];

    date = formatDate(activity.start);
    dura = formatDuration(activity.duration);

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
  table += addSumEmpty("TOTAL");
  table += addSumSimple(activities);
  table += addSumEmpty();
  table += addSumFinished(activities, "state");
  table += addSumEmpty();
  table += addSumAvgDuration(activities, "duration");
  table += "</tr>\n";

  table += "</table>";
  $("#activities").append(table);
  $("#activities").append("<br>");
}

function renderAffinities() {
  $("#affinities").empty();

  var table = "<table id='affinitiesTable'>";
  table += "<tr class='title'>\n";

  // Returns the HTML code for a worker title column
  function addTitleHTML(attribute) {
    table += "<th class='headerCell' onclick='"+"setActivityKey(\""+attribute+"\")'>";  
    var value = activities[0];
    if (value && value[attribute] != null) {
      table += attribute;
      if (attribute == activitiesSortKey && activitiesSortKeyToUpper)
        table += " &#8595;";
      if (attribute == activitiesSortKey && !activitiesSortKeyToUpper)
        table += " &#8593;";
    } else
      table += attribute;
    table += "</th>";
  }

  addTitleHTML("id");
  addTitleHTML("name");

  table += "</tr>\n";

  for (i = 1; i <= 63; ++i) {
    table += "<tr>";
    table += "<td width='50px'>"+i+"</td><td width='200px'><input type='edit' class='ttedit' id='affinity"+i+"' name='affinity' value='' onchange='onchangeaffinityprop("+i+")'></td>"
    table += "</tr>\n";
  }

  updateAffinities();

  table += "</table>";
  $("#affinities").append(table);
  $("#affinities").append("<br>");
}

function onchangeaffinityprop(affinity) {
  $('#affinity'+affinity).css("background-color", "greenyellow");
}

function updateAffinities() {
  $.ajax({ type: "GET", url: "/api/affinities", dataType: "json", success: 
    function(data) {
      affinities = data;
      for (i = 1; i <= 63; ++i) {
        var def = affinities[i];
        if (def)
          $("#affinity"+i).attr("value", def);
        $("#affinity"+i).css("background-color", "white");
      }
      document.getElementById("refreshbutton").className = "refreshbutton";
    }
  });
}

function sendAffinities() {
  var affinities = {};
  for (i = 1; i <= 63; ++i) {
    var affinity = $("#affinity"+i).attr("value");
    if (affinity != null)
      affinities[i] = affinity;
  }

  var data = JSON.stringify(affinities)
  $.ajax({ type: "POST", url: "/api/affinities", data: data, dataType: "json", success: 
    function(data) {
      updateAffinities();
    }
  });
}

function onchangejobprop(prop) {
  updateSelectionProp(updatedJobProps, JobProps, prop);
}

function onToggleJobEditor() {
  $("#job-editor-fields").dialog({
    modal: true,
    title: "Job editor",
  });
}

function updatejobs() {
  sendSelectionPropChanges(jobs, 'id', updatedJobProps, JobProps, "Jobs", selectedJobs,
    function() {
      reloadJobs();
      updateJobProps();
    }
  );
}

function addjob() {
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
    function() {
      setSelectionDefaultProperties(JobProps);
      reloadJobs();
    }
  });
}

function selectJobs() {
  var tag = document.getElementById("selectJobs").value;
  if (tag == "CUSTOM")
    ;
  else if (tag == "NONE")
    selectAll(false);
  else if (tag == "ALL")
    selectAll(true);
  else
    selectAll(true, tag);
}

function onDblClickList(e, i) {
  if (page == "activities") {
    var activity = activities[i];
    renderLog(activity.job_id);
  } else {
    var job = jobs[i];
    job.command != "" ? renderLog(job.id) : goToJob(job.id);
  }
}

// List selection handler
function onClickList(e, i) {
  if (!e) var e = window.event
  document.getElementById("selectJobs").value = "CUSTOM";
  // Unselect if not ctrl keys
  if (!e.ctrlKey) {
    if (page == "jobs") {
      selectedJobs = {};
    } else if (page == "workers")
      selectedWorkers = {};
    else if (page == "activities")
      selectedActivities = {};
  }

  var thelist;
  var selectedList;
  var idName;
  var tableId;
  if (page == "jobs") {
    thelist = jobs;
    selectedList = selectedJobs;
    idName = "id";
    tableId = "jobtable";
  } else if (page == "workers") {
    thelist = workers;
    selectedList = selectedWorkers;
    idName = "name";
    tableId = "workertable";
  } else if (page == "activities") {
    thelist = activities;
    selectedList = selectedActivities;
    idName = "id";
    tableId = "activitytable";
  } else
    return;

  // Unselect if not ctrl keys
  if (!e.ctrlKey) {
    for (j=0; j < thelist.length; j++)
      document.getElementById(tableId+j).className = "entry"+(j%2);
  }

  var begin = e.shiftKey ? Math.min(selectionStart, i) : i
  var end = e.shiftKey ? Math.max(selectionStart, i) : i

  selectionStart = e.shiftKey ? selectionStart : i;

  for (j = begin; j <= end; j++) {
    var item = thelist[j];
    if (item) {
      var selected = e.ctrlKey ? !selectedList[item[idName]] : true;
      selectedList[item[idName]] = selected;
      document.getElementById(tableId+j).className = "entry"+(j%2)+(selected?"Selected":"");
    }
  }

  if (page == "jobs") {
    updateJobProps();
  } else if (page == "workers") {
    updateWorkerProps();
  }

  // Remove selection
  window.getSelection().removeAllRanges();
}

function selectAll(state, filter) {
  var thelist;
  var selectedList;
  var idName;
  var tableId;

  if (page == "jobs") {
    thelist = jobs;
    selectedJobs = {};
    selectedList = selectedJobs;
    idName = "id";
    tableId = "jobtable";
  } else if (page == "workers") {
    thelist = workers;
    selectedWorkers = {};
    selectedList = selectedWorkers;
    idName = "name";
    tableId = "workertable";
  } else
    return;

  if (!state) {
    gridjobs.setSelectedRows([]);
  } else {        
    var selectarray = []
    for (j=0; j < dataViewjobs.getLength(); j++) {
      var item=dataViewjobs.getItem(j)
      if (filter == null || item.state == filter) {
        if (item.id != undefined)
          selectarray.push(item.id)
      }
    }
    var selectedRows = dataViewjobs.mapIdsToRows(selectarray);
    gridjobs.setSelectedRows(selectedRows);
  }

  if (page == "jobs") {
    updateJobProps();
  } else if (page == "workers") {
    updateWorkerProps();
  }
}

function removeSelection() {
  if (confirm("Do you really want to remove the selected jobs ?")) {
    var data = [];
    for (j=jobs.length-1; j >= 0; j--) {
      var job = jobs[j];
      if (selectedJobs[job.id])
        data.push(job.id);
    }
    $.ajax({ type: "DELETE", url: "/api/jobs", data: JSON.stringify(data), dataType: "json", success: 
      function() {
        selectedJobs = {};
        reloadJobs();
        updateJobProps();
      }
    });
  }
}

function startSelection() {
  var data = [];
  for (j=jobs.length-1; j >= 0; j--) {
    var job = jobs[j];
    if (selectedJobs[job.id])
      data.push(job.id);
  }
  $.ajax({ type: "POST", url: "/api/startjobs", data: JSON.stringify(data), dataType: "json", success: 
    function() {
      reloadJobs();
    }
  });
}

function viewSelection() {
  for (j=jobs.length-1; j >= 0; j--) {
    var job = jobs[j];
    if (selectedJobs[job.id] && job.url)
      window.open(job.url);
  }
}

function resetSelection() {
  if (confirm("Do you really want to reset the selected jobs and all their children jobs ?")) {
    var data = [];
    for (j=jobs.length-1; j >= 0; j--) {
      var job = jobs[j];
      if (selectedJobs[job.id])
        data.push(job.id);
    }
    $.ajax({ type: "POST", url: "/api/resetjobs", data: JSON.stringify(data), dataType: "json", success: 
      function() {
        reloadJobs();
      }
    });
  }
}

function resetErrorSelection() {
  if (confirm("Do you really want to reset the selected jobs and all their children jobs tagged in ERROR ?")) {
    var data = [];
    for (j=jobs.length-1; j >= 0; j--) {
      var job = jobs[j];
      if (selectedJobs[job.id])
        data.push(job.id);
    }
    $.ajax({ type: "POST", url: "/api/reseterrorjobs", data: JSON.stringify(data), dataType: "json", success: 
      function() {
        reloadJobs();
      }
    });
  }
}

function pauseSelection() {
  var data = [];
  for (j=jobs.length-1; j >= 0; j--) {
    var job = jobs[j];
    if (selectedJobs[job.id])
      data.push(job.id);
  }
  $.ajax({ type: "POST", url: "/api/pausejobs", data: JSON.stringify(data), dataType: "json", success: 
    function() {
      reloadJobs();
    }
  });
}

function updateJobProps() {
  updatedJobProps = checkSelectionProperties(jobs, JobProps, selectedJobs, "id");
}

function exportCSV() {
  window.open('csv.html?id=' + viewJob);
}

function cutSelection() {
  cutJobs = {}
  for (j=jobs.length-1; j >= 0; j--) {
    var job = jobs[j];
    if (selectedJobs[job.id]) {
      cutJobs[job.id] = true
    }
  }
  selectAll(false)
}

function pasteSelection() {
  var count = 0;
  var data = {}
  for (var id in cutJobs)
    data[id] = {parent:viewJob}
  $.ajax({ type: "POST", url: "/api/jobs", data: JSON.stringify(data), dataType: "json", success: 
    function() {
      reloadJobs();
    }
  });
}

$(document).ready(function() {
  initJobs();
  reloadJobs();
  reloadWorkers();
  reloadActivities();
  showPage("jobs");
  timer=setTimeout(timerCB,4000);
});

