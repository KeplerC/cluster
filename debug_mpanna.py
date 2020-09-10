import time
import struct
import logging
from cloudburst.client.client import CloudburstConnection
# change this every time the cluster restarts
routing_elb = 'aee12d8103fb64019a1c9f26d44f18c9-776076244.us-west-2.elb.amazonaws.com'
driver_node_ip = '3.16.55.37'
function_elb = 'add5f07f9256d4121a87a81722e2cdd5-321829147.us-west-2.elb.amazonaws.com'

dc = CloudburstConnection(function_elb, driver_node_ip) # function_elb, driver_node_ip

time_limit = 30
total_runs  = 80

#PATH_RVF = 0xb11b0c45
#PATH_RVD = PATH_RVF + 0x100


def deserializePath(buf):
    headerSize = 4+4+8+4
    wpSize = 8*8


    tp, size, cost, solveTimeMillis = struct.unpack_from('>LLdL', buf, 0)
    print(tp, size, cost, solveTimeMillis)
    nWaypoints = (len(buf) - headerSize) / wpSize
    print(nWaypoints)


    waypoints = []
    for t in range(int(nWaypoints)):
        waypoints.append(struct.unpack_from('>8d', buf, headerSize + t*wpSize))


    return waypoints




def mpl_anna(cloudburst, anna_routing_address, execution_id, sequence_num): # function to register
    import os, subprocess, time
    #local_ip = ip = os.popen("ifconfig eth0 | grep 'inet addr:' | grep -v '127.0.0.1' | cut -d: -f2 | awk '{ print $1 }'").read().strip()
    local_ip = os.popen("ifconfig eth0 | grep 'inet ' | cut -d: -f2 | awk '{ print $2 }'").read().strip()
    ip = local_ip
    #print("the local ip is " + local_ip)
    
    thread_id = str(1 + int(os.popen("echo $THREAD_ID").read().strip()))
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["LD_LIBRARY_PATH"] = "/root/local/lib:/root/local/lib64:/usr/local/lib"
    os.environ["PKG_CONFIG_PATH"] = "/root/local/share/pkgconfig:/root/local/lib64/pkgconfig"
    os.environ["PI"] = "3.141592653589793"
    os.environ["PI_2"] = "1.570796326794897"


    #if not local_ip:
    #    return None, thread_id
    #execution_command = '/mplambda/build/mpl_lambda_pseudo --scenario se3 --algorithm cforest --coordinator "$COORDINATOR" --jobs 10 --env se3/Twistycool_env.dae --robot se3/Twistycool_robot.dae --start 0,1,0,0,270,160,-200 --goal 0,1,0,0,270,160,-400 --min 53.46,-21.25,-476.86 --max 402.96,269.25,-91.0 --time-limit 60 --check-resolution 0.1 --anna_address ' + anna_address + ' --local_ip ' + local_ip + ' --execution_id ' + execution_id + ' --thread_id ' + thread_id + ' 2>/logs'
    execution_command = "sleep " + str((100-sequence_num) * 0.155) + " &&" + '/mplambda/build/mpl_lambda_pseudo --scenario fetch --algorithm cforest --coordinator "$COORDINATOR" --jobs 10 --env AUTOLAB.dae --env-frame=0.38,-0.90,0.00,0,0,-$PI_2 --goal=-1.07,0.16,0.88,0,0,0 --goal-radius=0.01,0.01,0.01,0.01,0.01,$PI --start=0.1,$PI_2,$PI_2,0,$PI_2,0,$PI_2,0 --time-limit ' + str(time_limit) + ' --check-resolution 0.01 --anna_address ' + anna_routing_address + ' --local_ip ' + local_ip + ' --execution_id ' + execution_id + ' --thread_id ' + thread_id + ' 2>/logs_{}_{}'.format(execution_id, str(time.time()))
    print(execution_command)
    #execution_command = "echo hello world" + '-anna_address ' + anna_routing_address + ' --local_ip ' + local_ip + ' --execution_id ' + execution_id + ' --thread_id ' + thread_id + ' >/logs'
    result = subprocess.run([execution_command], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    print(result)
    return result, thread_id


cloud_func = dc.register(mpl_anna, 'mpl_anna4')
# wait for 1 second for the registration process to fully finish
time.sleep(1)
# f = open("result_" + str(time.time()) + ".txt", "w")
f = open("result_" + "k_20_l_8_t_1" + ".txt", "w")


run = 0
# run the same experiment 24 times and take average
while run < total_runs:
    time.sleep(1)
    print("alive")
    run += 1
    f.write('T' + str(run) + '\n')
    print('T' + str(run))
    from random import random
    solution_key = ('solution_key_' + str(time.time()) + str(random())) # deferentiate keys  #+ str(run) +
    future_list = []   
    for i in range(100): # parallely run. 10 is the number of function requests. TODO: spin up more nodes
        #start = time.time()
        future_list.append(cloud_func(routing_elb, solution_key, i)) # routing_elb
        #print(time.time() - start)
        time.sleep(0.1)
    count = 1
    print("[[",future_list,"]]")
    future_list = filter(None, future_list )
    for future in future_list:
        print(count)
        count += 1
        print('object id is %s' % future.obj_id)
    start = time.time()
    result = None
    while result is None:
        a = 1
        if dc.kvs_client.get(solution_key)[solution_key] is not None:
            print("dc.kvs_client", dc.kvs_client, "||")
            print("&$", dc.kvs_client.get(solution_key), "&$")
            #print("|$$$", type(dc.kvs_client.get(solution_key)[solution_key].payload.peekitem(0)), "|")
        ret = dc.kvs_client.get(solution_key)
        if ret[solution_key] is not None: 
            print("heyyyy  dc.kvs_client.get(solution_key)[solution_key] is not None")
            result = ret[solution_key].payload.peekitem(0)
        if time.time() - start > time_limit: # terminate after 60 sec  # consistent with l38
            print("time out")
            break
    if result is None:
        print('no solution found')
        for future in future_list:
            future.get()  # blocking call
        continue
    if ret[solution_key] is not None:
        print("length of lattice payload = ", type(ret[solution_key].payload), ret[solution_key].payload.__len__(), "-=-")
    first = time.time()
    output = '%s, %s' % (first-start, result[0])
    print(output)
    f.write(output + '\n')
    #print(result.priority)

    last_topK = []
    while True:
        time.sleep(2)
        pl = dc.kvs_client.get(solution_key)[solution_key].payload

        key_list = []
        for key,value in pl.items():
            key_list.append(key)
        if last_topK != key_list:
            print("current topK: " + str(key_list))
            last_topK = key_list

        
        new_result = pl.peekitem(0)
        if not new_result is None and new_result[0] < result[0]: # priority is proportional to path length. the lower the better
            # top K -> pick shortest 
            result = new_result
            output = '%s, %s' % (time.time()-start, result[0])
            print(output)
            f.write(output + '\n')  # col1 time # col2 cost
            #print(result.priority)
        current_time = time.time()
        if current_time - start > time_limit: # run for 60 seconds # consistent with l38 in experiment
            break
    print('getting results')
    for future in future_list:
        future.get()  # blocking call


    print('printing waypoints')
    print(deserializePath(result[1]))
f.close()
