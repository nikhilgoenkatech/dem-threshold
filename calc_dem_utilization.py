import os
import csv
import time
import json
import smtplib
import logging
import requests
import traceback
import collections
import pandas as pd
from constant import *
from email import encoders
from matplotlib import pyplot as plt
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

class tenantInfo:
   def __init__(self):
     self.name = ""
     self.tenant_url = ""
     self.tenant_get_token = ""
     self.threshold = ""

class host_details:
   def __init__(self):
     self.host_name = ""
     self.host_ipaddress = []
     self.host_unit_consumption = 0

class email_details:
  def __init__(self):
    self.smtpserver = ""
    self.username = ""
    self.password = ""
    self.port = 0
    self.senders_list = ""
    self.receivers_list = ""

class app:
  def __init__(self):
   self.name = ""
   self.type = ""
   self.entityId = ""
   self.consumption = 0
   self.dem = 0

class synthetic_mon:
   def __init__(self):
     self.monitor_name = ""
     self.monitor_type = ""
     self.monitor_tags = ""
     self.monitor_url = ""
     self.monitor_freq =""
     self.monitor_loc_count = 0

#------------------------------------------------------------------------
# Author: Nikhil Goenka
# filename: the config file which the user would configure
#------------------------------------------------------------------------
def parse_config(filename):
  try:
    stream = open(filename)
    data = json.load(stream)
  except Exception as e:
    traceback.print_exc()
    print ("Exception encountered in parse_config function : %s ", str(e))
  finally:
    return data

#------------------------------------------------------------------------
# Author: Nikhil Goenka
# Function to call API and populate the excel file
#------------------------------------------------------------------------
def populate_tenant_details(logger, tenant, tenant_info):
  try:
    logger.info("In populate_tenant_details")
    logger.info("In populate_tenant_details %s ", tenant)

    tenant_info.tenant_url = tenant['tenant-URL']
    tenant_info.tenant_get_token = tenant['GET-token']
    tenant_info.name = tenant['tenant-name']
    tenant_info.threshold = tenant['DEM-Utilization-threshold']
  except Exception as e:
    print ("Exception encountered while executing populate_tenant_details %s ", str(e))
  finally:
    return tenant_info

#------------------------------------------------------------------------------
# Author: Nikhil Goenka
# Function to make API call using the token defined in constant.py
# Returns the json object returned using the API call
#------------------------------------------------------------------------------
def dtApiQuery(logger, endpoint, tenant_info, URL=""):
  try:
    data = {}
    logger.info("In dtApiQuery")
    logger.debug ("dtApiQuery: endpoint = %s", endpoint)

    if URL == "":
      URL = tenant_info.tenant_url

    query = str(URL) + str(endpoint)
    get_param = {'Accept':'application/json', 'Authorization':'Api-Token {}'.format(tenant_info.tenant_get_token)}
    populate_data = requests.get(query, headers = get_param, verify=False)

    if populate_data.status_code >=200 and populate_data.status_code <= 400:
      data = populate_data.json()

  except Exception as e:
    logger.error("Received exception while running dtApiQuery ", exc_info = e)

  finally:
    logger.info("Execution sucessfull: dtApiQuery  ")
    return data

#------------------------------------------------------------------------
# Author: Nikhil Goenka
# Function to fetch all the synthetic browsers and append it to the list "app_list" 
#------------------------------------------------------------------------
def populate_sessions_details(logger, err_msg, app_list, tenant_info, consumption_details, query, syn = 0):
  try:
    logger.info("In populate_sessions_details")
    logger.debug("populate_sessions_details = %s", query)
  
    url = (tenant_info.tenant_url).replace("v1","v2")
    applications = dtApiQuery(logger, query, tenant_info, url)
    apps = applications['result'][0]['data']

    for billing in apps:
      dimensions = billing['dimensions']
      if syn == 0:
        if dimensions[1] == "Billed":
          consumption_details[dimensions[0]] = billing['values'][0]

      elif syn >= 0:
          consumption_details[dimensions[0]] = billing['values'][0]
          logger.debug(billing['values'][0])

    logger.info("Successful execution: populate_sessions_details")

  except Exception as e:
    err_msg = "Received exception while executing populate_sessions_details " + str(e)
    logger.fatal("Received exception while running populate_sessions_details ", str(e), exc_info=True)
    
  finally:
    return app_list, consumption_details, err_msg

