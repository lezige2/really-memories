import os, sys, paramiko

host = os.environ.get("A10_HOST", "115.29.142.94")
port = int(os.environ.get("A10_PORT", "6137"))
user = os.environ.get("A10_USER", "root")
pw = os.environ["A10_PW"]
local, remote = sys.argv[1], sys.argv[2]

t = paramiko.Transport((host, port))
t.connect(username=user, password=pw)
sftp = paramiko.SFTPClient.from_transport(t)
sftp.put(local, remote)
print("uploaded", local, "->", remote)
sftp.close()
t.close()