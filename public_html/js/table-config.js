
/*** Config table main functions ***/
function configTableGetActiveTable() {
  var active_tab = document.getElementById("tabs").querySelector(".activetab");
  if (active_tab === null) return null;
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

function configTableGetFormForTable(table) {
  switch (table.id) {
    case "jobsTable":
      var form = document.getElementById("sql-search-job");
  }
  return form;
}

function configTableGetSortKey(table) {
  // Get current sort  key and sort direction
  var sortKey = "";
  var sortKeyToUpper = "";
  var config = configTableGetConfig(table);
  for (var i in config) {
    if (config[i][3] !== null) {
      sortKey = i;
      sortKeyToUpper = (config[i][3] === "up") ? true : false;
      break;
    }
  }
  return ({sortKey: sortKey, sortKeyToUpper: sortKeyToUpper});
}

function configTableGetSortKeyFromStorage(table) {
  var sortKey = "";
  var sortKeyToUpper = "";
  var configTable = configTableGetConfigFromStorage();
  var config = configTable[table.id];
  for (var i in config) {
    if (config[i][3] !== null) {
      sortKey = i;
      sortKeyToUpper = (config[i][3] === "up") ? true : false;
      break;
    }
  }
  return ({sortKey: sortKey, sortKeyToUpper: sortKeyToUpper});
}

function configTableGetConfig(table) {
  // Get config for table from document state
  var config = Object();
  var ths = table.getElementsByTagName("th");
  for (let i = 0; i < ths.length; i++) {
    let th = ths[i];
    var key = th.dataset.key;
    var order = th.style.order;
    var width = th.style.width;
    var visibility = (th.classList.contains("not-displayed")) ? false : true;
    if (th.querySelector(".sort-arrow") !=  null) var sort = (th.querySelector(".sort-arrow-up") !=  null) ? "up" : "down";
    else var sort = null;
    var sql = Array();
    var sqlInput = th.querySelector(".sql-input");
    if (sqlInput) {
      switch(sqlInput.tagName) {
        case "INPUT":
          var sql = sqlInput.value;
        case "SELECT":
          var options = sqlInput.selectedOptions;
          if (options !== undefined) {
            for (let i = 0; i < options.length; i++) {
              sql.push(options[i].value);
            }
          }
      }
    }
    config[key] = [order, width, visibility, sort, sql];
  }
  return config;
}

function configTableGetConfigFromStorage() {
  // Get config from localstorage
  // Build and empty initial config if absent
  var config = JSON.parse(window.localStorage.getItem("config-table"));
  if (config === null) {
    var tables = document.querySelectorAll("table");
    var config = Object();
    for (let i = 0; i < tables.length; i++) {
      config[tables[i].id] = Object();
    }
    window.localStorage.setItem("config-table", JSON.stringify(config));
  }
  return config;
}

function configTableSetConfig(table, column, key, value) {
  var config = configTableGetConfig(table);
  switch (key) {
    case "move":
      config[column][0] = value;
      break;
    case "resize":
      config[column][1]  = value;
      break;
    case "visible":
      config[column][2] = value;
      break;
    case "sortkey":
      for (var c in config) {
        config[c][3] = null;
      }
      config[column][3] = value;
      break;
    case "sql":
      config[column][4] = value;
  }
  return config;
}

function configTableSetConfigToStorage(table, newConfig) {
  let config = configTableGetConfigFromStorage();
  config[table.id] = newConfig;
  window.localStorage.setItem("config-table", JSON.stringify(config));
  return config;
}

function configTableReset() {
  window.localStorage.removeItem("config-table");
  reloadJobs();
}

function configTableApplyConfig(configTables, force=false, sqlRefresh=false, table=null) {
  // Apply the provided tableConfig object to the document
  // By default, change as few attributes as possible, except when force=true where all the configuration values are applied
  // sql request is done when sql_refresh=true
  // configTables is the configuration for all tables, except if table is provided. In this case configTables is the configuration for this table only
  if (table !== null) {
    let configTable = Object();
    configTable[table.id] = configTables;
    configTables = configTable;
  }
  for (var table_id in configTables) {
    if (table_id !== "jobsTable" && table_id !== "workersTable" ) {
      return;
    }
    var table = document.getElementById(table_id);
    var configNew = configTables[table_id];
    var configCur = Object();
    var configDiff = Object();
    if (force === true) {
      for (header in configNew) {
        configCur[header] = "";
      }
    } else {
      var configTable = configTableGetConfigFromStorage();
      if (configTable !== null && configTable[table_id] !== undefined && Object.keys(configTable[table_id]).length !== 0) {
        configCur = configTable[table_id];
      } else {
        for (header in configNew) {
          configCur[header] = "";
        }
      }
    }
    for (var header in configNew) {
      if (configCur[header].toString() == configNew[header].toString()) continue;
      else {
        configDiff[header] = Object.assign({}, configNew[header]);
      }
    }

    for (var header in configDiff) {
      var target_header = table.querySelector("th[data-key="+header+"]");
      var target_cells = Array();
      var cells = table.querySelectorAll("td");
      for (let i = 0; i < cells.length; i++) {
        let cell = cells[i];
        if (cell.style.order == target_header.style.order) {
          target_cells.push(cell);
        }
      }
      configDiff[header][5] = target_header;
      configDiff[header][6] = target_cells;
    }
    // Apply modifications
    for (var header in configDiff) {
      var order = configDiff[header][0];
      var width = configDiff[header][1];
      var visible = configDiff[header][2];
      var sort = configDiff[header][3];
      var sql = configDiff[header][4];
      var target_header = configDiff[header][5];
      var target_cells = configDiff[header][6];
      // Apply on header
      target_header.style.order = order;
      target_header.style.width = width;
      if (visible) target_header.classList.remove("not-displayed");
      else target_header.classList.add("not-displayed");
      if (sort === "up" || sort === "down") {
        columnSortArrowSet(table, header, sort);
      }
      if (sql !== undefined && sql !== null && String(sql).length) {
        var input = target_header.querySelector(".sql-input");
        switch (input.type) {
          case "datetime-local":
          case "text":
          case "number":
          case "search":
            input.value = sql;
            break;
          case "range":
            input.value = sql;
            var label = target_header.querySelector("label");
            label.innerHTML = label.innerHTML.replace(/\d+/, sql);
            break;
          case "select-multiple":
            var options = input.options;
            for (let i = 0; i < options.length; i++) {
              options[i].selected = sql.includes(options[i].value);
            }
            break;
        }
      }
      // Apply on data cells
      for (var cell of target_cells) {
        cell.style.order = order;
        cell.style.width = width;
        if (visible) cell.classList.remove("not-displayed");
        else cell.classList.add("not-displayed");
      }
    }
    if (sqlRefresh && table.id === configTableGetActiveTable().id) {
      document.getElementById("submit-sql-search-"+table.id).click();
    }
  }
}

function configTableCopyUrl() {
  // Copy the url with table configuration ino clipboad
  var origin_url = window.location["origin"];
  var config = configTableGetConfigFromStorage();
  var url = origin_url + '/?config-table=' + JSON.stringify(config);
  var editableNode = document.getElementById("copy-url-textarea");
  editableNode.classList.remove("not-displayed");
  editableNode.value = url;
  editableNode.select();
  document.execCommand("copy");
  editableNode.classList.add("not-displayed");
}

function configTableGetConfigFromUrl() {
  // Apply table config located in URL search parameters
  // and restore clean URI
  const params = new URLSearchParams(location.search);
  var config = params.get("config-table");
  if (config) {
    config = JSON.parse(config);
    for (let table_id in config) {
      table = document.getElementById(table_id);
      if (table !== null) configTableSetConfigToStorage(table, config[table_id]);
    }
    window.location.href = window.location["origin"]+window.location.pathname;
  }
  getSqlWhereJobs();
  getSqlWhereWorkers();
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

  var menu_inner = '\
  <div id="menu-content" class="flex-column">\
    <legend>Columns displayed</legend>';
  var config = configTableGetConfig(table);

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
  var config = configTableGetConfig(table);
  var visible = (config[key][2] === true) ? false: true;
  config = configTableSetConfig(table, key, "visible", visible);
  configTableApplyConfig(configTableSetConfigToStorage(table, config), force=true, sqlRefresh=false);
}

/*** Resizing ***/
function columnResizeStart(event) {
  event.preventDefault();
  var table = configTableGetActiveTable();
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
  var config = configTableSetConfig(table, header.dataset.key, "resize", width);
  configTableApplyConfig(config, force=true, sqlRefresh=false, table=table);
}

function columnResizeEnd(event) {
  var table = configTableGetActiveTable();
  var config = configTableGetConfig(table);
  configTableSetConfigToStorage(table, config);
  document.getElementById("resized").removeAttribute("id");
  document.removeEventListener("mousemove", columnResizeMove);
  document.removeEventListener("mouseup", columnResizeEnd);
}

/*** Dragging ***/
function columnDragStart(event) {
  event.dataTransfer.setData('text', null);
  event.dataTransfer.effectAllowed = "move";
  event.currentTarget.parentNode.setAttribute("id", "dragged");
}

function columnDrag(event) {
}

function columnDragOver(event) {
  event.preventDefault();
  event.dataTransfer.dropEffect = "move";
  var node = event.target;
  var classes = node.classList;
  if (classes.contains("dropzone")) {
    if (node.tagName === "LABEL") {
      var parentNode = node.parentElement;
      parentNode.classList.add("dropzone-hover");
    }
    node.classList.add("dropzone-hover");
  }
}

function columnDragEnter(event) {
  event.preventDefault();
}

function columnDragLeave(event) {
  event.preventDefault();
  for (var node of document.querySelectorAll(".dropzone-hover")) {
    node.classList.remove("dropzone-hover");
  }
}

function columnDrop(event, side) {
  event.preventDefault();
  var table = configTableGetActiveTable();
  var config = configTableGetConfig(table);
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

  var configTable = configTableGetConfigFromStorage();
  configTable[table.id] = config;
  configTableApplyConfig(configTable);
  configTableSetConfigToStorage(table, config);
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
    let dropzones = document.querySelectorAll(".dropzone-hover");
    for (let i = 0; i < dropzones.length; i++) {
      dropzones[i].classList.remove("dropzone-hover");
    }
  }
}

/*** sort ***/
function columnSortArrowSet(table, column, direction) {
  var target = table.querySelector("th[data-key=\'"+column+"\'] .side-left");
  var sortKey = document.createElement('div');
  sortKey.classList.add("sort-arrow", "dropzone");
  switch(direction) {
    case "up":
      sortKey.innerHTML = "&uarr;";
      sortKey.classList.add("sort-arrow-up");
      break;
    case "down":
      sortKey.innerHTML = "&darr;";
      sortKey.classList.add("sort-arrow-down");
      break;
  }
  if (target !== null) {
    var previousSortArrow = target.querySelector(".sort-arrow");
    if (previousSortArrow === null) {
      target.appendChild(sortKey);
    } else {
      previousSortArrow.innerHTML = sortKey.textContent;
    }
  }
}

