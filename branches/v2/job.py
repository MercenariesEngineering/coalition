# Simulate a job ending in error
import time, sys

for i in range(1000) :
	print (i)
	time.sleep (0.01)

sys.exit (0)