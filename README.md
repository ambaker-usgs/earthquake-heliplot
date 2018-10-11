# Introduction

HeliPlot.py is a Python application designed to generate heliplot images, thumbnails, and corresponding html files.  The format is that expected by the earthquake.usgs.gov 'Monitoring' web pages for the ANSS Backbone and USGS GSN stations.



# Dependencies

The dependencies that must be satisified to run HeliPlot.py are:
  - Python


## Python

HeliPlot.py was developed using the Miniconda distribution of Python 3.6.  We recommend using either the Miniconda (https://conda.io/miniconda.html) or Anaconda (https://www.anaconda.com/) distributions.  Both use the 'conda' packaging tool, which makes installation of dependencies much simpler.  A file named environment.yml is provided in order to set up a custom conda environment to satisfy the package dependencies.


# Installation

1. Install and configure Python (Miniconda or Anaconda are preferred)

2. Install the application
   git clone https://github.com/usgs/earthquake-heliplot


# Configuration

1. create conda environment

  a. cd to the heliplot directory
  
  b. run the following command to create a custom conda environment named TED
    conda env create -f environment.yml
    
  c. add the following line to the bottom of ~/.bashrc
    source activate heli

2. edit the ~/.bashrc to export the Python library directory.  For example, if the application was installed in /home/heli/heliplot, you would add the following line:
export PYTHONPATH=/home/heli/heliplot/lib

3. configure HeliPlot.py
  a. the configuration file is named HeliPlot.ini, which is located in the heliplot directory
  b. the file is set up to generate heliplots for the ANSS Backbone and USGS GSN stations, alter as needed


# Running HeliPlot.py
Execute the script from the command line or in a crontab.  For example, if HeliPlot.py is in the directory named /home/heli/heliplot, issue the following commands:
cd /home/heli/heliplot
./HeliPlot.py
