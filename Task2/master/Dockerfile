# Start from a newer official Python image
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

# Copy MPI program
# COPY mpi_hello.py /app/

# Create .ssh directory
RUN mkdir -p /root/.ssh && \
    chmod 700 /root/.ssh

# Copy the same SSH key pair to all containers (we'll generate these once)
COPY id_rsa /root/.ssh/
COPY id_rsa.pub /root/.ssh/
RUN chmod 600 /root/.ssh/id_rsa && \
    cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys && \
    chmod 600 /root/.ssh/authorized_keys

# Configure SSH
RUN echo "    StrictHostKeyChecking no" >> /etc/ssh/ssh_config && \
    echo "    UserKnownHostsFile /dev/null" >> /etc/ssh/ssh_config

ENV PATH_DATASET="Books_rating.csv"

CMD ["/usr/sbin/sshd", "-D"]