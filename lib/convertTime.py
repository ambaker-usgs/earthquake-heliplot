#!/usr/bin/env python

# -----------------------------------------------------------
# Filename: convertTime.py 
# -----------------------------------------------------------
# Purpose: Converts python time output to readable min/sec 
# -----------------------------------------------------------
# Methods: 
#	   setTime() - set the time using python time input 
# -----------------------------------------------------------
import os

class ConvertTime(object):
	def setTime(self, time):
		if time >= 60:
			end = "m"
			newtime = time / 60.0
		else:
			end = "s"
			newtime = time
		return newtime,end

