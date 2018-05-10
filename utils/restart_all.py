from docker import Client as DockerClient
from docker import tls as docker_tls
import datetime

MAX_RESTART_TIME = 60

manager = DockerClient(base_url='unix://var/run/docker.sock')

worker_nodes = manager.nodes(filters={'role': 'worker'})
restart_begin_time = datetime.datetime.now()
print("The current time is", restart_begin_time)

total_node_count = len(worker_nodes)
nodes_restarted = 0

print("Found", total_node_count, "worker nodes.")

node_clients = []
factomd_container_ids = []
print("Beginning restart.")
# Stop all the running factomd containers.
for node in worker_nodes:
    try:
        try:
            tls_config = docker_tls.TLSConfig(
                client_cert=('/home/ec2-user/tls/cert.pem',
                             '/home/ec2-user/tls/key.pem')
            )
            node_client = DockerClient(
                base_url=node['Spec']['Labels']['ip'] + ':' + node['Spec']['Labels']['engine_port'], tls=tls_config)
        except Exception as e:
            print("Error opening docker client.")
            raise(e)
        try:
            factomd_container_id = node_client.containers(
                filters={'status': 'running', 'label': 'name=factomd'})[0]
        except Exception as e:
            print("Error fetching container id for factomd")
            raise(e)
        try:
            node_client.stop(factomd_container_id)
        except Exception as e:
            print("Error restarting factomd container!")
            raise(e)
        node_clients.append(node_client)
        factomd_container_ids.append(factomd_container_id)
    except Exception as e:
        print("Error retrieving and stopping factomd container from node", node)
        print(e)

# Start all the containers using the appropriate client
assert len(node_clients) == len(factomd_container_ids)

client_containers = zip(node_clients, factomd_container_ids)

for client, container in client_containers:
    client.start(container)
    nodes_restarted += 1

if (datetime.datetime.now() - restart_begin_time).seconds > MAX_RESTART_TIME:
    print("WARNING: Restart took longer than", MAX_RESTART_TIME, "seconds!")
    print("Abnormal behavior expected!")
else:
    print("Restart completed in", (datetime.datetime.now() -
                                   restart_begin_time).seconds, "seconds.")
    print("Restarted", nodes_restarted, "out of", total_node_count, "nodes.")
