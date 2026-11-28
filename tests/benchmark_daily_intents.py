"""Synthetic only. Start an isolated Windows Ollama listener and clean up its own process."""
import base64, json, subprocess, sys, time
from threading import Event, Thread
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intent_benchmark_cases import CASES, request as fixture_request, score

models={"qwen2.5:3b":"357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b",
        "qwen2.5:7b-instruct-q4_K_M":"845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e",
        "qwen3:4b":"359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7"}
BASE="http://127.0.0.1:11439"
MIN_FREE_MIB=3072
STOP_FREE_MIB=1536
common="$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.UTF8Encoding]::new(); "

def run(code,timeout=30):
    q=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-EncodedCommand",
          base64.b64encode((common+code).encode("utf-16-le")).decode()],
          capture_output=True,timeout=timeout)
    if q.returncode:
        raise RuntimeError("Windows benchmark command failed")
    return q.stdout.decode("utf-8-sig").strip().replace("\r","")

def arg(value):
    return "'"+value.replace("'","''")+"'"

def request(path,data,timeout):
    raw=base64.b64encode(json.dumps(data,ensure_ascii=False).encode()).decode()
    return json.loads(run(f"$j=[Convert]::FromBase64String('{raw}'); "
        f"$r=Invoke-RestMethod -Method Post -Uri '{BASE}{path}' -TimeoutSec {timeout} -ContentType 'application/json' -Body $j;"
        "$r|ConvertTo-Json -Depth 18 -Compress",timeout+20))

def stats():
    s=run("$gpu=(& nvidia-smi.exe --query-gpu=memory.used,memory.total --format=csv,noheader,nounits | Select-Object -First 1); "
        "$free=(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory; @($gpu,$free)|ConvertTo-Json -Compress")
    gpu,ram=json.loads(s)
    return int(gpu.split(",")[0]),round(int(ram)/1024)

def get(path):
    return json.loads(run(f"Invoke-RestMethod -Uri '{BASE}{path}' -TimeoutSec 5 | ConvertTo-Json -Depth 18 -Compress"))

def benchmark(model):
    if stats()[1]<MIN_FREE_MIB:
        raise RuntimeError("insufficient starting RAM headroom")
    print("BENCH pull",model,flush=True)
    tag=get("/api/tags")["models"]
    if not any(x["name"]==model for x in tag):
        pulled=request("/api/pull",dict(model=model,stream=False),880)
        assert pulled.get("status")=="success"
    found=[x for x in get("/api/tags")["models"] if x["name"]==model]
    assert len(found)==1 and found[0]["digest"]==models[model]
    if stats()[1]<MIN_FREE_MIB:
        raise RuntimeError("insufficient pre-load RAM headroom")
    profiles=("original","compact")
    results={name:dict(cases=0, outcomes={}, warm_ms=[], input_tokens=[], output_tokens=[])
             for name in profiles}
    ticks=[]
    baseline=stats()
    peak_vram, minimum_ram=baseline
    completed=True
    cold_ms=load_ms=None
    for index,(case,text,context,expected) in enumerate(CASES):
        for profile in (profiles if index%2==0 else profiles[::-1]):
            if stats()[1]<STOP_FREE_MIB:
                completed=False
                break
            row=results[profile]
            try:
                with TickProbe(ticks):
                    result=request("/api/chat",fixture_request(profile,model,text,context),45)
                ms=round(result["total_duration"]/1e6)
                if cold_ms is None:
                    cold_ms,load_ms=ms,round(result["load_duration"]/1e6)
                else:
                    row["warm_ms"].append(ms)
                row["input_tokens"].append(result.get("prompt_eval_count"))
                row["output_tokens"].append(result.get("eval_count"))
                outcome=score(profile,result["message"]["content"],expected)
            except Exception:
                outcome="transport"
            row["cases"]+=1
            row["outcomes"][outcome]=row["outcomes"].get(outcome,0)+1
            if outcome!="pass":
                print("BENCH mismatch",model,profile,case,outcome,flush=True)
            gpu,ram=stats()
            peak_vram=max(peak_vram,gpu)
            minimum_ram=min(minimum_ram,ram)
            if ram<STOP_FREE_MIB:
                completed=False
                break
        if not completed:
            break
    entry=next((x for x in get("/api/ps")["models"] if x.get("name")==model),{})
    print("BENCH RESULT "+json.dumps(dict(model=model,complete=completed,cold_ms=cold_ms,load_ms=load_ms,
          profiles=results,baseline_gpu_mib=baseline[0],sampled_gpu_peak_mib=peak_vram,
          baseline_free_ram_mib=baseline[1],sampled_free_ram_low_mib=minimum_ram,
          synthetic_tick_max_ms=round(max(ticks,default=0)),vram_model_bytes=entry.get("size_vram"),
          model_total_bytes=entry.get("size"),context=entry.get("context_length"))),flush=True)
    request("/api/generate",dict(model=model,prompt="",keep_alive=0,stream=False),45)
    if not completed:
        print("BENCH stopped below working RAM reserve",flush=True)

