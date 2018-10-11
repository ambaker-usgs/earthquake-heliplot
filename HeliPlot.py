#!/usr/bin/env python

import configparser
from argparse import ArgumentParser
import os
from datetime import datetime, timedelta
import re
from obspy.core.utcdatetime import UTCDateTime
from pathlib import Path
from shutil import copyfile
from dateutil.tz import tzlocal

import kill
import parallelcwbQuery
import pullTraces
import freqResponse
import paralleldeconvFilter
import magnifyData
import parallelplotVelocity
import createThumbnails
import convertTime
import time
import sys

####################
def validate_config_file(config):
    """
    Purpose: Process config file to ensure all sections and key/value pairs
             are present.  Also, initialize and load the data dictionaries
             for each section.
         
    Arguments: handle to config file

    Returns: config file dictionaries
    """

    # initialize dictionaries
    setup_dict = {}
    plot_dict = {}
    cwbquery_dict = {}
    filters_dict = {}
    stations_dict = {}
    
    required_sections = ["SETUP", "PLOT", "CWBQUERY", "FILTERS", "STATIONS"]
    for section in required_sections:
        if not config.has_section(section):
            msg = "ERROR - Config file '{}' is missing the '{}' section"
            msg = msg.format(configfile, section)
            print(msg)
            sys.exit(1)

    print('All sections in ' + configfile + ' are present')

    ############################
    # process [SETUP] section
    section = 'SETUP'
    keys = {'data_dir', 'plot_dir', 'resp_dir', 'nodata_file'}
    for key in keys:
        if not config.has_option(section, key):
            msg = "ERROR - Config file '{}' '{} section is missing key '{}'"
            msg = msg.format(configfile, section, key)
            print(msg)
            sys.exit(1)
        else:
            setup_dict[key] = config.get(section, key)
            
    # make sure all the directories exist and then tack on a trailing / to each
    if not os.path.isdir(setup_dict['data_dir']):
        print("ERROR: [SETUP] section 'data_dir' does not exist")
        sys.exit(1)
    setup_dict['data_dir'] = setup_dict['data_dir'] + "/"

    if not os.path.isdir(setup_dict['plot_dir']):
        print("ERROR: [SETUP] section 'plot_dir' does not exist")
        sys.exit(1)
    setup_dict['plot_dir'] = setup_dict['plot_dir'] + "/"
    
    if not os.path.isdir(setup_dict['resp_dir']):
        print("ERROR: [SETUP] section 'resp_dir' does not exist")
        sys.exit(1)
    setup_dict['resp_dir'] = setup_dict['resp_dir'] + "/"

    # make sure the nodata file is there
    if not os.path.exists(setup_dict['nodata_file']):
        print("ERROR: [SETUP] section 'nodata_file' does not exist")
        sys.exit(1)

    ############################
    # process [PLOT] section
    section = 'PLOT'
    keys = {'default_magnification',
            'dpi', 'xres', 'yres',
            'format', 'thumbscale', 'vertical_scaling'}
    for key in keys:
        if not config.has_option(section, key):
            msg = "ERROR - Config file '{}' '{} section is missing key '{}'"
            msg = msg.format(configfile, section, key)
            print(msg)
            sys.exit(1)
        else:
            plot_dict[key] = config.get(section, key)


    ############################
    # process [CWBQUERY] section
    section = 'CWBQUERY'
    keys = {'cwbquery_jar', 'duration', 'ipaddress', 'httpport',
            'timeout', 'retries', 'sleep_time'}
    for key in keys:
        if not config.has_option(section, key):
            msg = "ERROR - Config file '{}' '{} section is missing key '{}'"
            msg = msg.format(configfile, section, key)
            print(msg)
            sys.exit(1)
        else:
            cwbquery_dict[key] = config.get(section, key)

    ############################
    # process [FILTERS] section
    section = 'FILTERS'
    keys = {'EHZfiltertype', 'EHZhpfreq',
            'BHZfiltertype', 'BHZbplowerfreq', 'BHZbpupperfreq',
            'BHZnotchlowerfreq', 'BHZnotchupperfreq',
            'LHZfiltertype', 'LHZbplowerfreq', 'LHZbpupperfreq',
            'LHZnotchlowerfreq', 'LHZnotchupperfreq',
            'VHZfiltertype', 'VHZlpfreq',
            'network_filter_exclude', 'network_magnification_exclude',
            'station_magnification_exclude'}
    for key in keys:
        if not config.has_option(section, key):
            msg = "ERROR - Config file '{}' '{} section is missing key '{}'"
            msg = msg.format(configfile, section, key)
            print(msg)
            sys.exit(1)
        else:
            filters_dict[key] = config.get(section, key)

    ############################
    # process [STATIONS] section
    section = 'STATIONS'
    keys = []
    for item in config.items(section):
        keys.append(item[0].upper())
    for key in keys:
        stations_dict[key] = config.get(section, key)

    
    return (setup_dict, plot_dict, cwbquery_dict, filters_dict, stations_dict)