#------------------------------------------------------------------------
# Author: Nikhil Goenka
# Function to calculate dem consumptions based on types of monitor using "app_list" and "consumption_details" dictionary
#------------------------------------------------------------------------
def populate_dem_consumption(logger, err_msg, app_list, consumption_details, total_consumption):
  try:
    logger.info("In populate_dem_consumption")
 
    csv_data = {} 
    for key in consumption_details.keys():
      for app in app_list:
        if app.entityId == key:
         if app.type == "Synthetic":
           consumption = float(consumption_details[key] * 1.0)
           app.dem = float(app.dem) + float(consumption)
           total_consumption = total_consumption + consumption

         elif app.type == "HTTP":
           consumption = float(consumption_details[key] * 0.1)
           app.dem = float(app.dem) + float(consumption)
           total_consumption = total_consumption + consumption

         else:
           consumption = float(consumption_details[key] * 0.25)
           app.dem = float(app.dem) +  float(consumption)
           total_consumption = total_consumption + consumption
         
         key = app.name
         csv_data[key] = app.dem

    logger.info("Successful execution: populate_dem_consumption")

  except Exception as e:
    err_msg = "Received exception while executing populate_dem_consumption " + str(e)
    logger.fatal("Received exception while running populate_dem_consumption ", str(e), exc_info=True)
    
  finally:
    return app_list, consumption_details, total_consumption, csv_data, err_msg
#------------------------------------------------------------------------
# Author: Nikhil Goenka
# Function to call API and populate the excel file
#------------------------------------------------------------------------

def fetch_application(logger, err_msg, tenant_info, app_list, query):
  try:
    logger.info("In fetch_application")
    logger.debug("fetch_application = %s", query)
   
    applications = dtApiQuery(logger, query, tenant_info)

    for application in applications:
      appInfo = app()
      appInfo.name = application['displayName']

      #For custom-type application, applicationType is not populated, hence the check
      try:
        appInfo.type = application['applicationType']
      except KeyError:
        appInfo.type = "Custom Application"

      appInfo.entityId = application['entityId']
      app_list.append(appInfo)
    
  except Exception as e:
    err_msg = "Received exception while executing fetch_applications " + str(e)
    logger.fatal("Received exception while running fetch_application ", str(e), exc_info=True)

  finally:
    logger.info("Successful execution: fetch_application")
    return app_list, err_msg

#------------------------------------------------------------------------
# Author: Nikhil Goenka
# Function to fetch all the synthetic browsers and append it to the directory "app_mgmt_zone" 
#------------------------------------------------------------------------
def fetch_syn_application(logger, err_msg, app_list, tenant_info, query):
  try:
    logger.info("In fetch_syn_application")
    logger.debug("fetch_syn_application = %s", query)
   
    #print query
    applications = dtApiQuery(logger, query, tenant_info)
    application = applications['monitors']

    for i in range(len(application)):
      appInfo = app()
      appInfo.name = application[i]['name']

      #For custom-type application, applicationType is not populated, hence the check
      try:
        if application[i]['type'] is not "HTTP":
          appInfo.type = "Synthetic"
        else:
          appInfo.type = "HTTP"
      except KeyError:
        appInfo.type = "Synthetic"
          
      appInfo.entityId = application[i]['entityId']
      app_list.append(appInfo)
 
    logger.info("Successful execution: fetch_sync_application")
    
  except Exception as e:
    err_msg = "Received exception while executing fetch_syn_application " + str(e)
    logger.fatal("Received exception while running fetch_syn_application ", str(e), exc_info=True)

  finally:
    return app_list, err_msg
