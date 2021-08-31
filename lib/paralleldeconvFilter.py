#!/usr/bin/env python

# --------------------------------------------------------------
# Filename: paralleldeconvFilter.py
# --------------------------------------------------------------
# Purpose: Simulates/filters station data stream. Simulating
#	   produces a deconvolved signal. Pre-filter bandpass
#	   corner frequencies eliminate end frequency spikes
#	   (ie H(t) = F(t)/G(t), G(t) != 0)
#
#	   *NOTE: Currently LHZ/BHZ/VHZ/EHZ have different 
#	   filter designs, higher freq channels will need to
#	   use a notch or high freq filter later on
# ---------------------------------------------------------------
# Methods:
#	   launchWorkers() - multiprocessing pool for filters
#	   deconvFilter() - deconvolve/filter station data 
# ---------------------------------------------------------------
import multiprocessing
import os, sys, string, subprocess
import time, signal, glob, re
import numpy as np
import linecache

from multiprocessing import Manager, Value
from lib.kill import Kill 
from lib.interrupt import KeyboardInterruptError, TimeoutExpiredError

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    print('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))


# Unpack self from parallel method args and call deconvFilter()
def unwrap_self_deconvFilter(args, **kwargs):
	return ParallelDeconvFilter.deconvFilter(*args, **kwargs)

class ParallelDeconvFilter(object):
	def __init__(self):
		# Initialize kill object for class
		self.killproc = Kill()

	def deconvFilter(self, stream, response, filters):
		# ----------------------------------------
		# Deconvolve/filter each station, filters
		# are based on channel IDs	
		# ----------------------------------------
		streamID = stream[0].get_id()
		tmpstr = re.split("\\.", streamID) 
		networkID = tmpstr[0].strip()	
		stationID = tmpstr[1].strip()
		respID = response['filename'].strip()
		netstatID = networkID + stationID 
	
		# Get filter types from filters[{},{},...]
		if streamID in filters['streamID']:
			filtertype = filters['filtertype']
			freqX = filters['freqX']
			freqY = filters['freqY']

		# Try/catch block for sensitivity subprocess
		try:
			#print("Stream/Filter: " + netstatID + " / " + str(filtertype)) 

			# Deconvolution (removes sensitivity)
			sensitivity = "Sensitivity:"	# pull sensitivity from RESP file
			grepSensitivity = ("grep " + '"' + sensitivity + '"' + " " +
				respID + " | tail -1")
			self.subprocess = True	# flag for exceptions (if !subprocess return)
			subproc = subprocess.Popen([grepSensitivity], stdout=subprocess.PIPE,
				stderr=subprocess.PIPE, shell=True)
			(out, err) = subproc.communicate(timeout=10)	# waits for child proc
			out = out.decode("utf-8")
			out = str(out)

			# Store/print pids for exception kills
			self.parentpid = os.getppid()
			self.childpid = os.getpid()
			self.gchildpid = subproc.pid

			# Pull sensitivity from subproc
			tmps = out.strip()
			tmps = re.split(':', tmps)
			tmps = tmps[1]
			tmps = tmps.replace(' ', '')
			tmps = tmps.replace("'", "")

			s = float(tmps)
			print("Stream/Filter: " + netstatID + " / " + str(filtertype) + " Sensitivity: " + str(s)) 
			sys.stdout.flush()
			sys.stderr.flush()
			self.subprocess = False	# subprocess finished

			# deconvolution (this will be a flag for the user)
			# stream.simulate(paz_remove=None, pre_filt=(c1, c2, c3, c4), 
			# 	seedresp=response, taper='True') 

			# Remove transient response and decimate signals to SR=1Hz 
			decfactor = int(stream[0].stats.sampling_rate)
			stream.detrend('demean')	# removes mean in data set
			#stream.taper(max_percentage=0.01/2.0, type='cosine')	# cos tapers beginning/end to remove transient resp
			stream.decimate(decfactor, no_filter=True, strict_length=False)	

			# Filter stream based on channel (remove sensitivity) 
			if filtertype == "bandpass":
				print("Bandpass filter: %.3f-%.3fHz" % (freqX, freqY))
				maxval = np.amax(stream[0].data) 
				stream.filter(filtertype, freqmin=freqX,
					freqmax=freqY, corners=4)	# bp filter 
				stream[0].data = stream[0].data / s
			elif filtertype == "bandstop":
				print("Bandstop filter: %.3f-%.3fHz" % (freqX, freqY))
				maxval = np.amax(stream[0].data)
				stream.filter(filtertype, freqmin=freqX,
					freqmax=freqY, corners=4)	# notch filter
				stream[0].data = stream[0].data / s
			elif filtertype == "lowpass":
				print("Lowpass filter: %.2f" % freqX) 
				stream.filter(filtertype, freq=freqX, corners=4) # lp filter 
				stream[0].data = stream[0].data / s
			elif filtertype == "highpass":
				print("Highpass filter: %.2f" % freqX) 
				stream.filter(filtertype, freq=freqX, corners=4) # hp filter
				stream[0].data = stream[0].data / s
			print("Filtered stream: " + str(stream) + "\n")
			return stream
		except subprocess.TimeoutExpired:
			print("TimeoutExpired deconvFilter(): terminate workers...")
			if self.subprocess:
				signum = signal.SIGKILL
				killargs = {'childpid': self.childpid,
					    'gchildpid': self.gchildpid,
					    'signum': signum}
				self.killproc.killSubprocess(**killargs)
			sys.stdout.flush()
			sys.stdout.flush()
			raise TimeoutExpiredError()
			return	# return to deconvFilter pool
		except KeyboardInterrupt:
			print("KeyboardInterrupt deconvFilter(): terminate workers...")
			if self.subprocess:
				signum = signal.SIGKILL
				killargs = {'childpid': self.childpid,
					    'gchildpid': self.gchildpid,
					    'signum': signum}
				self.killproc.killSubprocess(**killargs)
			raise KeyboardInterruptError()
			return
		except Exception as e:
			PrintException()
			print("UnknownException deconvFilter(): " + str(e))
			if self.subprocess:
				signum = signal.SIGKILL
				killargs = {'childpid': self.childpid,
					    'gchildpid': self.gchildpid,
					    'signum': signum}
				self.killproc.killSubprocess(**killargs)
			return

	def launchWorkers(self, stream, streamlen, response, filters):
		# ---------------------------------
		# Simulate/filter queried stations
		# ---------------------------------
		print("-------deconvFilter() Pool-------\n")
		# Merge traces to eliminate small data lengths, 
		# method 0 => no overlap of traces (i.e. overwriting
		# of previous trace data, gaps fill overlaps)
		# method 1 => fill overlaps using interpolation for
		# values between both vectors for x num of samples
		for i in range(streamlen):
			try:
				stream[i].merge(method=1, fill_value='interpolate',
					interpolation_samples=100)
			except Exception as e:
				print('Error merging traces:', e)

		# Deconvolution/Prefilter
		# Initialize multiprocessing pools
		PROCESSES = multiprocessing.cpu_count()
		print("PROCESSES:	" + str(PROCESSES))
		print("streamlen:	" + str(streamlen) + "\n")	

		pool = multiprocessing.Pool(PROCESSES)
		try:
			self.poolpid = os.getpid()
			self.poolname = "deconvFilter()"
			flt_streams = pool.map(unwrap_self_deconvFilter,
				list(zip([self]*streamlen, stream, response, filters)))
			pool.close()
			pool.join()
			self.flt_streams = flt_streams
			print("-------deconvFilter() Pool Complete-------\n\n")
		except TimeoutExpiredError:
			print("\nTimeoutExpiredError parallelDeconvFilter(): terminating pool...")
			# find/kill all child processes
			killargs = {'pid': self.poolpid, 'name': self.poolname}
			self.killproc.killPool(**killargs)
		except KeyboardInterrupt:
			print("\nKeyboardInterrupt parallelDeconvFilter(): terminating pool...")
			killargs = {'pid': self.poolpid, 'name': self.poolname}
			self.killproc.killPool(**killargs)
		else:
			# cleanup (close pool of workers)
			pool.close()
			pool.join()
