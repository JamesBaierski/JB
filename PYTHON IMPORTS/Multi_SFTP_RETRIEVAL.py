import paramiko
import pysftp
import os
from datetime import datetime, timedelta
import logging
from pathlib import Path
import re
import shutil
import warnings

# Set your date range here
START_DATE = "01/20/2025"  # Format: MM/DD/YYYY
END_DATE = "01/20/2025"    # Format: MM/DD/YYYY

# SFTP Configurations for different servers
SFTP_CONFIGS = {
    A": {
        "host": ,
        "username": ,
        "password": ,
        "port": 22,
        "paths": [
            
        ]
    },
    "B": {
        "host": ,
        "username": ,
        "password": ,
        "port": 22,
        "paths": [
            ,
            '
        ]
    },
    "C": {
        "host": ,
        "username": ,
        "password": ,
        "port": 22,
        "paths": [
            
        ]
    }
}

# Disable host key checking
warnings.filterwarnings('ignore', 'Unknown ssh-rsa host key')

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sftp_retriever.log', mode='w'),
        logging.StreamHandler()
    ]
)

class SFTPFileRetriever:
    def __init__(self, host, username, password, remote_path, local_path, port=22):
        self.logger = logging.getLogger(__name__)
        self.host = host
        self.username = username
        self.password = password
        self.remote_path = remote_path
        self.local_path = local_path
        self.port = port
        
        # Define SFTP connection options
        self.cnopts = pysftp.CnOpts()
        self.cnopts.hostkeys = None  # Disable host key checking

    def is_target_file(self, filename):
        """Check if the file is a PDF, Excel, or CSV file."""
        pattern = r'\.(pdf|xls[xmb]?|csv)$'
        return bool(re.search(pattern, filename.lower()))

    def get_file_type(self, filename):
        """Determine the file type category based on extension."""
        if filename.lower().endswith('.pdf'):
            return 'pdf'
        elif filename.lower().endswith('.csv'):
            return 'csv'
        else:  # .xls, .xlsx, .xlsm
            return 'excel'

    def create_base_folders(self, start_date, end_date, provider_name):
        """
        Create base PDF, Excel, and CSV folders.
        Returns a dictionary with paths for each file type.
        """
        base_path = Path(self.local_path)
        base_path.mkdir(parents=True, exist_ok=True)
        
        # Format dates for folder names
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        folder_paths = {}
        
        # Create one folder each for PDFs, Excel files, and CSVs
        for doc_type in ['PDF', 'Excel', 'CSV']:
            folder_name = f"{provider_name}_{doc_type}_{start_str}_{end_str}"
            folder_path = base_path / folder_name
            folder_path.mkdir(parents=True, exist_ok=True)
            folder_paths[doc_type.lower()] = folder_path
            
        return folder_paths

    def retrieve_files_by_date_range(self, start_date_str, end_date_str, provider_name):
        """
        Retrieve files within a specified date range and sort them into type-specific folders.
        """
        try:
            # Convert date strings to timestamps for comparison
            start_date = datetime.strptime(start_date_str, '%m/%d/%Y')
            end_date = datetime.strptime(end_date_str, '%m/%d/%Y')
            
            # Ensure end date is at the end of the day for inclusive comparison
            end_date = end_date.replace(hour=23, minute=59, second=59)
            
            # Create base folders
            folder_paths = self.create_base_folders(start_date, end_date, provider_name)
            self.logger.info(f"Created base folders: {folder_paths}")
            
            # Connect to SFTP server
            self.logger.info(f"Connecting to {self.host}...")
            with pysftp.Connection(
                host=self.host,
                username=self.username,
                password=self.password,
                port=self.port,
                cnopts=self.cnopts
            ) as sftp:
                self.logger.info("Connected successfully")
                
                # Change to remote directory
                sftp.chdir(self.remote_path)
                self.logger.info(f"Changed to remote directory: {self.remote_path}")
                
                # List directory contents
                dir_items = sftp.listdir_attr()
                self.logger.info(f"Found {len(dir_items)} items in directory")
                
                # Filter and download files
                count = {'pdf': 0, 'excel': 0, 'csv': 0}
                for item in dir_items:
                    # Convert timestamp to datetime
                    file_date = datetime.fromtimestamp(item.st_mtime)
                    
                    # Check if file is within date range and matches our criteria
                    if (start_date <= file_date <= end_date and 
                        self.is_target_file(item.filename)):
                        
                        remote_path = f"{self.remote_path}/{item.filename}"
                        
                        # Determine file type and add path prefix to filename
                        path_prefix = self.remote_path.strip('/').replace('/', '_')
                        file_type = self.get_file_type(item.filename)
                        dest_folder = folder_paths[file_type]
                            
                        # Create a unique filename by prepending the path
                        new_filename = f"{path_prefix}_{item.filename}"
                        local_file = dest_folder / new_filename
                        
                        self.logger.info(f"Downloading {item.filename} to {dest_folder} as {new_filename}...")
                        sftp.get(remote_path, str(local_file))
                        count[file_type] += 1
                
                self.logger.info(f"Downloaded {count['pdf']} PDF files, {count['excel']} Excel files, and {count['csv']} CSV files")
            
            # Verify downloads
            for doc_type, folder in folder_paths.items():
                if doc_type == 'pdf':
                    pattern = '*.pdf'
                elif doc_type == 'csv':
                    pattern = '*.csv'
                else:  # excel
                    pattern = '*.xls*'
                    
                files = list(folder.rglob(pattern))
                self.logger.info(f"Files in {doc_type} folder: {len(files)}")
            
            return count
            
        except Exception as e:
            self.logger.error(f"An error occurred: {str(e)}")
            import traceback
            self.logger.error(f"Traceback:\n{traceback.format_exc()}")
            return None

# Run the file retriever
if __name__ == "__main__":
    try:
        # Create timestamp for base folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_path = Path(PATH)
        
        grand_total = {'pdf': 0, 'excel': 0, 'csv': 0}
        
        # Process each provider
        for provider_name, config in SFTP_CONFIGS.items():
            print(f"\nProcessing provider: {provider_name}")
            
            # Create provider-specific local path
            local_path = base_path / f"{provider_name}_Files{timestamp}"
            
            # Process each path for this provider
            for path in config['paths']:
                print(f"\nProcessing path: {path}")
                
                # Update config with current path and local path
                current_config = {
                    "host": config['host'],
                    "username": config['username'],
                    "password": config['password'],
                    "port": config['port'],
                    "remote_path": path,
                    "local_path": local_path
                }
                
                # Create retriever instance
                retriever = SFTPFileRetriever(**current_config)
                
                # Retrieve files for the specified date range
                result = retriever.retrieve_files_by_date_range(START_DATE, END_DATE, provider_name)
                
                if result:
                    print(f"Download completed successfully for {path}!")
                    print(f"Downloaded {result['pdf']} PDF files, {result['excel']} Excel files, and {result['csv']} CSV files")
                    for file_type in ['pdf', 'excel', 'csv']:
                        grand_total[file_type] += result[file_type]
        
        print("\nGrand total of files downloaded:")
        print(f"PDFs: {grand_total['pdf']}")
        print(f"Excel files: {grand_total['excel']}")
        print(f"CSV files: {grand_total['csv']}")
            
    except ImportError:
        print("Please install required packages:")
        print("pip install paramiko pysftp")
