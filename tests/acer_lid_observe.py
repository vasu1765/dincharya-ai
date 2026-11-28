"""Attended, AC-only observation. Uses one disposable heartbeat, with no database or messages."""
import argparse
import json
import re
import secrets
import subprocess
import time

DAEMON = "44c1ef83-c50e-4ecc-8f19-4b112bc40f29"
IMAGE = "sha256:fff0b1b58321339ad0de04804548cb8ff14c9a929e6eead08ce3cd96535493ca"
HEARTBEAT = """import json,sys,time
for n in range(int(sys.argv[1])):
    print(json.dumps([n,time.time()]),flush=True)
    if n+1<int(sys.argv[1]):time.sleep(1)
"""


def call(*args, timeout=12):
    return subprocess.run(args, text=True, capture_output=True, timeout=timeout, check=True).stdout.strip()


def power():
    return call("powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                "Add-Type -AssemblyName System.Windows.Forms; "
                "[System.Windows.Forms.SystemInformation]::PowerStatus.PowerLineStatus") == "Online"


def events(start):
    command = (
        f"$d=[DateTimeOffset]::FromUnixTimeSeconds({start}).LocalDateTime;"
        "$filter=@{LogName='System';ProviderName='Microsoft-Windows-Kernel-Power';Id=42,105;StartTime=$d};"
        """$rows=@(Get-WinEvent -FilterHashtable $filter -ErrorVariable violations -ErrorAction SilentlyContinue);
        if (@($violations | Where-Object {$_.FullyQualifiedErrorId -notlike 'NoMatchingEventsFound*'}).Count) {
            throw 'power event log unavailable'
        }
        $sleep=@($rows | Where-Object {$_.Id -eq 42}).Count;
        $dc=@($rows | Where-Object {
            if ($_.Id -eq 105) {
              $ac=([xml]$_.ToXml()).Event.EventData.Data | Where-Object {$_.Name -eq 'AcOnline'};
              if (!$ac) { throw 'power source transition could not be classified' };
              $ac.InnerText -match '^(false|0)$'
            }
        }).Count;
        Write-Output ($sleep.ToString()+':'+$dc.ToString())
        """
    )
    result = call("powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command)
    if not re.fullmatch(r"\d+:\d+", result):
        raise RuntimeError("invalid power log result")
    return tuple(map(int,result.split(":")))


def observe():
    if call("docker","info","--format","{{.ID}}")!=DAEMON:
        raise RuntimeError("daemon mismatch")
    if call("docker","image","inspect","--format","{{.Id}}",IMAGE)!=IMAGE:
        raise RuntimeError("image mismatch")
    policy = call("powershell.exe","-NoProfile","-NonInteractive","-Command",
                  "powercfg /qh SCHEME_CURRENT SUB_BUTTONS")
    match = re.search(r"5ca83367-6e45-459f-a27b-476b1d01c936\b(?:(?!Power Setting GUID:)[\s\S])*?"
                      r"Current AC Power Setting Index:\s*0x([0-9a-f]+)",policy,re.I)
    if not match or int(match[1],16)!=0 or not power():
        raise RuntimeError("active AC lid policy not ready")
    name="dincharya-lid-"+secrets.token_hex(10)
    label="org.dincharya.ac-lid-check"
    start=int(time.time())
    child=subprocess.Popen(["docker","run","--rm","--name",name,"--label",label+"="+name,
                            "--network","none","--pull","never","--read-only","--cap-drop","ALL",
                            "--security-opt","no-new-privileges","--entrypoint","python",IMAGE,
                            "-u","-B","-c",HEARTBEAT,"91"],stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,text=True)
    time.sleep(3)
    print("Keep the charger connected. Close after the observation starts, reopen after 60 seconds, then wait for the result.",flush=True)
    try:
        out,_=child.communicate(timeout=145)
    finally:
        if child.poll() is None:
            if call("docker","inspect","-f",'{{index .Config.Labels "'+label+'"}}',name)==name:
                call("docker","stop","-t","2",name,timeout=15)
            child.communicate(timeout=10)
    rows=[json.loads(line) for line in out.splitlines()]
    if child.returncode!=0 or [row[0] for row in rows]!=list(range(91)):
        raise RuntimeError("heartbeat did not complete")
    gaps=[b[1]-a[1] for a,b in zip(rows,rows[1:])]
    sleeps,dc=events(start)
    print(f"heartbeat samples={len(rows)} maximum_gap_s={max(gaps):.2f} sleep_events={sleeps} battery_events={dc}")
    if any(gap<=0 or gap>3.5 for gap in gaps) or sleeps or dc or not power():
        raise RuntimeError("physical observation did not meet safety criteria")
    print("PASS attended AC-only heartbeat and no sleep or battery transition")


if __name__=="__main__":
    args=argparse.ArgumentParser(description=__doc__)
    args.add_argument("--owner-attending",action="store_true",required=True)
    args.parse_args()
    try:
        observe()
    except (ValueError,RuntimeError,subprocess.SubprocessError) as error:
        print("FAIL physical observation",type(error).__name__)
        raise SystemExit(1)
