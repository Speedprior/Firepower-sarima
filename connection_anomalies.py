# -*- coding: utf-8 -*-
"""
Created on Sat Aug 22 16:08:23 2020

@author: speedprior
"""

import pandas as pd
import itertools, sys, os, glob, re, math, zipfile
from datetime import timedelta
from statsmodels.tsa.statespace.sarimax import SARIMAX
import matplotlib.pyplot as plt
plt.style.use('fivethirtyeight')
import matplotlib
matplotlib.rcParams['axes.labelsize'] = 14
matplotlib.rcParams['xtick.labelsize'] = 12
matplotlib.rcParams['ytick.labelsize'] = 12
matplotlib.rcParams['text.color'] = 'G'
import tkinter as tk
from tkinter import filedialog
 
filePrefix = "30_minute_device"


# File dialog for directory path
def getDirectoryPath(title):
    root = tk.Tk()
    root.title(title)
    root.geometry("400x50")
    root.update()
    root.deiconify()
    root.focus_force()
    reportInputPath = filedialog.askdirectory()
    root.withdraw()
    return(reportInputPath)
 
#hyper-parameter search for auto-regression, integration, and
# moving average order using Akaike Information Criteria
def autoSarimax(y):
  p = d = q = range(0, 2)
  pdq = list(itertools.product(p, d, q))
  seasonal_pdq = [(x[0], x[1], x[2], 48) for x in list(itertools.product(p, d, q))]
  bestModel = {"model":'model','param':(0,0,0),'param_seasonal':(0,0,0,48) ,'aic':sys.maxsize}
  for param in pdq:
      for param_seasonal in seasonal_pdq:
          try:
              print(param + param_seasonal)
              mod = SARIMAX(y,order=param,seasonal_order=param_seasonal,enforce_stationarity=False,enforce_invertibility=False)
              results = mod.fit()
              print('ARIMA{}x{}12 - AIC:{}'.format(param,param_seasonal,results.aic))
              if results.aic < bestModel['aic']: bestModel = {'model':results,'param':\
                 param, 'param_seasonal':param_seasonal,'aic':results.aic}
          except:
              continue
  return(bestModel)
 

#read every csv file in the user-chosen directory with the prefix specified.
# Concantenate them into a dataframe, then convert the field we want to numeric
def readReports():
    reportInputPath = getDirectoryPath("Path to sensor reports")
    reports = pd.DataFrame()
    timeRe = re.compile("[0-9]{14}")
    os.chdir(reportInputPath)
    for file in glob.glob(filePrefix + "*.zip"):
        zipfile.ZipFile(file).extractall()
    for file in glob.glob(filePrefix + "*.csv"):
        timeDF = pd.read_csv(file)
        timeDF.insert(2,'Time',pd.to_datetime(timeRe.findall(file)[0]))
        reports = pd.concat([timeDF,reports])
    reports['Initiator Bytes'] = pd.to_numeric(reports['Initiator Bytes'].str.replace(",",""))
    reports['Responder Bytes'] = pd.to_numeric(reports['Responder Bytes'].str.replace(",",""))
    return reports
 

#Take the big dataframe of all reports and chop it up into separate dataframes
# for each sensor, resampled to end up in exactly 30 minute chunks. Also,
# Get a list of devices included in the report
def collateDevices():
    reports = readReports()
    devices = reports.Device.unique()
    deviceRecords = {}
    for device in devices:
        deviceRecord = reports[reports['Device'].str.contains(device)]
        deviceRecord.index = deviceRecord.Time
        deviceRecord = deviceRecord.resample('30Min').mean().interpolate()
        deviceRecords[device] = deviceRecord
    return deviceRecords,devices

#Train a traffic model for each device in the csv files. Get the confidence
# intervals, and the places they are exceeded. Set the earliest data under
# consideration to three days before the last.
def modelTraffic():
    deviceRecords,devices = collateDevices()
    deviceModels = {}
    for device in devices:
        lastStamp = deviceRecords[device].index[-1]
        start = lastStamp - timedelta(days=3)  
        model = autoSarimax(deviceRecords[device]['Initiator Bytes'])
        pred = model['model'].get_prediction(start=start)
        pred_ci = pred.conf_int()
        excessBytes = pred_ci['upper Initiator Bytes'].lt(deviceRecords[device]['Initiator Bytes'])
        excessBytes = deviceRecords[device][excessBytes] - pred_ci['upper Initiator Bytes'][excessBytes]
        deviceModels[device] = {'model':model,'pred':pred,'pred_ci':pred_ci,\
                                'time':lastStamp,'excess':excessBytes}
    return deviceModels,deviceRecords,devices,start
 
#Build the plots and record the excess bytes
def graphPredictions():
    deviceModels,deviceRecords,devices,start = modelTraffic()
    rows = math.ceil(len(devices)/2)
    fig, ax = plt.subplots(nrows=rows,ncols=2, figsize=(12,rows*3))
    devicePosition = 0
    for column in (0,1):
        for row in range(0,rows):
            if len(devices) <= devicePosition:
                device = devices[devicePosition]
                devicePosition = devicePosition + 1
                lower = deviceModels[device]['pred_ci']['lower Initiator Bytes'][start:]
                upper = deviceModels[device]['pred_ci']['upper Initiator Bytes'][start:]
                ax[row][column].plot(deviceRecords[device]['Initiator Bytes'][start:],color="Orange")
                ax[row][column].fill_between(deviceRecords[device][start:].index,lower[start:],upper[start:])
                ax[row][column].set_title(device)
    fig.tight_layout()
    reportOutputPath = getDirectoryPath("Path to save reports")
    fig.savefig(reportOutputPath + "/baselines_" +  start.strftime("%Y-%h%d%H") + ".png")
    deviceDF = pd.DataFrame(deviceModels)
    deviceDF.to_csv(reportOutputPath + "/" + \
                start.strftime("%Y-%h%d%H") + "_excess_traffic.csv")

def main():
    graphPredictions()
 
if __name__ == "__main__":
    main()
