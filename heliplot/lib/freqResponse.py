#!/usr/bin/env python

# ---------------------------------------------------------------
# Filename: freqResponse.py 
# ---------------------------------------------------------------
# Purpose: Pull/store frequency responses for queried stations 
# ---------------------------------------------------------------
# Methods:
#	   storeResps() - store responses for each station 
# ---------------------------------------------------------------
import os, sys, re

class FreqResponse(object):
	def storeFilters(self, streamID, networkID, channelID):
		# Check network filter exceptions list and
		# store filter types for each station
		if networkID in self.net_filterexc:
			filtertype = self.net_filterexc[networkID]
		else:
			# Assign default channel filter types
			if channelID == "EHZ":
				filtertype = self.EHZfiltertype
			elif channelID == "BHZ":
				filtertype = self.BHZfiltertype
			elif channelID == "LHZ":
				filtertype = self.LHZfiltertype
			elif channelID == "VHZ":
				filtertype = self.VHZfiltertype
		
		# Assign filter coefficients according to channel/filtertype
		filterstats = {}	
		if channelID == "EHZ":
			if filtertype == "highpass":
				hpfreq = self.EHZhpfreq
				filterstats = {'streamID': streamID,
					'filtertype': filtertype,
					'freqX': hpfreq, 'freqY': ''}
				return filterstats
		elif channelID == "BHZ":
			if filtertype == "bandpass":
				bplower = self.BHZbplowerfreq
				bpupper = self.BHZbpupperfreq
				filterstats = {'streamID': streamID,
					'filtertype': filtertype,
					'freqX': bplower, 'freqY': bpupper}
				return filterstats
			elif filtertype == "bandstop":
				notchlower = self.BHZnotchlowerfreq
				notchupper = self.BHZnotchupperfreq
				filterstats = {'streamID': streamID,
					'filtertype': filtertype,
					'freqX': notchlower, 'freqY': notchupper}
				return filterstats
		elif channelID == "LHZ":
			if filtertype == "bandpass":
				bplower = self.LHZbplowerfreq
				bpupper = self.LHZbpupperfreq
				filterstats = {'streamID': streamID,
					'filtertype': filtertype,
					'freqX': bplower, 'freqY': bpupper}
				return filterstats
			elif filtertype == "bandstop":
				notchlower = self.LHZnotchlowerfreq
				notchupper = self.LHZnotchupperfreq
				filterstats = {'streamID': streamID,
					'filtertype': filtertype,
					'freqX': notchlower, 'freqY': notchupper}
				return filterstats
		elif channelID == "VHZ":
			if filtertype == "lowpass":
				lpfreq = self.VHZlpfreq
				filterstats = {'streamID': streamID,
					'filtertype': filtertype,
					'freqX': lpfreq, 'freqY': ''}
				return filterstats
	
	def storeResps(self, resppath, stream, filelist, streamlen, datetimeUTC,
			EHZfiltertype, EHZhpfreq,
			BHZfiltertype, BHZbplowerfreq, BHZbpupperfreq,
			BHZnotchlowerfreq, BHZnotchupperfreq,
			LHZfiltertype, LHZbplowerfreq, LHZbpupperfreq,
			LHZnotchlowerfreq, LHZnotchupperfreq,
			VHZfiltertype, VHZlpfreq,
			net_filterexc):
		print("-------freqResponse() Start-------\n")	
		
		# Initialize self variables
		self.EHZfiltertype = EHZfiltertype
		self.EHZhpfreq = EHZhpfreq
		self.BHZfiltertype = BHZfiltertype
		self.BHZbplowerfreq = BHZbplowerfreq
		self.BHZbpupperfreq = BHZbpupperfreq
		self.BHZnotchlowerfreq = BHZnotchlowerfreq
		self.BHZnotchupperfreq = BHZnotchupperfreq
		self.LHZfiltertype = LHZfiltertype
		self.LHZbplowerfreq = LHZbplowerfreq
		self.LHZbpupperfreq = LHZbpupperfreq
		self.LHZnotchlowerfreq = LHZnotchlowerfreq
		self.LHZnotchupperfreq = LHZnotchupperfreq
		self.VHZfiltertype = VHZfiltertype
		self.VHZlpfreq = VHZlpfreq
		self.net_filterexc = net_filterexc
	
		# Initialize station ID values
		os.chdir(resppath)
		networkID = []
		stationID = []
		locationID = []
		channelID = []

		# Need stations listed in SeedFiles directory
		for i in range(streamlen):
			tmpstation = filelist[i]
			stationindex = tmpstation.index('_')
			networkID.append(str(tmpstation[0:2]))
			stationID.append(stream[i][0].stats.station)
			locationindex = len(tmpstation)-11
			channelindex = len(tmpstation)-14
			locationID.append(str(tmpstation[locationindex:locationindex+2]))
			channelID.append(str(tmpstation[channelindex:channelindex+3]))

		try:
			print("Get/set station responses...")	
			stationName = []	# station names for output plots
			self.resp = []		# station freq responses for deconvolution
			self.filtertype = []	# station filter list

			print("streamlen = %d\n" % streamlen)
		
			# Loop through stations and get responses (if no resp, rm station)
			i = 0
			while i < len(stream):
				if i == len(stream):
					break	# index = num of streams
				
				# Check for empty loc codes, replace "__" with ""
				if locationID[i] == "__":
					locationID[i] = ""
				resfilename = ("RESP."+networkID[i]+"."+stationID[i]+"."+
					locationID[i]+"."+channelID[i])	# response file

				if not os.path.isfile(resfilename):
					# if no response remove station from stream list
					#streamID = stream[i][0].get_id()
					print("------------------------------------------")	
					print("No response: %s" % resfilename)
					print("Removing stream[%d]: %s" % (i,streamID))
					stream.pop(i)
					networkID.pop(i)
					stationID.pop(i)
					locationID.pop(i)
					channelID.pop(i)
					print("stream[%d] removed..." % i)
					print("------------------------------------------\n")	
					i = i 
				else:
					tmpname = re.split('RESP.', resfilename)
					stationName.append(tmpname[1].strip())
					resp = {'filename': resfilename, 'date': datetimeUTC,
						'units': 'VEL'}	# freq response of data (vel)
					self.resp.append(resp)
					streamID = stream[i][0].get_id() 	
					filterstats = self.storeFilters(streamID, networkID[i], channelID[i])
					self.filtertype.append(filterstats)	
					i = i + 1
		
			self.networkID = networkID
			self.stationID = stationID
			self.locationID = locationID
			self.channelID = channelID
			self.stationName = stationName	# store station names
			self.stream = stream	# store new stream	
			self.streamlen = len(self.stream)	# store new streamlen	
			print("new stationName len = %d" % len(self.stationName))	
			print("new stream len = %d\n" % self.streamlen) 
			print("-------freqResponse() Complete-------\n\n")	
		except KeyboardInterrupt:
			print("KeyboardInterrupt freqResponse(): terminating freqResponse() method")
			sys.exit(0)
			print("Method freqResponse() is terminated!")
		except Exception as e:
			print("Exception freqResponse(): " + str(e))
			sys.exit(0)
			print("Method freqResponse() is terminated!")
