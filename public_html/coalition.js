$(document).ready(function()
{
	var xmlrpc = imprt("xmlrpc");
	var service = new xmlrpc.ServerProxy ("/xmlrpc", ["getjobs"]);
	var jobs = service.getjobs ();
	var table = "<table id='jobs'>";
	table += "<tr id='jobtitle'><th>ID</th><th>Title</th><th>State</th><th>Worker</th><th>Try</th><th>StartTime</th><th>PingTime</th><th>Command</th></tr>\n";
	for (i=0; i < jobs.length; i++)
	{
		var job = jobs[i];
		table += "<tr id='job'><td>"+job.ID+"</td><td>"+job.Title+"</td><td>"+job.State+"</td><td>"+job.Worker+"</td><td>"+job.Try+"</td><td>"+job.StartTime+"</td><td>"+job.PingTime+"</td><td>"+job.Command+"</td></tr>\n";
	}
	table += "</table>";
	$("#main").append(table);
});

