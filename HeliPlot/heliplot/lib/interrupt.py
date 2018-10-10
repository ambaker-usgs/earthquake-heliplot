#!/usr/bin/env python

# --------------------------------------------------------------
# Filename: interrupt.py 
# --------------------------------------------------------------
# Purpose: Interrupt error classes for parallel routines 
# ---------------------------------------------------------------
# Classes:
#	   KeyboardInterruptError() 
#	   TimeoutExpiredError() 
# ---------------------------------------------------------------

class KeyboardInterruptError(Exception): pass
class TimeoutExpiredError(Exception): pass
