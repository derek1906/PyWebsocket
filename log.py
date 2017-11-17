import time
import sys

def log(msg):
	msg = str(msg)
	if len(msg) == 0:
		msg = "<empty>"
	elif len(msg) > 500:
		msg = msg[:500] + "..."

	current_time = time.strftime("%H:%M:%S", time.localtime())
	msg = msg.replace("\n", "\n" + " " * (len(current_time) + 3))
	
	sys.stdout.write("\r[{}] {}\n".format(current_time, msg))