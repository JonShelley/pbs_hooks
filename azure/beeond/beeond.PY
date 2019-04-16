import pbs

import subprocess
import json
import os
import copy
import traceback
from string import find
import sys
from os import path, mkdir, chmod, chown, sep
import pwd
#from shutil import rmtree

e = pbs.event()
j = e.job
pbs_conf = pbs.get_pbs_conf()
PBS_HOME = pbs_conf["PBS_HOME"]

if e.type == pbs.EXECJOB_BEGIN:
    pbs.logmsg(pbs.EVENT_DEBUG, "EXECJOB_BEGIN event")
elif e.type == pbs.EXECJOB_END:
    pbs.logmsg(pbs.EVENT_DEBUG, "EXECJOB_END event")


#
# FUNCTION caller_name
#
def caller_name():
    """
    Return the name of the calling function or method.
    """
    return str(sys._getframe(1).f_code.co_name)

def decode_list(data):
    """
    json hook to convert lists from unicode to utf-8
    """
    ret = []
    for item in data:
        if isinstance(item, unicode):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = decode_list(item)
        elif isinstance(item, dict):
            item = decode_dict(item)
        ret.append(item)
    return ret

def decode_dict(data):
    """
    json hook to convert dictionaries from unicode to utf-8
    """
    ret = {}
    for key, value in data.iteritems():
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        elif isinstance(value, list):
            value = decode_list(value)
        elif isinstance(value, dict):
            value = decode_dict(value)
        ret[key] = value
    return ret

def merge_dict(base, new):
    """
    Merge together two multilevel dictionaries where new
    takes precedence over base
    """
    if not isinstance(base, dict):
        raise ValueError('base must be type dict')
    if not isinstance(new, dict):
        raise ValueError('new must be type dict')
    newkeys = new.keys()
    merged = {}
    for key in base:
        if key in newkeys and isinstance(base[key], dict):
            # Take it off the list of keys to copy
            newkeys.remove(key)
            merged[key] = merge_dict(base[key], new[key])
        else:
            merged[key] = copy.deepcopy(base[key])
    # Copy the remaining unique keys from new
    for key in newkeys:
        merged[key] = copy.deepcopy(new[key])
    return merged

def read_cfg():
    # Set the default values
    defaults = {}
    defaults["start_cmd"] = "beeond start"
    defaults["stop_cmd"] = "-L -d"
    defaults["stop_options"] = "beeond stop"
    defaults["mnt_pnt"] = "/beeond"
    defaults["disk_loc"] = "/mnt/resource/beeond"
    defaults["disk_type"] = "ssd"
    defaults["ssd_disk_loc"] = "/mnt/resource/beeond"
    defaults["ram_disk_loc"] = "/mnt/pbs_ramdisk"

    # Identify the config file and read in the data
    config_file = ''
    if 'PBS_HOOK_CONFIG_FILE' in os.environ:
        config_file = os.environ["PBS_HOOK_CONFIG_FILE"]
    if not config_file:
        tmpcfg = os.path.join(PBS_HOME, 'mom_priv', 'hooks',
                              'beeond.CF')
    try:
        with open(config_file, 'r') as desc:
            config = merge_dict(defaults, json.load(desc, object_hook=decode_dict))
    except:
        raise
    pbs.logmsg(pbs.EVENT_DEBUG3, "Hook configuration: %s" % config)
    return config

def make_nfile(exec_host, nfilename):
    nodes = exec_host
    nodes = nodes.split('+')
    node_file = list()
    for node in nodes:
        node_file.append(node.split(":")[0])
    pbs.logmsg(pbs.EVENT_DEBUG, "Nodes: %s" % node_file)
    pbs.logmsg(pbs.EVENT_DEBUG, "Node file path: %s" % nfilename)
    outf = open(nfilename, "w")
    for n in node_file:
        outf.write("%s\n" % n)
    outf.close()

