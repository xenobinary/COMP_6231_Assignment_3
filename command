Task 1:

Docker image creation part
Server: 
FROM ozxx33/fileserver-base
WORKDIR /usr/src/app
COPY ./server.py .
CMD ["python", "./server.py"]

go to the directory whereh the Dockerfile and server.py are present, then run the following command to build the image: 
docker build -t task1_server .
explanation: creates a docker image with the name task1_server with current directory files.

Client:
FROM ozxx33/fileserver-base
WORKDIR /usr/src/app
COPY . .
ENV SERVER_IP=server
ENV SERVER_PORT=65432
CMD ["python", "./client.py"]

go to the directory whereh the Dockerfile and client.py are present, then run the following command to build the image:
docker build -t task1_client .
explanation: creates a docker image with the name task1_client with current directory files.

Create a docker overlay network:
docker swarm init
after this command, we get a token to join the swarm from other computers.
docker swarm join --token SWMTKN-1-1s98jjyar97v56xixj7wh7jf3wlzcdb5oodn9uldsfhdcmocrr-0zaaxsd8m4ml1bpredq1uqfii 192.168.12.3:2377
(or use docker swarm join-token worker to get the token)

Then run the following command to create overlay network:
docker network create -d overlay 6231-net

In other computers, run the following command to join the swarm:
docker swarm join --token <token> <manager-ip>:2377

We can check the nodes in the swarm on manager computer using:
docker node ls

Copy the client build Dockerfile to other computers and build the image using the same command as above.
(or we can save the image as a tar file using docker save and load it in other computers using docker load
in manager computer: docker save -o task1_client.tar task1_client
in worker computer: docker load -i task1_client.tar)

Run the server container in manager node:
docker run -it --rm --name server --hostname server --network 6231-net task1_server bash
root@server:/usr/src/app# hostname -i
10.0.1.28
root@server:/usr/src/app# python server.py
Server listening on 0.0.0.0:65432

Run the client container in the first worker nodes:
docker run -it --rm --name client1 --hostname client1 --network 6231-net task1_client bash
root@client1:/usr/src/app# hostname -i
10.0.1.30
root@client1:/usr/src/app# python client.py

Run the client container in the second worker nodes:
docker run -it --rm --name client2 --hostname client2 --network 6231-net task1_client bash
root@client2:/usr/src/app# python client.py

docker run -it --rm --name client3 --hostname client3 --network 6231-net task1-client bash
root@client3:/usr/src/app# hostname -i
10.0.1.34
root@client3:/usr/src/app# python client.py


Task 2:
Docker image creation part

# Start from an official Python image
FROM python:3.10-slim

# Set environment variables for non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

# Install OpenSSH for communication and OpenMPI for the cluster
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    openmpi-bin \
    libopenmpi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install the mpi4py library for Python
RUN pip install --no-cache-dir mpi4py
RUN pip install pandas

# Create working directory
RUN mkdir -p /app
WORKDIR /app

# Create .ssh directory
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh

# Copy the same SSH key pair to all containers
COPY id_rsa /root/.ssh/
COPY id_rsa.pub /root/.ssh/
RUN chmod 600 /root/.ssh/id_rsa && \
    cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys && \
    chmod 600 /root/.ssh/authorized_keys

# Configure SSH
RUN echo "    StrictHostKeyChecking no" >> /etc/ssh/ssh_config && \
    echo "    UserKnownHostsFile /dev/null" >> /etc/ssh/ssh_config

# Set environment variable for dataset path
ENV PATH_DATASET="/app/Books_rating.csv"

# start the SSH service
CMD ["/usr/sbin/sshd", "-D"]
go to the directory whereh the Dockerfile is present, then run the following command to build the image:
docker build -t mpi-node .
explanation: creates a docker image with the name mpi-node with current directory files.

In the same directory, create a hostfile.txt with the following content:
mpi-head slots=1
mpi-worker1 slots=2
mpi-worker2 slots=2
mpi-worker3 slots=2
mpi-worker4 slots=2
mpi-worker5 slots=2
mpi-worker6 slots=2
mpi-worker7 slots=2
mpi-worker8 slots=2
mpi-worker9 slots=2
mpi-worker10 slots=2

In the same directory, place the dataset Books_rating.csv and the mpi program q1_t3.py, q2_t3.py, q3_t3.py, q4_t3.py.
In the manager node, create a manager container:
docker run -d --name mpi-head --hostname mpi-head --network 6231-net -v "$(pwd):/app:ro" mpi-node

In the manager node, create one worker container:
docker run -d --name mpi-worker1 --hostname mpi-worker1 --network 6231-net -v "$(pwd):/app:ro" mpi-node
docker run -d --name mpi-worker2 --hostname mpi-worker2 --network 6231-net -v "$(pwd):/app:ro" mpi-node

In the worker node, create worker containers using the same command (with different hostname) as above.
Worker1: 
docker run -d --name mpi-worker3 --hostname mpi-worker3 --network 6231-net -v "$(pwd):/app:ro" mpi-node
docker run -d --name mpi-worker4 --hostname mpi-worker4 --network 6231-net -v "$(pwd):/app:ro" mpi-node
docker run -d --name mpi-worker5 --hostname mpi-worker5 --network 6231-net -v "$(pwd):/app:ro" mpi-node
Worker2:
docker run -d --name mpi-worker6 --hostname mpi-worker6 --network 6231-net -v "$(pwd):/app:ro" mpi-node
docker run -d --name mpi-worker7 --hostname mpi-worker7 --network 6231-net -v "$(pwd):/app:ro" mpi-node
docker run -d --name mpi-worker8 --hostname mpi-worker8 --network 6231-net -v "$(pwd):/app:ro" mpi-node
Worker3:
docker run -d --name mpi-worker9 --hostname mpi-worker9 --network 6231-net -v "$(pwd):/app:ro" mpi-node
docker run -d --name mpi-worker10 --hostname mpi-worker10 --network 6231-net -v "$(pwd):/app:ro" mpi-node



