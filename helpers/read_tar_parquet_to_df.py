import tarfile
import io
import pyarrow.parquet as pq

def process_parquet_files_from_tar(tar_path, work_on_df, number_of_files=None):
    """
    Process Parquet files from a tar archive.

    Args:
        tar_path (str): The path to the tar archive.
        work_on_df (function): A function that takes a pandas DataFrame as input and performs some operation on it.
        number_of_files (int, optional): The maximum number of files to process. Defaults to None.

    Returns:
        None
    """
    # Open the tar file
    with tarfile.open(tar_path, 'r') as tar:
        # Iterate over each member in the tar file
        for i, member in enumerate(tar.getmembers()):
            # Check if the member is a file
            if member.isfile() and member.name.endswith('.parquet'):
                # Extract the file into an in-memory bytes buffer
                file_obj = tar.extractfile(member)
                if file_obj is not None:
                    # Read the Parquet file from the bytes buffer
                    with io.BytesIO(file_obj.read()) as buffer:
                        table = pq.read_table(buffer)
                        # Process the Parquet file (table)
                        print(f"Processing {member.name}")
                        # Example: print the first few rows
                        work_on_df(table.to_pandas())
                        if number_of_files is not None and i + 1 >= number_of_files:
                            break