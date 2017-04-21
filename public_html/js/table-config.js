
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

function configTableInit() {
  var table = configTableGetActiveTable();
  configTableAddHandlers(table);
  columnDragEnable(table);
  columnResizeEnable(table);

  var menu_inner = '\
  <form id="menu-form">\
    <fieldset>\
      <legend>Table configuration</legend>\
      <fieldset>\
        <legend>Toggle visibility</legend>';
  var columns = configTableGetHeaders(table);
  for (var i in columns) {
    var checked = (table.querySelector("th[data-key="+columns[i]+"]").classList.contains("not-displayed")) ? "unchecked" : "checked";
    menu_inner += '<label>'+columns[i]+'<input type="checkbox" checked="'+checked+'" onchange="columnToggleDisplay('+table.id+', '+i+')"></label>';
  }
  menu_inner += '\
      </fieldset>\
      <button id="menu-form-cancel" type="submit" value="cancel">Cancel</button>\
      <button id="menu-form-save" type="submit" value="save">Save</button>\
      <button id="menu-form-url" type="submit" value="copy-url">Copy url to clipboard</button>\
    </fieldset>\
  </form>';

  document.getElementById("menu-button").classList.add("not-displayed");
  var menu = document.createElement("div");
  menu.setAttribute("id", "menu");
  menu.innerHTML = menu_inner;

  var body = document.getElementsByTagName("body")[0];
  var body_last_child = body.children[body.children.length - 1];
  menu = body.insertBefore(menu, body_last_child.nextSibling);
  document.getElementById("content").classList.add("width-80");

  $("#menu-form").submit(function(e) {
    e.preventDefault();
    var action = $(document.activeElement)[0].value;
    switch (action) {
      case "cancel":
        configTableCancel(table);
      case "save":
        configTableSave(table);
        break;
      case "copy-url":
        configTableUrl(table);
    }
  });
}

function configTableAddHandlers(table) {
  var tr = document.createElement("tr");
  tr.innerHTML = 
  for (header of table.querySelectorAll("th")) {
    var handler = document.createElement("div");
    handler.setAttribute("class", "flex-row handler");
    handler.innerHTML = '\
<div class="flex-row draggable" ondragstart="columnDragStart(event)">\
  <div class="flex-column dropzone half"\
    ondrop="columnDrop(event, '+header.style.order+', \'left\')"\
    ondragover="columnDragOver(event)"\
    ondragleave="columnDragLeave(event)">\
  </div>\
  <div class="flex-column dropzone half"\
    ondrop="columnDrop(event, '+header.style.order+', \'right\')"\
    ondragover="columnDragOver(event)"\
    ondragleave="columnDragLeave(event)">\
  </div>\
</div>\
<div class="flex-column resizable" onmousedown="columnResizeInit(event)"></div>';
    header.insertAdjacentElement("afterbegin", handler);
  }
}

function configTableCancel(table) {
  document.getElementById("menu").remove();
  document.getElementById("content").classList.remove("width-80");
  document.getElementById("menu-button").classList.remove("not-displayed");
  columnDragDisable(table);
  columnRezizeDisable(table);
}

function configTableSave(table) {
  console.log("save config");
}

function configTableCopyUrl(table) {
  console.log("copy url");
}

function configTableGetHeaders(table) {
  var column_headers = table.querySelectorAll("thead th");
  var headers = Object();
  for (header of column_headers) {
    headers[header.style.order] = header.dataset.key;
  }
  return headers;
}

function columnToggleDisplay(table, column) {
  column++;
  table.querySelector("th:nth-child("+column+")").classList.add("not-displayed");
  table.querySelector("td:nth-child("+column+")").classList.add("not-displayed");
}

function eventStopPropagation(event) {
  console.log("stop propagation");
  if (!event) var event = window.event;
  event.cancelBubble = true;
  if (event.stopPropagation) event.stopPropagation();
}

