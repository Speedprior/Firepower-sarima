# Firepower-sarima
This script will ingest a bunch of Firepower connection event reports in csv, and plot the bandwidth alongside the prediction from the SARIMA algorithm. It doesn't do much, but if you have a compliance requirement to baseline the traffic on each sensor, it should do the trick. 

The connection event reports must not include any fields that will break up the report into individual connection events; I didn't put in anything to sum up the sessions for each sensor. For example, my reports just include the 'device,' 'Initiator Bytes,' and 'responder bytes' fields. This will produce one row for each sensor, for each report.

Edit the global variable with the prefix name of your report, e.g. "hour_connection_events." Schedule the compliance reports to run every hour; or every half-hour if your throughput is high enough that you can't store a full hour's worth. Download them all to a single directory, and point the script to that directory when it starts. When it's finished running all the math (SARIMAX hyperparameter search takes most of the time), it'll ask you for an output directory, where it will save a plot of the projected and observed data for each sensor.
