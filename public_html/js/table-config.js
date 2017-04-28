
/*** Config table main functions ***/
function configTableGetActiveTable() {
  var active_tab = document.getElementById("tabs").querySelector(".activetab");
  var table = "";
  switch (active_tab.id) {
    case "jobtab":
      table = "jobsTable";
      break;
    case "workertab":
      table = "workersTable";
      break;
    case "activitytab":
      table = "activitiesTable";
      break;
    case "logtab":
      return;
    case "affinitytab":
      table = "affinitiesTable";
      break;
  }
  return document.getElementById(table);
}

function configTableGetSortKey(table) {
  var sortKey = "";
  var sortKeyToUpper = "";
  switch (table.id) {
    case "jobsTable":
      sortKey = "jobsSortKey";
      sortKeyToUpper = "jobsSortKeyToUpper";
      break;
    case "workersTable":
      sortKey = "workersSortKey";
      sortKeyToUpper = "workersSortKeyToUpper";
      break;
    case "activitiesTable":
      sortKey = "activitiesSortKey";
      sortKeyToUpper = "activitiesSortKeyToUpper";
      break;
  }
  return ({sortKey: sortKey, sortKeyToUpper: sortKeyToUpper});
} 

function configTableGetConfig(table) {
  var config = Object();
  var tableConfig = Object();
  for (th of table.getElementsByTagName("th")) {
    var key = th.dataset.key;
    var order = th.style.order;
    var width = th.style.width;
    var visibility = (th.classList.contains("not-displayed")) ? false : true;
    if (th.querySelector(".sort-arrow") !=  null) var sort = (th.querySelector(".sort-arrow-up") !=  null) ? "up" : "down";
    else var sort = null;
    var sql_input = th.querySelector(".sql-input");
    var sql = (sql_input == null) ? "" : sql_input.value;
    config[key] = [order, width, visibility, sort, sql];
  }
  tableConfig[table.id] = config;
  return tableConfig;
}

function configTableSetInitialConfig(table) {
  // Add order style attribute t o each data cell
  for (tr of table.querySelectorAll("tr")) {
    if (tr.children[0].tagName == "TH") continue;
    tds = tr.children;
    for (i=0; i < tds.length; i++) {
      var td = tds[i];
      td.style.order = i;
    }
  }
  configTableSet = true;
}

function configTableSetConfig(table, column, action, value) {
  var configTable = configTableGetConfig(table); 
  var config = configTable[table.id];
  switch (action) {
    case "resize":
      config[column][1] = value;
      break;
    case "visible":
      config[column][2] = value;
      break;
    case "sortkey":
      config[column][3] = value;
      break;
  }
  configTable[table.id] = config;
  return configTable;
}

function configTableReset() {
  console.log("reset table setup");
  var table = configTableGetActiveTable();
  jobsTheadBuilt = false;
  configJobFilter = false;
  var form = table.querySelector("sql-search-form");
  if (form != null) {
    form.reset();
    for (i = 0; i < form.length; i++) {
      var value = (form[i].dataset.defaultvalue) ? form[i].dataset.defaultvalue : null;
      form[i].value = value;
    }
  }
  localStorage.setItem("table-config-"+table.id, JSON.stringify(configTableGetConfig(table)));
  config = configTableGetConfig(table);
  configTableApplyConfig(config);
} 

function configTableApplyConfig(tableConfig) {
  var configDiff = Object();
  var requireSqlRefresh = false;
  // Get only the differences from current setup
  for (var table_id in tableConfig) {
    var table = document.getElementById(table_id);
    var configNew = tableConfig[table_id];
    var configCur = configTableGetConfig(table)[table_id];
    for (var header in configCur) {
      if (configCur[header].toString() == configNew[header].toString()) continue;
      else {
        configDiff[header] = configNew[header];
        // sql or sortkey changed
        if (configCur[header][3] != configNew[header][3] || configCur[header][4] != configNew[header][4]) requireSqlRefresh = true;
      }
    }
    for (var header in configDiff) {
      var target_header = table.querySelector("th[data-key="+header+"]");
      var target_cells = Array();
      for (var cell of table.querySelectorAll("td")) {
        if (cell.style.order == target_header.style.order) target_cells.push(cell);
      }
      configDiff[header][5] = target_header;
      configDiff[header][6] = target_cells;
    }
  }
  // Apply modifications
  for (var header in configDiff) {
    var order = configDiff[header][0];
  //if (form != null) form.submit();
    var width = configDiff[header][1];
    var visible = configDiff[header][2];
    var sort = configDiff[header][3];
    var sql = configDiff[header][4];
    // Apply on header
    target_header = configDiff[header][5];
    target_header.style.order = order;
    target_header.style.width = width;
    if (visible) target_header.classList.remove("not-displayed");
    else target_header.classList.add("not-displayed");
    switch (sort) {
      case null: 
        break;
      case "up":
        var key = configTableGetSortKey(table);
        window[key["sortKey"]] = header;
        window[key["sortKeyToUpper"]] = true;
        break;
      case "down":
        var key = configTableGetSortKey(table);
        window[key["sortKey"]] = header;
        window[key["sortKeyToUpper"]] = false;
        break;
    }
    if (sql) target_header.querySelector(".sql-input").value = sql;
    // Apply on data cells
    for (var cell of configDiff[header][6]) {
      cell.style.order = order;
      cell.style.width = width;
      if (visible) cell.classList.remove("not-displayed");
      else cell.classList.add("not-displayed");
    }
    if (requireSqlRefresh) table.querySelector(".sql-search-form").submit();
  }
}

