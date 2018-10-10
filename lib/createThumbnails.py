#!/usr/bin/env python

# ---------------------------------------------------------------
# Filename: createThumbnails.py 
# ---------------------------------------------------------------
# Purpose: Create thumbnails from heli output plots (350x262) 
# ---------------------------------------------------------------
# Methods:
#	   convertImage() - creates thumbnail image 
# ---------------------------------------------------------------
import os, glob, re
import matplotlib.image as img

class CreateThumbnails(object):
    def convertImage(self, thumbpath, plotspath, thumbscale):
        os.chdir(thumbpath)	# cd into thumbnails dir
        if (thumbpath == plotspath):
            print("Image/thumbnail paths match: NOT removing current images...")
        else:
            # print("Image/thumbnail paths DO NOT match: removing previous images...")
            thmfiles = glob.glob(thumbpath + "*")
            for f in thmfiles:
                os.remove(f)	# rm tmp thumbnails from Thumbnails dir

        # read from output plots dir
        imgfiles = glob.glob(plotspath + "*")
        #print("thumbscale = " + str(thumbscale)) 
        cnt = 0

        for filespec in imgfiles:
            # get the original file name
            tmp = re.split('/', filespec)
            orig_filename = tmp[len(tmp) - 1].strip()

            # the filename format is station_name.png - parse
            # the station_name
            tmp = re.split('\.', orig_filename)
            station_name = tmp[0].strip()	# pull station name

            # make the new spec by appending _24hr.png to
            # the station_name
            new_name = station_name + "_24hr.png"

            # create the thumbnail version of the original image
            img.thumbnail(filespec, new_name, scale=thumbscale)
            cnt = cnt + 1

        print("thumbnails generated: " + str(cnt) + "\n")
