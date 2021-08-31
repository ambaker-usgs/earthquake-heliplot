#!/usr/bin/env python

# -----------------------------------------------------------
# Filename: parallelcwbQuery.py
# -----------------------------------------------------------
# Purpose: Creates multiprocessing pool to run multiple 
#	   instances of CWBQuery.jar. CWBQuery pulls station
#	   seed files from specified server (Golden/ASL)
# -----------------------------------------------------------
# Methods:
#	   launchWorkers() - launches pool of cwbQuery workers
#	   cwbQuery() - queries stations from station.cfg
# -----------------------------------------------------------
import multiprocessing
from multiprocessing import Manager, Value
import os, sys, string, subprocess
import time, signal, glob

from lib.kill import Kill 
from lib.interrupt import KeyboardInterruptError, TimeoutExpiredError

# Unpack self from parallel method args and call cwbQuery()
def unwrap_self_cwbQuery(args, **kwargs):
	return ParallelCwbQuery.cwbQuery(*args, **kwargs)

class ParallelCwbQuery(object):
	def __init__(self):
		# Initialize kill object for class
		self.killproc = Kill()
	
	def cwbQuery(self, station):
		# ------------------------------------------------
		# Pull specific station seed files using CWBQuery	
		# ------------------------------------------------
		for attempt in range(self.cwbattempts):
			try:
				cmd = ("java -jar " + self.cwbquery +
					" -s " + '"'+station+'"' + " -b " + '"'+self.datetimeQuery+
					'"' + " -d " + '"'+str(self.duration)+'"' +
					" -t dcc512 -o " + self.seedpath+"%N_%y_%j -h " +
					'"'+self.ipaddress+'"')
				# print(cmd)
				# may want to implement a logger to track system
				# pid hangs and program exceptions
				#print ("java -jar " + self.cwbquery + " -s " + '"'+station+'"' +
				#	" -b " + '"'+self.datetimeQuery+'"' + " -d " + 
				#	'"'+str(self.duration)+'"' + " -t dcc512 -o " + self.seedpath+"%N_%y_%j -h " +
				#	'"'+self.ipaddress+'"')
				subproc = subprocess.Popen([cmd],
					stdout=subprocess.PIPE, stderr=subprocess.PIPE,
					preexec_fn=os.setsid, shell=True)
				(out, err) = subproc.communicate(timeout=self.cwbtimeout) # waits
				#time.sleep(2)
				out = out.decode("utf-8")
				err = err.decode("utf-8")

				# Set pids and kill args for killSubprocess() method 
				self.parentpid = os.getppid()
				self.childpid = os.getpid()
				self.gchildpid = subproc.pid
				#print("parent pid: " + str(self.parentpid))
				#print("child  pid: " + str(self.childpid))
				#print("gchild pid: " + str(self.gchildpid))
				if (len(out) == 0):
					print("Query on " + station)
					print("Returned 0 blocks\n")
				print(str(out))
				print(str(err))
				sys.stdout.flush()
				sys.stderr.flush()
			except subprocess.TimeoutExpired:
				print("TimeoutExpired cwbQuery(): retrying (attempt %d)..." % attempt)
				time.sleep(self.cwbsleep)

				if attempt == (self.cwbattempts-1):
					print("TimeoutExpired cwbQuery(): terminate workers...")
					signum = signal.SIGKILL	
					killargs = {'childpid': self.childpid,
						    'gchildpid': self.gchildpid,
						    'signum': signum}
					self.killproc.killSubprocess(**killargs) 
					sys.stdout.flush()
					sys.stderr.flush()
					raise TimeoutExpiredError()
					return 	# returns to cwbQuery pool
			except KeyboardInterrupt:
				print("KeyboardInterrupt cwbQuery(): terminate workers...")
				signum = signal.SIGKILL
				killargs = {'childpid': self.childpid,
					    'gchildpid': self.gchildpid,
					    'signum': signum}
				self.killproc.killSubprocess(**killargs)
				raise KeyboardInterruptError()
				return
			except Exception as e:
				print("UnknownException cwbQuery(): " + str(e))
				signum = signal.SIGKILL
				killargs = {'childpid': self.childpid,
					    'gchildpid': self.gchildpid,
					    'signum': signum}
				self.killproc.killSubprocess(**killargs)
				return
			else:
				break
	
	def launchWorkers(self, stationinfo, cwbquery, cwbattempts, 
			  cwbsleep, cwbtimeout, datetimeQuery, 
			  duration, seedpath, ipaddress):
		# ---------------------------------------------
		# Initialize all vars needed to run cwbQuery()
		# ---------------------------------------------
		print("------cwbQuery() Pool------\n")
		files = glob.glob(seedpath+"*")
		self.cwbquery = cwbquery	
		self.cwbattempts = cwbattempts	
		self.cwbsleep = cwbsleep	
		self.cwbtimeout = cwbtimeout
		self.datetimeQuery = datetimeQuery
		self.duration = duration
		self.seedpath = seedpath	
		self.ipaddress = ipaddress
		
		for f in files:
			os.remove(f)	# remove tmp seed files from SeedFiles dir
		stationlen = len(stationinfo)

		# ---------------------------------------------
		# Create multiprocessing pools to run multiple
		# instances of cwbQuery()
		# ---------------------------------------------
		PROCESSES = multiprocessing.cpu_count()
		print("PROCESSES:	" + str(PROCESSES))
		print("stationlen:	" + str(stationlen) + "\n")	
		pool = multiprocessing.Pool(PROCESSES)
		try:
			self.poolpid = os.getpid()
			self.poolname = "cwbQuery()"
			#print "pool PID:	" + str(self.poolpid) + "\n"
			pool.map(unwrap_self_cwbQuery, list(zip([self]*stationlen, stationinfo)))
			
			# pool.close()/pool.terminate() must be called before pool.join()
			# pool.close(): prevents more tasks from being submitted to pool,
			#               once tasks have been completed the worker processes 
			#		will exit
			# pool.terminate(): tops worker processes immediately without 
			#		    completing outstanding work, when the pool
			#		    object is garbage collected terminate() will
			#		    be called immediately
			# pool.join(): wait for worker processes to exit
			pool.close()
			pool.join()
			print("------cwbQuery() Pool Complete------\n\n")
		except TimeoutExpiredError:
			print("\nTimeoutExpired parallelcwbQuery(): terminating pool...")
			# find/kill all child processes
			killargs = {'pid': self.poolpid, 'name': self.poolname} 
			self.killproc.killPool(**killargs)
		except KeyboardInterrupt:
			print("\nKeyboardInterrupt parallelcwbQuery(): terminating pool...")
			killargs = {'pid': self.poolpid, 'name': self.poolname} 
			self.killproc.killPool(**killargs)
		else:
			# cleanup (close pool of workers)
			pool.close()
			pool.join()
