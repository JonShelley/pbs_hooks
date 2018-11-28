#!/bin/bash
/opt/pbs/bin/qmgr -c "create hook chk_ib"
/opt/pbs/bin/qmgr -c "set hook chk_ib event=exechost_startup"
/opt/pbs/bin/qmgr -c "import hook chk_ib application/x-python default chk_ib.py"
/opt/pbs/bin/qmgr -c "create hook setup_jobdir"
/opt/pbs/bin/qmgr -c "set hook setup_jobdir event=\"execjob_begin,execjob_end\""
/opt/pbs/bin/qmgr -c "import hook setup_jobdir application/x-python default setup_jobdir.py"