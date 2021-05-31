## Install dependencies
To install dependencies run `pip3 install -r requirements.txt`

## Working of the script
The script would accept configuration from the user in a config file. Configurable file can broadly be divided into multiple sections viz:

### Tenant-level:
**tenant-URL**: The tenant for which the script would collect from.
**Token**: Tenant with read permissions to Billing and API-V2 metrics.
**DEM-Utilization threshold**: Customer defined threshold for DEM utilization.

### Email-details:
**SMTP-server**: SMTP server details that would be used to send the email/alert
**SMTP-username**: Username of the SMTP server
**Password**: Password of SMTP username
**SMTP-Port**: Port on which the SMTP server is running 

### Config.json:
Please find below the config file that the need to fill in -  
![config](dem-threshold/config.png) 

The script makes API call to pull data for past 2-hours and populates two csv files per day viz:
1.	tmp_DDMMYYY.csv – It would capture total consumption of DEM units for that day.
2.	DDMMYYY.csv - It would constitute the DEM consumption for each application for that day. So typically, a day would have 12 entries.

### Output generated:
The script would need to be scheduled to run every 2 hours and would be able to collect DEM utilization for the past 2-hours. Once pulled individually for each application, synthetic monitors, and http monitors, it will publish the data in csv file for that day and compute the total utilization. The total computation would then be compared with the configured threshold (“DEM-Utilization-threshold”) and depending on the threshold, it will fire an alert email.

If the total consumption is <= 40% of the configured threshold, the alert would be fired with “WARNING”, whereas, for 80% and above, it would be fired as an “ALERT”. The email would also contain the DEM usage for that day along with the csv file with details, so that the customer can identify the application that has used DEM usage and take an action accordingly. 

Sample outputs for both the alerts. 
![warning](dem-threshold/warning.msg)  
![alert](dem-threshold/alert.msg)  

**Potential improvement**:
Whilst this is not supported in the script yet, script can be enhanced to implement the following logic:
A configuration API can be triggered alongwith the email to limit the data-capture on the application utilizing maximum DEM for that day. Doing so would help to reduce any manual intervention required with virtually no turn around time once the alert is generated.