In the manager node, run the following command to access the mpi-head container:
docker exec -it mpi-head bash

then run the following command to execute the mpi program using mpirun or mpiexec:
0 process:
mpirun --allow-run-as-root --mca btl_tcp_if_include eth0 --mca oob_tcp_if_include eth0 -n 1 --host mpi-worker4 -x PATH_DATASET="/app/Books_rating.csv" python q1_t3.py

1 processes:
mpirun --allow-run-as-root --mca btl_tcp_if_include eth0 --mca oob_tcp_if_include eth0 -n 2 --host mpi-head,mpi-worker4 -x PATH_DATASET="/app/Books_rating.csv" python q1_t3.py

2 processes:
mpirun --allow-run-as-root --mca btl_tcp_if_include eth0 --mca oob_tcp_if_include eth0 -n 3 --host mpi-head,mpi-worker3,mpi-worker4 -x PATH_DATASET="/app/Books_rating.csv" python q1_t3.py

3 processes:
mpirun --allow-run-as-root --mca btl_tcp_if_include eth0 --mca oob_tcp_if_include eth0 -n 4 --host mpi-head,mpi-worker6,mpi-worker3,mpi-worker9 -x PATH_DATASET="/app/Books_rating.csv" python q1_t3.py

4 processes:
mpirun --allow-run-as-root --mca btl_tcp_if_include eth0 --mca oob_tcp_if_include eth0 -n 5 --host mpi-head,mpi-worker1,mpi-worker3,mpi-worker6,mpi-worker9 -x PATH_DATASET="/app/Books_rating.csv" python q1_t3.py

Q1t3: 5.696596401
Q2t3: 6.529791102
q3t3: 8.672914233
q4t3: 6.553401591

5 processes:
mpirun --allow-run-as-root --mca btl_tcp_if_include eth0 --mca oob_tcp_if_include eth0 -n 6 --host mpi-head,mpi-worker1,mpi-worker2,mpi-worker3,mpi-worker6,mpi-worker9 -x PATH_DATASET="/app/Books_rating.csv" python q1_t3.py

Q1t3: 9.661271696
Q2t3: 9.30441128
Q3t3: 13.037916583
q4t3: 10.614299845

6 processes:
mpirun --allow-run-as-root --mca btl_tcp_if_include eth0 --mca oob_tcp_if_include eth0 -n 7 --host mpi-head,mpi-worker1,mpi-worker2,mpi-worker3,mpi-worker4,mpi-worker6,mpi-worker9 -x PATH_DATASET="/app/Books_rating.csv" python q1_t3.py

Q1t3: 12.016897256
Q2t3: 12.348387634000002
Q3t3: 12.451021179
q4t3: 12.431010434000001

7 processes:
mpirun --allow-run-as-root --mca btl_tcp_if_include eth0 --mca oob_tcp_if_include eth0 -n 8 --host mpi-head,mpi-worker1,mpi-worker2,mpi-worker3,mpi-worker4,mpi-worker6,mpi-worker10,mpi-worker9 -x PATH_DATASET="/app/Books_rating.csv" python q1_t3.py

Q1t3: 10.960901164000001
Q2t3: 10.768961308000002
Q3t3: 10.696905724
q4t3: 11.279467695

8 processes:
mpirun --allow-run-as-root --mca btl_tcp_if_include eth0 --mca oob_tcp_if_include eth0 -n 9 --host mpi-head,mpi-worker1,mpi-worker2,mpi-worker3,mpi-worker4,mpi-worker5,mpi-worker6,mpi-worker10,mpi-worker9 -x PATH_DATASET="/app/Books_rating.csv" python q1_t3.py

Q1t3: 15.865010103
Q2t3: 13.819409182
Q3t3: 14.294992356
q4t3: 13.319243172

9 processes:
mpirun --allow-run-as-root --mca btl_tcp_if_include eth0 --mca oob_tcp_if_include eth0 -n 10 --host mpi-head,mpi-worker1,mpi-worker2,mpi-worker3,mpi-worker4,mpi-worker5,mpi-worker6,mpi-worker8,mpi-worker10,mpi-worker9 -x PATH_DATASET="/app/Books_rating.csv" python q1_t3.py

Q1t3: 14.444542352
Q2t3: 12.109358837
Q3t3: 12.676043157
q4t3: 13.091119011

10 processes:
mpirun --allow-run-as-root --mca btl_tcp_if_include eth0 --mca oob_tcp_if_include eth0 -n 11 --host mpi-head,mpi-worker1,mpi-worker2,mpi-worker3,mpi-worker4,mpi-worker5,mpi-worker6,mpi-worker7,mpi-worker8,mpi-worker10,mpi-worker9 -x PATH_DATASET="/app/Books_rating.csv" python q1_t3.py

Q1t3: 15.423924749
Q2t3: 13.614748411
Q3t3: 13.620505634
q4t3: 12.144080002

