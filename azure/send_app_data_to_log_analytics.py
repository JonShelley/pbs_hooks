#!/usr/bin/env python2.7

#import pbs
import json
import requests
import datetime
import hashlib
import hmac
import base64
import traceback

def debug(msg):
    pbs.logmsg(pbs.EVENT_DEBUG3, 'debug: %s' % msg)


def error(msg):
    pbs.logmsg(pbs.EVENT_ERROR, 'error: %s' % msg)


def parse_config_file():
        """
        Read the config file in json format
        """
        debug('Parse config filed')

        # Identify the config file and read in the data
        config_file = ''
        if 'PBS_HOOK_CONFIG_FILE' in os.environ:
            config_file = os.environ['PBS_HOOK_CONFIG_FILE']
        if not config_file:
            error('Config file not found')
        msg = 'Config file is %s' % config_file
        debug(msg)
        try:
            with open(config_file, 'r') as desc:
                config = json.load(desc)
        except IOError:
            error('I/O error reading config file')
        debug('cgroup hook configuration: %s' % config)
        return config


# Build the API signature
def build_signature(customer_id, shared_key, date, content_length, method, content_type, resource):
    x_headers = 'x-ms-date:' + date
    string_to_hash = method + "\n" + str(content_length) + "\n" + content_type + "\n" + x_headers + "\n" + resource
    bytes_to_hash = bytes(string_to_hash).encode('utf-8')  
    decoded_key = base64.b64decode(shared_key)
    encoded_hash = base64.b64encode(hmac.new(decoded_key, bytes_to_hash, digestmod=hashlib.sha256).digest())
    authorization = "SharedKey {}:{}".format(customer_id,encoded_hash)
    return authorization

# Build and send a request to the POST API
def post_data(customer_id, shared_key, body, log_type):
    method = 'POST'
    content_type = 'application/json'
    resource = '/api/logs'
    rfc1123date = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    content_length = len(body)
    signature = build_signature(customer_id, shared_key, rfc1123date, content_length, method, content_type, resource)
    uri = 'https://' + customer_id + '.ods.opinsights.azure.com' + resource + '?api-version=2016-04-01'

    headers = {
        'content-type': content_type,
        'Authorization': signature,
        'Log-Type': log_type,
        'x-ms-date': rfc1123date
    }

    response = requests.post(uri,data=body, headers=headers)
    if (response.status_code >= 200 and response.status_code <= 299):
        print 'Accepted'
    else:
        print "Response code: {}".format(response.status_code)

# Read in the config file
cfg = parse_config_file()

# Update the customer ID to your Log Analytics workspace ID
customer_id = cfg["customer_id"]

# For the shared key, use either the primary or the secondary Connected Sources client authentication key   
shared_key = cfg["shared_key"]

# Read in the job env
e = pbs.event()
j = e.job

# Read log_type from the environment
if "PBS_AZURE_LA_LOG_TYPE" in j.Variable_List:
    log_type = j.Variable_List["PBS_AZURE_LA_LOG_TYPE"]

# Read the filename to upload from the environment
if "PBS_AZURE_LA_DATA_FILE" in j.Variable_List:
    data_file = j.Variable_List["PBS_AZURE_LA_DATA_FILE"]
    if os.path.isfile(data_file):
        try:
            with open(data_file) as datafile:
                json_data = json.load(datafile)
                debug("data file contents: %s" % json_data)
                post_data(customer_id, shared_key, json_data, log_type)
                debug("Completed sending data to log anaylitics")
        except SystemExit:
            debug("Exited with SystemExit")  
        except:
            debug("Failed to post data to log analytics")
            error(traceback.format_exc())
            raise
    else:
        debug("Data file: %s was not found" % data_file)