class TickProbe:
    """Observe scheduling jitter of the real worker function with stubbed ports, never the live DB."""
    def __init__(self, results):
        self.stop=Event()
        self.results=results

    def tick(self):
        from datetime import datetime, timezone
        from unittest.mock import Mock
        from dincharya.personal_service import deliver_due
        actor,bot=101,102
        worker=Mock()
        worker.execute.side_effect=lambda query, params=None: Mock(
            fetchone=Mock(return_value=(1,1,actor,"Synthetic",datetime.now(timezone.utc))
                          if "claim" in query else (True,)))
        def transport(method,body):
            return {"ok":True,"result":{"message_id":1,"from":{"is_bot":True,"id":bot},
                    "chat":{"id":actor,"type":"private"},"text":body["text"]}}
        due=time.monotonic()
        while not self.stop.is_set():
            started=time.monotonic()
            deliver_due(worker,transport,actor,bot)
            self.results.append((time.monotonic()-due)*1000)
            due=started+.25
            self.stop.wait(max(0,due-time.monotonic()))
            worker.reset_mock()

    def __enter__(self):
        self.thread=Thread(target=self.tick,daemon=True)
        self.thread.start()
        return self

    def __exit__(self,*exc):
        self.stop.set()
        self.thread.join(timeout=1)


def main():
    if stats()[1]<MIN_FREE_MIB:
        raise RuntimeError("need more than 3 GiB available Acer RAM")
    started=run("""if (Get-NetTCPConnection -LocalPort 11439 -ErrorAction SilentlyContinue) { throw 'port in use' }
$exe=Join-Path $env:LOCALAPPDATA "Programs\\Ollama\\ollama.exe"
$id=[Guid]::NewGuid().ToString('N')
$directory=Join-Path $env:TEMP ("dincharya-model-bench-"+$id)
New-Item -ItemType Directory -Path $directory|Out-Null
$env:OLLAMA_MODELS=$directory
$env:OLLAMA_HOST='127.0.0.1:11439'
$env:OLLAMA_CONTEXT_LENGTH='2048'
$env:OLLAMA_NUM_PARALLEL='1'
$env:OLLAMA_MAX_LOADED_MODELS='1'
$env:OLLAMA_NO_CLOUD='1'
$p=Start-Process -FilePath $exe -ArgumentList 'serve' -WindowStyle Hidden -PassThru
@($p.Id,$directory)|ConvertTo-Json -Compress""")
    pid,folder=json.loads(started)
    try:
        for _ in range(20):
            try:
                if get("/api/version").get("version"):break
            except RuntimeError:time.sleep(1)
        else: raise RuntimeError("isolated endpoint did not start")
        address=json.loads(run(f"$x=Get-NetTCPConnection -State Listen -LocalPort 11439; "
           f"if ($x.OwningProcess -ne {pid}) {{ throw 'owner mismatch' }}; $x.LocalAddress|ConvertTo-Json -Compress"))
        assert address=="127.0.0.1"
        for model in models:
            benchmark(model)
    finally:
        run(f"$proc=Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
            f"if ($proc) {{ $x=Get-NetTCPConnection -State Listen -LocalPort 11439 -ErrorAction SilentlyContinue; "
            f"if ($x -and $x.OwningProcess -ne {pid}) {{ throw 'owner mismatch' }}; "
            f"if ($proc.ProcessName -ne 'ollama') {{ throw 'process mismatch' }}; Stop-Process -Id {pid} }}; "
            f"$p={arg(folder)}; if ((Split-Path $p -Leaf) -match '^dincharya-model-bench-[a-f0-9]{{32}}$' -and "
            "(Split-Path $p -Parent) -eq $env:TEMP -and (Test-Path -LiteralPath $p)) { Remove-Item -LiteralPath $p -Recurse -Force }")
        print("BENCH isolated listener stopped and scratch removed",flush=True)

if __name__=="__main__":
    try:main()
    except (Exception,KeyboardInterrupt) as e:
        print("BENCH STOP "+type(e).__name__,file=sys.stderr)
        sys.exit(1)
