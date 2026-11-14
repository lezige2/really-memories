import os, sys, paramiko

host = os.environ.get("A10_HOST", "115.29.142.94")
port = int(os.environ.get("A10_PORT", "6137"))
user = os.environ.get("A10_USER", "root")
pw = os.environ["A10_PW"]
cmd = sys.argv[1]
timeout = float(os.environ.get("A10_TIMEOUT", "90"))

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, port=port, username=user, password=pw, timeout=20,
          allow_agent=False, look_for_keys=False)
stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
out = stdout.read().decode("utf-8", "replace")
err = stderr.read().decode("utf-8", "replace")
sys.stdout.write(out)
if err.strip():
    sys.stdout.write("\n[STDERR]\n" + err)
rc = stdout.channel.recv_exit_status()
c.close()
sys.exit(rc)