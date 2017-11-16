import time

def log(msg):
	current_time = time.strftime("%H:%M:%S", time.localtime())
	msg = str(msg).replace("\n", "\n" + " " * (len(current_time) + 3))
	print("\r[{}] {}".format(current_time, msg))