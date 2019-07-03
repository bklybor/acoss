import subprocess
from sys import argv
import time

# 11325 batches
start = int(argv[1])
end = int(argv[2])
tic = time.time()
for i in range(start, end):
    subprocess.call(["python", "ChenFusion.py", "-s", "benchmarking", "-d", "../features_benchmark", "-i", "%i"%i])
    t = time.time()-tic
    print("Total Elapsed Time: %.3g"%(t))
    print("Avg time per iteration: %.3g"%(t/(i-start+1)))

# Do CREMA back to back
for i in range(start, end):
    subprocess.call(["python", "ChenFusion.py", "-c", "crema", "-s", "crema_benchmarking", "-d", "../crema_benchmark", "-i", "%i"%i])
    t = time.time()-tic
    print("Total Elapsed Time: %.3g"%(t))
    print("Avg time per iteration: %.3g"%(t/(i-start+1)))