#------------------------------------------------------------------------
# Author: Nikhil Goenka
# Function to call API and populate the excel file
#------------------------------------------------------------------------
def populate_smtp_variable(data, logger, smtp_server_details):
  try:
    smtp_server = data['email-details']
    smtp_server_details.username = smtp_server['username']
    smtp_server_details.password = smtp_server['password']
    smtp_server_details.smtpserver = smtp_server['server']
    smtp_server_details.port = int(smtp_server['port'])
    smtp_server_details.senders_list = smtp_server['senders-list']
    smtp_server_details.receivers_list = smtp_server['receiver-list']

  except Exception as e:
    traceback_print.exc()
    logger.error("Exception encountered while executing populate_smtp_variable %s ", str(e))

  finally:
    return smtp_server_details
#------------------------------------------------------------------------------
# Author: Nikhil Goenka
# Function to initialize the email server
# Returns the smtp_server initialized 
#------------------------------------------------------------------------------

def initialize_email_server(logger, smtp_server_details):
  try:
    logger.info("In initialize_email_server")
    smtp_server = smtplib.SMTP(smtp_server_details.smtpserver,smtp_server_details.port)
    smtp_server.connect(smtp_server_details.smtpserver,smtp_server_details.port)
    smtp_server.starttls()
    smtp_server.ehlo()

    smtp_server.login(smtp_server_details.username, smtp_server_details.password)
    logger.info("Execution sucessfull: initialize_email_server")

  except Exception as e:
    traceback.print_exc()
    logger.error("Received exception while running initialize_email_server", str(e), exc_info = True)

  finally:
    return smtp_server

#------------------------------------------------------------------------------
# Author: Nikhil Goenka
# Function to send an email
#------------------------------------------------------------------------------
def send_email(err_msg, logger, smtp_server, content, smtp_server_details):
  try:
    logger.info("In send_email")
    logger.debug ("send_email: smtp_server = %s", smtp_server)
    logger.debug ("send_email: message = %s", content)
    content["From"] = smtp_server_details.senders_list
    content["To"] = smtp_server_details.receivers_list

    smtp_server.sendmail(smtp_server_details.senders_list, (smtp_server_details.receivers_list).split(','), content.as_string())
    logger.info("Execution sucessfull: send_email")

  except Exception as e:
    traceback.print_exc()
    logger.error("Received exception while running send_email", str(e), exc_info = True) 


  finally:
   return err_msg

#------------------------------------------------------------------------------
# Author: Nikhil Goenka
#------------------------------------------------------------------------------
def html_header(logger):
    try:
      logger.info("In html_header: ")
      html = """
      <html>
      <head>
      <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
      </head>
      <body bgcolor="#FFFFFF" leftmargin="0" topmargin="0" marginwidth="0" marginheight="0">
      <center>
      <img src="cid:image1" class = "center" width:90%>
      </center>
      <br></br>
      <p> Hi Team, </p>
      <p> The current DEM Units consumption <b>{total_consumption}</b> has breached <b>{percentage}</b> of the configured {threshold} threshold. Following are the details of DEM Units: </p>
      <br></br>
      <center>
      </style>
    """
    except Exception:
      traceback.print_exc()
      logger.error ("Received error while executing html_header %s", str(e))
    finally:
      return html

