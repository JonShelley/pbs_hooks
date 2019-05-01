# Azure

## Check IB
Purpose:
- To check if the IB on the HPC compute nodes (H/HB/HC) are showing as up

### Required files
- chk_ib.py: Hook to check if eth1 is up IB enabled H16r(m) or NV24r nodes

### Setup Hook
qmgr commands
```
/opt/pbs/bin/qmgr -c "create hook chk_ib"
/opt/pbs/bin/qmgr -c "set hook chk_ib event=exechost_startup"
/opt/pbs/bin/qmgr -c "import hook chk_ib application/x-python default chk_ib.py"
```

## Setup jobdir
Purpose:
- To create a job dir on the local SSD that the user can use on each node assigned to the job

### Required files
- setup_jobdir.py

### Setup Hook
qmgr commands
```
create hook setup_jobdir
set hook setup_jobdir event="execjob_begin,execjob_end"
import hook setup_jobdir application/x-python default setup_jobdir.py
```

## Manage WAAgent
Purpose:
- To reduce jitter on the compute nodes when jobs are running

### Required files
- stop_waagent.py

### Setup Hook
qmgr commands
```
create hook stop_wa
set hook stop_wa event="execjob_begin,execjob_end"
import hook stop_wa application/x-python default stop_waagent.py
```

## Send application data to log analytics:
Purpose: 
- upload job metadata stored in a json file to Azure log analytics for later processing

### Additional system setup requirements
- yum install -y python-requests

### Required files
- send_app_data_to_log_analytics.py 
- send_app_data_to_log_analytics.json

### Setup Hook
update send_app_data_to_log_analytics.json (config file) with the appropriate values for your subscription
```
{
    "customer_id": "xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "shared_key":  "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```
qmgr commands
```
create hook azure_la
set hook azure_la event=execjob_epilogue
import hook azure_la application/x-config default send_app_data_to_log_analytics.json
import hook azure_la application/x-python default send_app_data_to_log_analytics.py
```

