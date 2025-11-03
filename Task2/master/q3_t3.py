"""
You are allowed use necessary python libraries.
You are not allowed to have any global function or variables.
"""
# from dotenv import load_dotenv
import os
import pandas as pd
from mpi4py import MPI

# load_dotenv()


class MPISolution:
    """
    You are allowed to implement as many methods and variables as you wish
    """
    def __init__(self, dataset_path=None, dataset_size=None):
        self.dataset_path = dataset_path
        self.dataset_size = dataset_size
    
    def distribute_chunks(self, total_size, num_processes):
        """
        Distributes total_size into num_chunks nearly equal parts.
        Returns a list of chunk sizes.
        """
        base_size = total_size // num_processes
        remainder = total_size % num_processes
        chunk_sizes = [base_size + 1 if i < remainder else base_size for i in range(num_processes)]
        return chunk_sizes

    def run(self)->tuple[str,list,list,float]:
        """
        Returns the tuple of (final_answer,chunkSizePerThread,answerPerThread,totalTimeTaken)
        """
        try:
            if (self.dataset_size is None) or (self.dataset_path is None):
                raise ValueError("dataset_size and dataset_path must be set")
            if self.dataset_path is None:
                raise ValueError("dataset_path must be set before calling this method")
            if not os.path.exists(self.dataset_path):
                raise FileNotFoundError(f"The dataset file at {self.dataset_path} does not exist.")

            start_time = MPI.Wtime()
            comm = MPI.COMM_WORLD
            rank = comm.Get_rank()
            size = comm.Get_size()

            if rank == 0:
                if size <= 1:
                    raise RuntimeError("MPI world size must be at least 2 to distribute work")

                slave_workers = size - 1
                chunk_distribution = self.distribute_chunks(self.dataset_size, slave_workers)
                starting_indices = [0]
                for chunk_size in chunk_distribution[:-1]:
                    starting_indices.append(starting_indices[-1] + chunk_size)

                # Distribute task to all slaves
                for worker in range(1, size):
                    task_index = worker - 1
                    payload = {
                        "chunk_size": chunk_distribution[task_index],
                        "start_index": starting_indices[task_index],
                    }
                    comm.send(payload, dest=worker)

                # Each worker processes its chunk and sends back the result
                results = []
                for worker in range(1, size):
                    result = comm.recv(source=worker)
                    results.append(result)
                    # print(f"Worker {worker} processed its chunk and sent back the result.")
                
                final_answer = '-----'
                chunkSizePerThread = chunk_distribution
                answerPerThread = results
                end_time = MPI.Wtime()
                total_time_taken = end_time - start_time
                return final_answer, chunkSizePerThread, answerPerThread, total_time_taken
            else:
                payload = comm.recv(source=0)
                chunk_size = payload.get("chunk_size", 0)
                start_index = payload.get("start_index", 0)
                # print(f"Worker {rank} received chunk starting at {start_index} with size {chunk_size}")

                if chunk_size <= 0:
                    count = 0
                else:
                    try:
                        skiprows_range = range(1, start_index + 1)
                        df = pd.read_csv(
                            self.dataset_path,
                            usecols=["BId", "RScore", "UId", "UName"],
                            skiprows=skiprows_range,
                            nrows=chunk_size,
                        )

                        agg = (
                            df.groupby("UId")
                            .agg(
                                rscore_sum=("RScore", "sum"),
                                rscore_count=("RScore", "count"),
                                books=("BId", "nunique"),
                                name=("UName", "first"),
                            )
                        )

                        candidates = agg[agg["rscore_sum"] == 4 * agg["rscore_count"]]
                        result = ("", 0)
                        if not candidates.empty:
                            max_uid = candidates["books"].idxmax()
                            name_val = candidates.at[max_uid, "name"]
                            books_val = candidates.at[max_uid, "books"]
                            name = "" if pd.isna(name_val) else str(name_val)
                            # Coerce to numeric and convert to built-in int
                            num = pd.to_numeric(books_val, errors="coerce")
                            try:
                                count = int(num.item())  # type: ignore[attr-defined]
                            except Exception:
                                count = int(num)  # type: ignore[arg-type]
                            result = (name, count)

                        comm.send(result, dest=0)
                    except Exception as e:
                        comm.send(("", 0), dest=0)  

                return '-----', [], [], 0.0  # Return a default value for non-master ranks
        except Exception as e:
            return ' ', [], [], 0.0 # In case of any error, return default

if __name__ == '__main__':
    DATA_PATH = os.getenv('PATH_DATASET') 
    solution = MPISolution(dataset_path=DATA_PATH, dataset_size=3000000)
    final_answer,chunkSizePerThread,answerPerThread,totalTimeTaken = solution.run()
    
    # if master worker:
        #print({"final_answer":final_answer,"chunkSizePerThread":chunkSizePerThread,"answerPerThread":answerPerThread,"totalTimeTaken":totalTimeTaken}) 
    comm = MPI.COMM_WORLD
    if comm.Get_rank() == 0:
        print({
            "final_answer": final_answer,
            "chunkSizePerThread": chunkSizePerThread,
            "answerPerThread": answerPerThread,
            "totalTimeTaken": totalTimeTaken,
        })