#------------------------------------------------------------------------------
# Author: Nikhil Goenka
#------------------------------------------------------------------------------
def html_footer(err_msg, logger, html, content, filename):
    try:
      logger.info("In html_footer : ")
      logger.debug("In html_footer %s: ", content)

      html = html + """ 
      <center>
      <p style="text-align:left;">Thanks, </p>
      <p style="text-align:left;">Dynatrace Team </p>
      <center>
      <img src="cid:image2">
      </center>
      </body>
      """

      content.attach(MIMEText(html, "html"))
      msgAlternative = MIMEMultipart('alternative')
      content.attach(msgAlternative)

      fp = open('images/Email_Template_01.jpg','rb')
      msgImage = MIMEImage(fp.read())
      fp.close()

      msgImage.add_header('Content-ID', '<image1>')
      content.attach(msgImage)

      fp = open('images/Email_Template_03.jpg','rb')
      msgImage = MIMEImage(fp.read())
      fp.close()

      msgImage.add_header('Content-ID', '<image2>')
      content.attach(msgImage)

      part = MIMEBase('application', "octet-stream")
      part.set_payload(open(filename, "rb").read())
      encoders.encode_base64(part)
      part.add_header('Content-Disposition', 'attachment; filename=%s"' % filename)
      content.attach(part)
     
    except Exception:
      traceback.print_exc()
      logger.error ("Received error while executing html_footer %s", str(e))
     
    finally:
      return err_msg, content

def create_csv(logger, err_msg, app_list, total_consumption, csv_data, filename, path):
  try:
     logger.info ("In create_csv")
     new_consumption = 0 

     #for key in csv_data.keys():
     #  print (key + " " + str(csv_data[key]))

     if not os.path.exists(path):
        os.makedirs(path)

     tmp_filename = path + "/total_consumption." + filename
     filename = path + "/" + filename 
     
     if not os.path.isfile(filename):
       fp = open(filename, "w")
       row_header = "Date"
       row_value = time.strftime("%H:%M:%S") 

       for key in csv_data.keys():
         row_header = row_header + "," + key 
         row_value = row_value + "," + str(csv_data[key])

       row_header = row_header + "\n"
       row_value = row_value + "\n"

       fp.write(row_header)
       fp.write(row_value)
       fp.close()

       #File to write total_consumption
       fp = open(tmp_filename, "w")
        
       fp.write (str(total_consumption))
       fp.close()

       new_consumption = total_consumption

     else:
       read_fp = open(filename, "r")
       lines = read_fp.readlines()
       read_fp.close()

       header = lines[0]
       header_val = header[:-1].split(",")

       write_fp = open(filename, "a")
       row_value = time.strftime("%H:%M:%S") 

       for headers in header_val:
         if headers == "Date":
           continue
         try: 
           row_value = row_value + "," + str(csv_data[headers])
         except KeyError:
           row_value = row_value + "," + str(0.0)
           
       row_value = row_value + "\n"
       write_fp.write(row_value)
       write_fp.close()
       
       fp = open(tmp_filename, "r")
       old_consumption = float(fp.readlines()[0])
       fp.close()   

       fp = open(tmp_filename, "w")
       new_consumption = float(old_consumption) + float(total_consumption)
       fp.write(str(new_consumption))  
       fp.close()   

  except Exception as e:
     traceback.print_exc()
     logger.error ("Received exception while running create_csv: "+ str(e))
     err_msg = "Received exception while running create_csv" + str(e)

  finally:
     return new_consumption, filename 

def getTableHTML(logger, err_msg, df):
  try:
    logger.info("In getTableHTML")

    # Defining the properties of the table
    styles = [
        dict(selector=" ", 
             props=[("margin","0.5em"),
                    ("font-family",'"Helvetica", "Arial", sans-serif'),
                    ("border-collapse", "collapse"),
                    ("border","none"),
                       ]),

         dict(selector="thead", 
              props=[("background-color","#fff"),
                     ("border","1px solid black")
                    ]),

        # Define the shading of the cells in table
        dict(selector="tbody tr:nth-child(even)",
             props=[("background-color", "#0099E6")]),
        dict(selector="tbody tr:nth-child(odd)",
             props=[("background-color", "#eee")]),

        dict(selector="td", 
             props=[("padding", ".5em"),
                    ("border","1px solid black")]),

        dict(selector="th", 
             props=[("font-size", "100%"),
                    ("text-align", "center"),
                    ("border","1px solid black")]),

    ]
    logger.info ("Completed the execution successfully of getTableHTML..")
 
  except Exception as e:
      logger.debug("Received an exception while executing getTableHTML ", str(e))
      traceback.print_exc()

  finally:
      return err_msg, (df.style.set_table_styles(styles)).render()

