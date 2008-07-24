# Simulate a job ending in error
import time

for i in range(1000) :
	print (i)
	time.sleep (0.01)

os.exit (1)
