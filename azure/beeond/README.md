# PBS hook for beeOND integration
Notes:
To run this hook you will need to do the following
- install BeeOND on the compute nodes
- enable passwordless ssh for root on the compute nodes. 
- enable pdsh on your cluster (optional for faster setup time on BeeOND. Not yet tested)
 - modify the hook to include the pdsh start option for the beeond script ( this will reduce startup time of BeeOND).o
- Modify the BeeGFS configuration files and make them available to the compute nodes ( Only if you want something other then the default BeeGFS configuration).

Files:
- beeond.json: Configurations file
- beeond.py: Hook File

Create the hook and configure it in PBS
```shell
/opt/pbs/bin/qmgr -c 'c h beeond'
/opt/pbs/bin/qmgr -c 's h beeond event="execjob_begin,execjob_end"'
/opt/pbs/bin/qmgr -c 's h beeond alarm=300'
/opt/pbs/bin/qmgr -c 'i h beeond application/x-config default beeond.json'
/opt/pbs/bin/qmgr -c 'i h beeond application/x-python default beeond.PY'
```

Configuration options:
<Need to be added>

Usage:
Currently to get a beeond file system the job must request place=excl. If this is the case, the hook will create a beeond file system. This will be modified in the future (suggestions welcome for how you would like to see this done)

