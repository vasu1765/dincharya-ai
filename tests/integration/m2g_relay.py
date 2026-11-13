"""Opaque byte/HTTP test relays. Application uses real psycopg/httpx, not psql."""
import json
import os
from pathlib import Path
import socket
import subprocess
import threading


class UnixTCPRelay:
    def __init__(self,path,docker,compose,environment,host,port):
        self.path=str(path);self.running=True;self.sockets=[];self.children=[]
        self.server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.server.bind(self.path);os.chmod(self.path,0o600);self.server.listen()
        def serve():
            while self.running:
                try:client,_=self.server.accept()
                except OSError:break
                if not self.running:client.close();break
                self.sockets.append(client)
                script="const net=require('node:net');const s=net.connect("+str(int(port))+","+json.dumps(host)+");s.on('connect',()=>{process.stdin.pipe(s);s.pipe(process.stdout);});s.on('error',()=>process.exit(1));"
                child=subprocess.Popen(docker+compose+['exec','-T','mock-services','node','-e',script],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=environment,bufsize=0)
                self.children.append(child)
                def upstream(c=client,p=child):
                    try:
                        while chunk:=c.recv(65536):p.stdin.write(chunk)
                    except (OSError,ValueError):pass
                    finally:
                        try:p.stdin.close()
                        except (OSError,ValueError):pass
                def downstream(c=client,p=child):
                    try:
                        while chunk:=os.read(p.stdout.fileno(),65536):c.sendall(chunk)
                    except (OSError,ValueError):pass
                    finally:c.close()
                threading.Thread(target=upstream,daemon=True).start();threading.Thread(target=downstream,daemon=True).start()
        self.thread=threading.Thread(target=serve,daemon=True);self.thread.start()
    def close(self):
        self.running=False
        try:
            wake=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);wake.connect(self.path);wake.close()
        except OSError:pass
        self.server.close();self.thread.join(timeout=2)
        for client in self.sockets:
            try:client.shutdown(socket.SHUT_RDWR);client.close()
            except OSError:pass
        for child in self.children:
            try:child.wait(timeout=2)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=2)
        Path(self.path).unlink(missing_ok=True)
