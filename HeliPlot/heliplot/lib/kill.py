#!/usr/bin/env python

# -----------------------------------------------------------
# Filename: kill.py 
# -----------------------------------------------------------
# Purpose: Kill subprocess launches and/or multiprocessing
#	   pool. These methods use parent/child/grandchild
#	   pids to search and destroy hanging processes
# -----------------------------------------------------------
# Methods: 
#	   killSubprocess() - kills system subprocess child
#	   killPool() - kills pool of method workers
# -----------------------------------------------------------
import psutil
import signal
import os, time

class Kill(object):
	def killSubprocess(self, childpid, gchildpid, signum):
		# ---------------------------------------
		# Kills pool subprocess child/grandchild
		# proc.kill()
		# proc.send_signal(signum)	# kill child (just in case)
		# proc.terminate()	# stop grandchild proc
		# (out, err) = proc.communicate()
		# raise subprocess.TimeoutExpired(proc.args, output=out)
		# os.killpg(proc.pid, signum)	# kill process group
		# ---------------------------------------
		print("Child proc:	%6s" % childpid)
		print("Killing gchild:	%6s" % gchildpid) 	
		time.sleep(1)
		# Send kill signal to child/grandchild (terminate/kill)
		os.kill(gchildpid, signum)	# kill grandchild process	
		#os.kill(childpid, signum)	# kill child process
		time.sleep(1)

	def killPool(self, pid, name):
		# ---------------------------------------
		# Kills multiprocessing pool and children
		# sys.exit(0)
		# os.wait()	# wait for all threads to exit
		# pool.terminate()
		# pool.join()
		# pkill -TERM -P 'pid' - kill process group
		# kill -- -$PGID - kill parent/child/gchild
		# ---------------------------------------
		print("Pool %s is terminated" % name)
		parent = psutil.Process(pid)
		print("Parent pid:	%6s" % pid)
		print("Killing children of pool: %6s..." % pid)
		#time.sleep(1)
		# set recursive=True to kill grandchildren
		for child in parent.get_children(recursive=True):
			if 'terminated' in str(child):
				print("\tterminated child: " + str(child))
			else:	
				print("\tkilling child: " + str(child))
				child.kill()	# kill children of pool
			time.sleep(1)	
		print("Killing pool:	%6s..." % pid)
		time.sleep(1)
		parent.kill()	# kill pool (parent)
