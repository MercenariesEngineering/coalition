Coalition aim to be a minimal and robust distributed job manager, to use for example in a renderfarm ;)

The project is written in twisted matrix using xml-rpc.

### Quick documentation ###

## Run a server ##
```
python server.py
```

## Add some jobs ##
```
python control.py -c myCommand -d myDir http://myserver:19211/ add
```

## List the jobs in a terminal ##
```
python control.py http://myserver:19211/ list
```

## Remove a job ##
```
python control.py -i jobId http://myserver:19211/ remove
```

## Run a worker ##
```
python worker.py http://myserver:19211/
```

## Monitor the server ##
```
firefox http://myserver:19211/
```

![http://coalition.googlecode.com/files/coalition.png](http://coalition.googlecode.com/files/coalition.png)