function writeCSV (str)
{
	if (typeof (str) == "number")
		$("#csv").append(str,",");
	else if (str == "" || str == undefined)
		$("#csv").append(',');
	else
		$("#csv").append('"' + str.replace (/"/gi, '""') + '",');
}

function writeLine (str)
{
	$("#csv").append('</br>');
}

$(document).ready(function()
{
	Args = {}
	url = document.URL.split("?");
	args = url[1].split("&");
	for (i = 0; i < args.length; i++)
	{
		arg = args[i].split("=");
		Args[arg[0]] = arg[1];
	}
	if (Args.id == undefined)
		return;


	$.ajax({ type: "GET", url: "/json/getjobs", data: "id="+Args.id, dataType: "json", success: 
	function(data) 
	{
		for (i = 0; i < data.Vars.length; ++i)
		{
			writeCSV (data.Vars[i]);
		}
		writeLine ();
		for (j = 0; j < data.Jobs.length; ++j)
		{
			var job = data.Jobs[j];
			for (i = 0; i < data.Vars.length; ++i)
			{
				if (data.Vars[i] == "StartTime")
				{
					var start = new Date(job[i]*1000)
					writeCSV (start.getFullYear() + '/' + start.getMonth() + '/' + start.getDate() + ' ' + start.getHours () + ':' + start.getMinutes () + ':' + start.getSeconds());
				}
				else
					writeCSV (job[i]);
			}
			writeLine ();
		}
	}});
});