function columnResizeEnable(table) {
  for (resizable of table.querySelectorAll(".resizable")) {
    resizable.classList.remove("not-displayed");
  }
}

function columnResizeDisable(table) {
  for (resizable of table.querySelectorAll(".resizable")) {
    resizable.classList.add("not-displayed");
  }
}

function columnResizeInit(event) {
  console.log("column resize init");
  var table = configTableGetActiveTable();
  var header = event.target.parentNode; 
  columnDragDisable(table);
  document.addEventListener("mousemove", function() {columnResizeMove(header)}, false);
  document.addEventListener("mouseup", function() {columnResizeEnd(header)}, false);
}

function columnResizeMove(header) {
  console.log("column resize");
  var table = configTableGetActiveTable();
  var width = (event.clientX - header.offsetLeft) + 'px';
  header.style.width = width;
  for (cell of table.querySelectorAll("td:nth-child("+header.style.order+")")) {
    cell.style.width = width;
  }
}

function columnResizeEnd(header) {
  console.log("mouse up");
  var table = configTableGetActiveTable();
  document.removeEventListener("mousemove", columnResizeMove);
  document.removeEventListener("mouseup", columnResizeEnd);
  columnDragEnable(table);
}

function columnDragEnable(table) {
  for (draggable of table.querySelectorAll(".draggable")) {
    draggable.setAttribute("draggable", "true");
    draggable.classList.remove("not-displayed");
  }
}

function columnDragDisable(table) {
  for (draggable of table.querySelectorAll(".draggable")) {
    draggable.removeAttribute("draggable");
    draggable.classList.add("not-displayed");
  }
}

function columnDragStart(event) {
  console.log("drag start");
  event.dataTransfer.dropEffect = "move";
  var node = event.target.parentNode;
  var order = node.style.order;
  node.setAttribute("id", "dragged");
  // create hovereable dropzones
  header_cells = node.parentNode.querySelectorAll("th");
  for (let cell of header_cells) {
    var dropzone = document.createElement("div");
    dropzone.setAttribute("class", "flex-row dropzones");
    dropzone.innerHTML = '<div class="flex-column dropzone half" ondrop="columnDrop(event, '+order+', \'left\')" ondragover="columnDragOver(event)" ondragleave="columnDragLeave(event)"></div><div class="flex-column dropzone half" ondrop="columnDrop(event, '+order+', \'right\')" ondragover="columnDragOver(event)" ondragleave="columnDragLeave(event)"></div>';
    cell.insertAdjacentElement("afterbegin", dropzone);
  }
}

function columnDrop(event, order, side) {
  event.preventDefault();
  var origin = document.getElementById("dragged");
  if (origin == null) clean();
  var target = event.target.parentElement.parentElement;
  var target_order = Number(target.style.order);
  if (target_order == "") clean();
  if (order == target_order) clean();
  var direction = (order < target_order) ? 1 : -1
  if (direction == 1) {
    if (side == "left") {
      for (let i = order + 1; i <= target_order - 1; i++) {
        columnSetOrder(i, i - 1);
      }
      origin.style.order = target_order - 1;
    } else {
      for (let i = order + 1; i <= target_order; i++) {
        columnSetOrder(i, i - 1);
      }
      origin.style.order = target_order;
    }
  } else {
    if (side == "left") {
      for (let i = target_order; i <= order - 1; i++) {
        columnSetOrder(i, i + 1);
      }
      origin.style.order = target_order;
    } else {
      for (let i = target_order + 1; i <= order - 1; i++) {
        columnSetOrder(i, i + 1);
      }
      origin.style.order = target_order + 1;
    }
  }
  clean();

  function columnSetOrder(index, new_index) {
    let node = document.querySelector('.active-tab-content th[style="order: '+index+';"]');
    node.style.order = new_index;
  }
    
  function clean() {
    if (origin != null) origin.removeAttribute("id");
    $(".dropzones").remove();
    return;
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