#------------------------------------------------------------------------------
# Author: Nikhil Goenka
# Function to make API call using the token defined in constant.py
# Returns the json object returned using the API call
#------------------------------------------------------------------------------
if __name__ == "__main__":
  try:
    filename = "config.json"
    data = parse_config(filename)

    logging.basicConfig(filename=data['log_file'],
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%Y-%m-%dT%H:%M:%S.000',
                            level=logging.DEBUG)
    logger = logging.getLogger()

    err_msg = ""
    email_body = ""
    smtp_server_details = email_details()
    smtp_server_details = populate_smtp_variable(data, logger, smtp_server_details)
    smtp_server = initialize_email_server(logger, smtp_server_details)
 
    content = MIMEMultipart('related')
    html = html_header(logger)

    tenant_info = tenantInfo()
    tenant_info = populate_tenant_details(logger, data['tenant-details'], tenant_info)

    #First fetch all the applications
    app_list = []
    consumption_list = {}

    #Now fetch all the synthetic applications 
    app_list,err_msg = fetch_application(logger, err_msg, tenant_info, app_list, FETCH_APPLICATIONS)
    total_consumption = 0

    #Now fetch all the synthetic applications
    app_list, err_msg = fetch_syn_application(logger, err_msg, app_list, tenant_info, FETCH_SYN_APPLICATIONS)

    app_list, consumption_list, err_msg = populate_sessions_details(logger, err_msg, app_list, tenant_info, consumption_list, APP_BILLING_API)
    app_list, consumption_list, err_msg = populate_sessions_details(logger, err_msg, app_list, tenant_info, consumption_list, APP_BILLING_API_REPLAY)
    app_list, consumption_list, err_msg = populate_sessions_details(logger, err_msg, app_list, tenant_info, consumption_list, SYN_BILLING_API, 1)
    app_list, consumption_list, err_msg = populate_sessions_details(logger, err_msg, app_list, tenant_info, consumption_list, HTTP_BILLING_API, 2)
  
    app_list, consumption_list, total_consumption, csv_data, err_msg = populate_dem_consumption (logger, err_msg, app_list, consumption_list, total_consumption) 
    #Setting the decimal points to only 2 (or else it was displaying upto 5 points)    
    pd.set_option('display.precision', 2)

    #Create csv file if does not exist
    filename = time.strftime("%Y%m%d") + ".csv"
    total_consumption, filename = create_csv(logger, err_msg, app_list, total_consumption, csv_data, filename, data['csv-file-path'])

    if float(total_consumption) > (float(tenant_info.threshold) * 0.80):
      content["Subject"] = "ALERT: DEM utilization has crossed 80%"
      
      reader = csv.DictReader(open(filename))
      df = pd.read_csv(filename)

      err_msg, table_html = getTableHTML(logger, err_msg, df)
      html = html.format(total_consumption=total_consumption,
                        percentage='80%',
                        threshold = tenant_info.threshold)
      html = html + table_html

      err_msg, content = html_footer(err_msg, logger, html, content, filename)
      err_msg = send_email(err_msg, logger, smtp_server, content, smtp_server_details)

    elif float(total_consumption) > (float(tenant_info.threshold) * 0.40):
      content["Subject"] = "WARNING: DEM utilization is now at 40% of the configured threshold"
      reader = csv.DictReader(open(filename))

      df = pd.read_csv(filename)
      err_msg, table_html = getTableHTML(logger, err_msg, df)
      html = html.format(total_consumption=total_consumption,
                        percentage='40%',
                        threshold = tenant_info.threshold)
      html = html + table_html

      err_msg, content = html_footer(err_msg, logger, html, content, filename)
      err_msg = send_email(err_msg, logger, smtp_server, content, smtp_server_details)
   
    logger.info("Successful execution: func")
    
  except Exception as e:
    traceback.print_exc()
    logger.debug("Encountered exception in main",e)
