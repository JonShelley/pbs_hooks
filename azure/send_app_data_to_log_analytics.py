#!/usr/bin/env python2.7

import pbs
import json
import datetime
import hashlib
import hmac
import base64
import traceback
import sys
import os
import subprocess

# Add standard python module path
sys.path.append('/lib/python2.7/site-packages')

import requests

def debug(msg):
    pbs.logmsg(pbs.EVENT_DEBUG3, 'LA debug: %s' % msg)


def error(msg):
    pbs.logmsg(pbs.EVENT_ERROR, 'LA error: %s' % msg)


def run_cmd(cmd):
    debug("Cmd: %s" % cmd)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        debug('cmd failed!\n\tstdout="%s"\n\tstderr="%s"' % (stdout, stderr))
    return stdout, stderr


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
    debug("Entering build_signature")
    x_headers = 'x-ms-date:' + date
    string_to_hash = method + "\n" + str(content_length) + "\n" + content_type + "\n" + x_headers + "\n" + resource
    bytes_to_hash = bytes(string_to_hash).encode('utf-8')  
    decoded_key = base64.b64decode(shared_key)
    encoded_hash = base64.b64encode(hmac.new(decoded_key, bytes_to_hash, digestmod=hashlib.sha256).digest())
    authorization = "SharedKey {}:{}".format(customer_id,encoded_hash)
    return authorization

# Build and send a request to the POST API
def post_data(customer_id, shared_key, body, log_type):
    debug("Entering post_data")
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
    
    debug("Body: %s" % body)
    debug("Body type: %s" % type(body))
    response = requests.post(uri,data=body, headers=headers)
    if (response.status_code >= 200 and response.status_code <= 299):
        debug('Accepted')
    else:
        debug("Rejected - Response code: {}".format(response.status_code))

# Read in the config file
cfg = parse_config_file()

# Update the customer ID to your Log Analytics workspace ID
customer_id = cfg["customer_id"]

# For the shared key, use either the primary or the secondary Connected Sources client authentication key   
shared_key = cfg["shared_key"]

# Read in the job env
e = pbs.event()
j = e.job

# Read the filename to upload from the environment
try:
    if not j.in_ms_mom():
        debug("Not on the ms node")
        e.accept()
    if "PBS_AZURE_LA_JSON_FILE_DIR" in j.Variable_List and "PBS_AZURE_LA_LOG_TYPE" in j.Variable_List:
        debug("Proceed to add data to log analytics")
        log_type = j.Variable_List["PBS_AZURE_LA_LOG_TYPE"]
        debug("Log type: %s" % log_type)
        data_file_dir = j.Variable_List["PBS_AZURE_LA_JSON_FILE_DIR"]
        data_filename = data_file_dir + os.sep + j.id + ".json"
        debug("Data filename: %s" % data_filename)
        # Get VM Instance
        cmd = [ "curl", "-s", "-H", "Metadata:true", "http://169.254.169.254/metadata/instance?api-version=2017-12-01"]
        stdout, stderr = run_cmd(cmd)
        json_vm = json.loads(stdout)
        vm_size=json_vm["compute"]["vmSize"]
        debug("json_vm vm_inst: %s" % vm_size)
        
        if os.path.isfile(data_filename):
            with open(data_filename) as data_fp:
                json_data = json.load(data_fp)
                json_data["vmSize"] = vm_size
                json_str = json.dumps(json_data)
                debug("data file contents: %s" % json_str)
                post_data(customer_id, shared_key, json_str, log_type)
                debug("Completed sending data to log anaylitics")
        else:
            debug("Data file: %s was not found" % data_filename)
except SystemExit:
    debug("Exited with SystemExit")  
except:
    debug("Failed to post data to log analytics")
    error(traceback.format_exc())
    raise