function configTableCopyUrl(table) {
}

/*** Visibility ***/
function configTableMenuToggle() {
  var menu = document.getElementById("menu");
  if (menu !== null) {
    document.getElementById("menu-button").innerHTML = "&equiv;";
    menu.remove();
    document.getElementById("content").classList.remove("width-80");
    return;
  }

  var table = configTableGetActiveTable();
  if (!configTableSet) configTableSetInitialConfig(table);

  var menu_inner = '\
  <div id="menu-content" class="flex-column">\
    <legend>Toggle visibility</legend>';
  var config = configTableGetConfig(table)[table.id];

  for (var header in config) {
    var checked = (config[header][2]) ? "checked ": "";
    menu_inner += '<label>'+header+'<input type="checkbox" '+checked+'onchange="columnDisplayToggle(\''+header+'\')"></label>';
  }

  document.getElementById("menu-button").innerHTML = "&raquo;";
  var menu = document.createElement("div");
  menu.setAttribute("id", "menu");
  menu.classList.add("flex-column");
  menu.innerHTML = menu_inner;

  var body = document.getElementsByTagName("body")[0];
  var body_last_child = body.children[body.children.length - 1];
  menu = body.insertBefore(menu, body_last_child.nextSibling);
  document.getElementById("content").classList.add("width-80");
}

function columnDisplayToggle(key) {
  var table = configTableGetActiveTable();
  var config = configTableGetConfig(table)[table.id];
  var visible = true;
  if (config[key][2] == true) visible = false;
  configTableApplyConfig(configTableSetConfig(table, key, "visible", visible));
}

/*** Resizing ***/
function columnResizeStart(event) {
  event.preventDefault();
  var table = configTableGetActiveTable();
  if (!configTableSet) configTableSetInitialConfig(table);
  document.addEventListener("mousemove", columnResizeMove, false);
  document.addEventListener("mouseup", columnResizeEnd, false);
  event.target.parentNode.parentNode.parentNode.setAttribute("id", "resized");
}

function columnResizeMove(event) {
  var table = configTableGetActiveTable();
  var table_offset = Number(table.parentElement.scrollLeft);
  var header = document.getElementById("resized");
  var width = Number(event.clientX - header.offsetLeft + table_offset);
  if (width <= 32) {
    width = "32px";
  } else {
    width = width+"px";
  }
  configTableApplyConfig(configTableSetConfig(table, header.dataset.key, "resize", width));
}

function columnResizeEnd(event) {
  var table = configTableGetActiveTable();
  document.getElementById("resized").removeAttribute("id");
  document.removeEventListener("mousemove", columnResizeMove);
  document.removeEventListener("mouseup", columnResizeEnd);
}

/*** Dragging ***/
function columnDragStart(event) {
  var table = configTableGetActiveTable();
  if (!configTableSet) configTableSetInitialConfig(table);
  //event.preventDefault();
  //event.stopPropagation();
  event.dataTransfer.dropEffect = "move";
  event.currentTarget.parentNode.setAttribute("id", "dragged");
}

function columnDrop(event, side) {
  event.preventDefault();
  var table = configTableGetActiveTable();
  var configTable = configTableGetConfig(table);
  var config = configTable[table.id];
  var origin = document.getElementById("dragged");
  var o_key = origin.dataset.key;
  var o_order = Number(config[o_key][0]);
  var target = event.target;
  while (target.tagName != "TH") {
    target = target.parentElement;
  }
  var t_key = target.dataset.key;
  var t_order = Number(config[t_key][0]);

  if (o_order == t_order) return(clean());

  var direction = (o_order < t_order) ? 1 : -1
  if (direction == 1) {
    if (side == "left") {
      for (let i = o_order + 1; i < t_order; i++) {
        columnSetOrder(i, i - 1);
      }
      config[o_key][0] = t_order - 1;
    } else {
      for (let i = o_order + 1; i <= t_order; i++) {
        columnSetOrder(i, i - 1);
      }
      config[o_key][0] = t_order;
    }
  } else {
    if (side == "left") {
      for (let i = t_order; i <= o_order - 1; i++) {
        columnSetOrder(i, i + 1);
      }
      config[o_key][0] = t_order;
    } else {
      for (let i = t_order + 1; i <= o_order - 1; i++) {
        columnSetOrder(i, i + 1);
      }
      config[o_key][0] = t_order + 1;
    }
  }

  configTable[table.id] = config;
  configTableApplyConfig(configTable);
  clean();

  function columnSetOrder(o_order, t_order) {
    for (c in config) {
      if (config[c][0] == o_order) {
        config[c][0] = t_order;
        return;
      }
    }
  }

  function clean() {
    document.getElementById("dragged").removeAttribute("id");
    for (let hovered of document.querySelectorAll(".dropzone-hover")) { 
      hovered.classList.remove("dropzone-hover");
    }
  }
}

function columnDragOver(event) {
  event.preventDefault();
  var node = event.target;
  var classes = node.classList;
  if (classes.contains("dropzone")) {
    node.classList.add("dropzone-hover");
  }
}

function columnDragLeave(event) {
  event.preventDefault();
  var node = event.target;
  node.classList.remove("dropzone-hover");
}