################################
################################
if __name__ == '__main__':
    # Main program for running each HeliPlot module and tracking times

    # -------------------------
    # initialize timer variables
    # -------------------------
    totalTime = 0
    run_times = {}  # dictionary containing run times for different steps

# -------------------
    # handle command line - the only option is --help
    program_name = 'HeliPlot'
    description = 'Generate web content (heliplot/html files) for earthquake.usgs Monitoring web pages.'
    parser = ArgumentParser(prog=program_name, usage=program_name + ' [--help]',
                            description=description)
    parser.parse_args()

    # Create file spec for the working directory and open the config file
    homedir = os.path.dirname(os.path.abspath(__file__))
    configfile = os.path.join(homedir, program_name + '.ini')
    if not os.path.isfile(configfile):
        log_msg = "Config file '{}' does not exist"
        log_msg = log_msg.format(configfile)
        print(log_msg)
        sys.exit(1)
    config = configparser.ConfigParser()
    config.read_file(open(configfile))

# -------------------
    # validate the config file (make sure all sections and required
    # key/value pairs are present) - also, load the section dictionaries
    setup_dict, plot_dict, cwbquery_dict, filters_dict, stations_dict = validate_config_file(config)

#    for key in filters_dict:
#        print("filters_dict[" + key + "] = " + filters_dict[key])
#    sys.exit(0)
    
# -------------------
    # turn stations dict into a list
    # CU_ANWB = 00/LHZ |  Willy Bob, Antigua and Barbuda
    station_list = []
    for key in stations_dict:
        tmp = key.split('_')
        net_sta = tmp[0] + tmp[1]
        # pad to length of 7
        net_sta = net_sta.ljust(7)
        tmp = stations_dict[key].split('|')
        loc_chan = tmp[0].strip()
        tmp = loc_chan.split('/')
        chan_loc = tmp[1] + tmp[0]
        station_list.append(net_sta + chan_loc)
#    for i in range(len(station_list)):
#        print("station_list[" + str(i) + "] = [" + station_list[i] + "]")
#    sys.exit(0)
    
# -------------------
    # reformat/split the network exceptions  list (used in
    # freqResponse)
    tmpnetfilt = re.split(',', filters_dict['network_filter_exclude'])
    net_filterexc = {}
    for i in range(len(tmpnetfilt)):
        tmpnetfilt[i] = tmpnetfilt[i].strip();
        tmpexc = re.split(':', tmpnetfilt[i])
        net_filterexc[tmpexc[0].strip()] = str(tmpexc[1].strip())
    
# -------------------
    # setup the date fields
    # datetimeUTC is for obspy's use in freqResponse
    utc_time  = datetime.utcnow() - timedelta(days=1)
    timestring = str(utc_time)
    timestring = re.split("\\.", timestring)
    tmp = timestring[0]
    timedate = tmp.replace("-", "/")
    datetimeQuery = timedate.strip()
    tmpUTC = datetimeQuery
    tmpUTC = tmpUTC.replace("/", "")
    tmpUTC = tmpUTC.replace(" ", "_")
    datetimeUTC = UTCDateTime(str(tmpUTC))

    # plot start/end are used in labelling the plots
    start_time = utc_time + timedelta(hours=1)
    start_time_str = start_time.strftime("%Y%m%d_%H:00:00")
    end_time = start_time + timedelta(days=1)
    end_time_str = end_time.strftime("%Y%m%d_%H:00:00")
    plot_start = UTCDateTime(start_time_str)
    plot_end = UTCDateTime(end_time_str)

# -------------------
    # use cwbQuery to get data
    query = parallelcwbQuery.ParallelCwbQuery()    # initialize parallel cwbQuery object
    t1 = time.time()

