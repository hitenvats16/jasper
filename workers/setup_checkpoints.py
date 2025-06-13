import os
import zipfile
import logging
import requests
from tqdm import tqdm
import io
import shutil
from core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def download_file(url: str, save_path: str):
    """Download a file with a progress bar"""
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Raise an exception for bad status codes
    
    # Get the total file size
    total_size = int(response.headers.get('content-length', 0))
    
    # Create progress bar
    progress_bar = tqdm(
        total=total_size,
        unit='iB',
        unit_scale=True,
        desc=f"Downloading {os.path.basename(save_path)}"
    )
    
    # Download the file with progress bar
    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                size = f.write(chunk)
                progress_bar.update(size)
    
    progress_bar.close()
    
    # Verify file size
    if os.path.getsize(save_path) != total_size:
        raise Exception("Downloaded file size doesn't match expected size")

def setup_checkpoints():
    """
    Download checkpoints from URL, extract them to the workers directory,
    and clean up the zip file.
    """
    checkpoints_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "checkpoints")
    zip_path = os.path.join(checkpoints_dir, "checkpoints.zip")
    extract_dir = os.path.join(checkpoints_dir)

    # Remove checkpoints directory if it exists
    if os.path.exists(checkpoints_dir):
        shutil.rmtree(checkpoints_dir)
    
    # Create checkpoints directory
    os.makedirs(checkpoints_dir, exist_ok=True)

    try:
        # Download the file
        logger.info(f"Downloading checkpoints from: {settings.CHECKPOINTS_URL}")
        os.makedirs(checkpoints_dir, exist_ok=True)
        download_file(settings.CHECKPOINTS_URL, zip_path)

        # ensure extract_dir exists
        os.makedirs(extract_dir, exist_ok=True)

        # Extract the zip file
        logger.info(f"Extracting zip file to: {extract_dir}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        logger.info("Checkpoints setup completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error setting up checkpoints: {str(e)}")
        # Clean up in case of error
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        return False