def run_cmd(cmd):
    # Get job substate based on printjob output
    try:
        pbs.logmsg(pbs.EVENT_DEBUG4, "cmd: %s" % cmd)
        # Collect the job substate information
        process = subprocess.Popen(cmd, shell=False,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        out, err = process.communicate()
        pbs.logmsg(pbs.EVENT_DEBUG, "%s: Output: %s" % (caller_name(), out))
        pbs.logmsg(pbs.EVENT_DEBUG, "%s: Error: %s" % (caller_name(), err))
        pbs.logmsg(pbs.EVENT_DEBUG, "%s: Return Code: %s" % (caller_name(), process.returncode))
        return(True)
    except Exception as exc:
        pbs.logmsg(pbs.EVENT_DEBUG, "%s: Unexpected error: %s" %
                   (caller_name(), exc))
        return(False)

mom = pbs.get_local_nodename().lower()
mom = mom.split(".")[0]
pbs.logmsg(pbs.EVENT_DEBUG, "Mom: %s" % mom)
try:
    if e.job.in_ms_mom():
        # See if the job requests beeond
        # [Rework] Look for ENV that requests beeond or do it at the chunk level
        if "place" in j.Resource_List:
            results = str(j.Resource_List["place"]).find("excl")
            pbs.logmsg(pbs.EVENT_DEBUG, "Results: %s" % (results))
            if str(j.Resource_List["place"]).find("excl") == -1:
                pbs.logmsg(pbs.EVENT_DEBUG, "Not an exclusive job: %s" % (j.Resource_List["place"]))
                e.accept()
            else:
                # Check to see if PBS_JOB_FS=BEEOND is in the job environment
                env = j.Variable_List
                env = env.split(",")
                env_vars = {}
                for item in env:
                    tmp = item.split("=")
                    env_vars[tmp[0]] = tmp[1]
                pbs.logmsg(pbs.EVENT_DEBUG, "Environment Variables: %s" % (env_vars))

        # Read in the config file
        cfg = read_cfg()
        node_filename = PBS_HOME+os.sep+"aux/%s.beeond" % j.id
        node_filename = "/tmp/%s.beeond" % j.id
        make_nfile(j.exec_host2, node_filename)

        # Determine the disk type
        disk_type = cfg["disk_type"]
        pbs.logmsg(pbs.EVENT_ERROR, "disk_type: %s" % disk_type)
        pbs.logmsg(pbs.EVENT_ERROR, "type: %s" % type(disk_type))
        if str(disk_type.lower()) == "ssd": 
            disk_loc = cfg["ssd_disk_loc"]
        elif str(disk_type.lower()) == "ram":
            disk_loc = cfg["ram_disk_loc"]
        else:
            pbs.logmsg(pbs.EVENT_ERROR, "Unknown disk_type: %s" % disk_type)
            pbs.event().reject("Fix disk_type in the setup_beeond config file")

        # Start/stop beeond only on rank 0 node
        try:
            if e.type == pbs.EXECJOB_BEGIN:
                # Start beeond
                start_cmd = cfg["start_cmd"].split()
                start_cmd += ["-n", node_filename]
                if disk_type.lower() == "ram":
                    start_cmd += ["-r"]
                start_cmd += ["-d", disk_loc]
                start_cmd += ["-c", cfg["mnt_pnt"]]
                start_cmd += ["-f", cfg["cfg_path"]]

                pbs.logmsg(pbs.EVENT_DEBUG, "Start cmd: %s" % start_cmd)
                run_cmd(start_cmd)
                run_cmd('/usr/bin/date')
                #e.accept()
            elif e.type == pbs.EXECJOB_END:
                # Make sure to clean up the disk
                stop_cmd = cfg["stop_cmd"].split()
                stop_cmd += ["-n", node_filename]
                stop_cmd +=  cfg["stop_args"].split()
                pbs.logmsg(pbs.EVENT_DEBUG, "Stop cmd: %s" % stop_cmd)
                run_cmd(stop_cmd)
                # Remove beeond node file
                os.remove(node_filename)
            else:
                pbs.logmsg(pbs.EVENT_DEBUG, "No action defined for event: %s" % e.type )

        except:
            pbs.logmsg(pbs.EVENT_DEBUG, str(traceback.format_exc().strip().splitlines()))

except:
    pbs.logmsg(pbs.EVENT_DEBUG, str(traceback.format_exc().strip().splitlines()))