#    # set ending time for call to CWBQuery.jar
    timestring = str(datetime.utcnow() - timedelta(days=1))
    timestring = re.split("\\.", timestring)
    tmp = timestring[0]
    timedate = tmp.replace("-", "/")
    datetimeQuery = timedate.strip()
    
    queryargs = {'stationinfo':   station_list,
                 'cwbquery':      cwbquery_dict['cwbquery_jar'], 
                 'cwbattempts':   int(cwbquery_dict['retries']),
                 'cwbsleep':      int(cwbquery_dict['sleep_time']),
                 'cwbtimeout':    int(cwbquery_dict['timeout']),
                 'datetimeQuery': datetimeQuery,
                 'duration':      cwbquery_dict['duration'],
                 'seedpath':      setup_dict['data_dir'],
                 'ipaddress':     cwbquery_dict['ipaddress']}
    query.launchWorkers(**queryargs)
    run_times['Pull data'] = round(time.time() - t1, 2)

# -------------------
    # read in the data files and analyze         
    strm = pullTraces.PullTraces()
    t1 = time.time()
    strm.analyzeRemove(setup_dict['data_dir'])
    run_times['Load data'] = round(time.time() - t1, 2)

# -------------------
    # Pull freq responses from queried stations and store
    # also store station filter types
    resp = freqResponse.FreqResponse()
    t1 = time.time()    
    respargs = {'resppath':           setup_dict['resp_dir'],
                'stream':             strm.stream, 
                'filelist':           strm.filelist,
                'streamlen':          strm.streamlen, 
                'datetimeUTC':        datetimeUTC,
                'EHZfiltertype':      filters_dict['EHZfiltertype'],
                'EHZhpfreq':          float(filters_dict['EHZhpfreq']),
                'BHZfiltertype':      filters_dict['BHZfiltertype'],
                'BHZbplowerfreq':     float(filters_dict['BHZbplowerfreq']),
                'BHZbpupperfreq':     float(filters_dict['BHZbpupperfreq']),
                'BHZnotchlowerfreq':  float(filters_dict['BHZnotchlowerfreq']),
                'BHZnotchupperfreq':  float(filters_dict['BHZnotchupperfreq']),
                'LHZfiltertype':      filters_dict['LHZfiltertype'],
                'LHZbplowerfreq':     float(filters_dict['LHZbplowerfreq']),
                'LHZbpupperfreq':     float(filters_dict['LHZbpupperfreq']),
                'LHZnotchlowerfreq':  float(filters_dict['LHZnotchlowerfreq']),
                'LHZnotchupperfreq':  float(filters_dict['LHZnotchupperfreq']),
                'VHZfiltertype':      filters_dict['VHZfiltertype'],
                'VHZlpfreq':          float(filters_dict['VHZlpfreq']),
                'net_filterexc':      net_filterexc}
    resp.storeResps(**respargs)
    run_times['Get responses'] = round(time.time() - t1, 2)
    
# -------------------
    # Deconvolve/filter queried stations
    fltr = paralleldeconvFilter.ParallelDeconvFilter()
    t1 = time.time()    
    fltrargs = {'stream':    resp.stream,
                'streamlen': resp.streamlen,
                'response':  resp.resp,
                'filters':   resp.filtertype}
    fltr.launchWorkers(**fltrargs)
    run_times['Filter data'] = round(time.time() - t1, 2)
#    sys.exit(0)
    
# -------------------
    # Magnify trace data
    mag = magnifyData.MagnifyData()
    t1 = time.time()

    # reformat network and station mag. excludes
    tmpnetmag = re.split(',', filters_dict['network_magnification_exclude'])
    net_magnificationexc = {}
    for i in range(len(tmpnetmag)):
        tmpnetmag[i] = tmpnetmag[i].strip();
        tmpexc = re.split(':', tmpnetmag[i])
        net_magnificationexc[tmpexc[0].strip()] = float(tmpexc[1].strip())
#        print("net_magnificationexc[" + tmpexc[0].strip() + "] = [" + str(net_magnificationexc[tmpexc[0].strip()]) + "]")
        
    tmpstatmag = re.split(',', filters_dict['station_magnification_exclude'])
    stat_magnificationexc = {}	
    for i in range(len(tmpstatmag)):
        tmpstatmag[i] = tmpstatmag[i].strip();	
        tmpexc = re.split(':', tmpstatmag[i])
        stat_magnificationexc[tmpexc[0].strip()] = float(tmpexc[1].strip())
#        print("stat_magnificationexc[" + tmpexc[0].strip() + "] = [" + str(stat_magnificationexc[tmpexc[0].strip()]) + "]")
    
    magargs = {'flt_streams': fltr.flt_streams,
               'net_magnificationexc': net_magnificationexc,
               'stat_magnificationexc': stat_magnificationexc,
               'magnification_default': float(plot_dict['default_magnification'])}
    magnified_streams = mag.magnify(**magargs)
    run_times['Magnify data'] = round(time.time() - t1, 2)

