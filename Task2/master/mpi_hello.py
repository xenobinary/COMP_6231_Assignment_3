from mpi4py import MPI
import socket

def main():
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    hostname = socket.gethostname()
    
    print(f"Hello from process {rank} out of {size} on {hostname}!!!!")
    
    # Test communication between processes
    if size >= 2:
        # print(f"Testing communication between rank 0 and rank 1")
        if rank == 0:
            # Rank 0 sends first
            data = {"message": "Hello from rank 0!", "number": 42}
            comm.send(data, dest=1, tag=11)
            print(f"Rank {rank} sent: {data}")
            # Then it receives
            received_data = comm.recv(source=1)
            print(f"Rank {rank} received: {received_data}")

        elif rank == 1:
            # Rank 1 receives first
            received_data = comm.recv(source=0, tag=11)
            print(f"Rank {rank} received: {received_data}")
            # Then it sends
            data = {"message": "Hello from rank 1!", "number": 24}
            comm.send(data, dest=0)
            print(f"Rank {rank} sent: {data}")
    
    # Synchronize all processes
    comm.barrier()
    
    # Broadcast from root process (0) to all others
    # if rank == 0:
    #     broadcast_data = "Broadcast message from root!"
    # else:
    #     broadcast_data = None
    
    # broadcast_data = comm.bcast(broadcast_data, root=0)
    # print(f"Rank {rank} received broadcast: {broadcast_data}")

if __name__ == "__main__":
    main()