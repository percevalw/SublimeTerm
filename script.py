
import subprocess, os, time, signal, sys

if __name__ == "__main__":
    print("**** Started ****")
    pid = os.fork()
    current_env = os.environ
    print("ENV", current_env)
    if pid == 0:
        process = subprocess.Popen("/bin/bash",
                                   stdin = subprocess.PIPE,
                                   stdout = subprocess.PIPE,
                                   stderr = subprocess.PIPE,
                                   env = current_env)
        count = 50
        while True:
            count -= 1
            #if os.path.exists("/proc/"+str(process.pid)):
            time.sleep(0.1)
#            print(os.getenv("BASHPID"))
            print("PID FROM CHILD", process.pid)
            if count <= 0:
                os.kill(pid, signal.SIGTERM)
                break
        sys.stdin.write("pwd\n")
    else:
        print("PID FROM PARENT", pid)
        count = 50
        while True:
            count -= 1
            #if os.path.exists("/proc/"+str(process.pid)):
            time.sleep(0.1)
#            print(os.getenv("BASHPID"))
            if count <= 0:
                os.kill(pid, signal.SIGTERM)
                break
#            else:
        print("**** Ended ****")