# -------------------
    # Plot filtered/magnified streams
    plt = parallelplotVelocity.ParallelPlotVelocity()
    t1 = time.time()
    pltargs = {'streams':           magnified_streams,
               'plotspath':         setup_dict['plot_dir'],
               'stationName':       resp.stationName,
               'magnification':     mag.magnification,
               'vertrange':         float(plot_dict['vertical_scaling']),
               'datetimePlotstart': plot_start,
               'datetimePlotend':   plot_end,
               'resx':              int(plot_dict['xres']),
               'resy':              int(plot_dict['yres']),
               'pix':               int(plot_dict['dpi']),
               'imgformat':         plot_dict['format'],
               'filters':           resp.filtertype}
    plt.launchWorkers(**pltargs)
    run_times['Make plots'] = round(time.time() - t1, 2)
    
# -------------------
    # nodata.png is an 800x600 png file containing the text
    # 'Data Not Available'.  If CWB data weren't available,
    # there won't be a png file in setup['plot_dir'], in which
    # case we need to copy nodata.png to station.png
    src_file = setup_dict['nodata_file']
    count = 0
    for key in stations_dict:
        fields = key.split('_')
        station_code = fields[1]
        dest_file = setup_dict['plot_dir'] + station_code + ".png"
        my_file = Path(dest_file)
        if my_file.is_file() is False:
            copyfile(src_file, dest_file)
            count = count + 1
    print("\n'Data Not Available' files copied for stations missing data: " + str(count) + "\n")

# -------------------
    # Create thumbnails from full-sized png files - make sure to
    # do this after copying in nodata.png to plot dir for stations
    # with no data
    thm = createThumbnails.CreateThumbnails()
    t1 = time.time()
    thmargs = {'thumbpath':  setup_dict['plot_dir'],
               'plotspath':  setup_dict['plot_dir'],
               'thumbscale': float(plot_dict['thumbscale'])}
    thm.convertImage(**thmargs)
    run_times['Make thumbs'] = round(time.time() - t1, 2)

# -------------------
    # create the HTML files
    local_TZ = datetime.now(tzlocal()).tzname()
    local_time = datetime.today()
    local_time_str = local_time.strftime("%a %m/%d/%y %H:%M") + " " + local_TZ
    utc_time = datetime.utcnow()
    utc_time_str = utc_time.strftime("%a %m/%d/%y %H:%M") + " UTC"
    width = "1280"
    height = "700"
    align = "center"
    count = 0
    for key in stations_dict:
        fields = key.split('_')
        network_code = fields[0]
        station_code = fields[1]
        fields = stations_dict[key].split('|')
        long_name = fields[1].strip()
        image = "./" + station_code + ".png"
        htmlname = setup_dict['plot_dir'] + station_code + "_24hr.html"

        html = open(htmlname, 'w')
        html.write("<!DOCTYPE html>\n")
        html.write("<html>\n")
        html.write("\t<head>\n")
        html.write("\t\t<title>USGS TELEMETRY DATA</title>\n")
        html.write("\t</head>\n")
        html.write("\t<body>\n")
        html.write("\t\t<h2><CENTER>Data from Station " + network_code + " " + station_code + " (" + long_name + ")</CENTER></h2>\n")
        html.write("\t\t<h3><CENTER>last updated at </CENTER></h3>\n")
        html.write("\t\t<h3><CENTER>" + local_time_str + " (" + utc_time_str + ")</CENTER></h3>\n")
        html.write("\t\t<CENTER><img src=" + '"' + image + '"' + " width=" + '"' + width + '"' + " height=" + '"' + height + '"' + "></CENTER>\n")
        html.write("\t\t<p align=" + '"' + align + '"' + ">\n")
        html.write("\t</body>\n")
        html.write("</html>")
        html.close()
        count = count + 1
    print("\nHTML files generated: " + str(count) + "\n")

    
# -------------------
    # print run-time statistics and exit
    total_time = 0.0
    print("Execution times:")
    for key in run_times:
        total_time = total_time + run_times[key]
        print("\t" + key + ": \t\t" + str(run_times[key]) + " seconds")

    print("Total Elapsed Time:\t\t " + str(round(total_time, 2)) + " seconds")

    sys.exit(0)
