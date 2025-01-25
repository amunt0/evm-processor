import os
import sys
import time
import json
import signal
import logging
import requests
from pathlib import Path
from typing import Optional, Dict, Tuple
from datetime import datetime

# Custom JSON Formatter
class JsonFormatter(logging.Formatter):
    def format(self, record):
        if isinstance(record.msg, dict):
            json_record = record.msg
        else:
            json_record = {'message': record.msg}
        
        json_record.update({
            'timestamp': self.formatTime(record),
            'level': record.levelname
        })
        return json.dumps(json_record)

# Set up JSON logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.handlers = [handler]

class BlockExplorer:
    def __init__(self):
        self.storage_path = Path(os.getenv('STORAGE_PATH', '/data'))
        self.tendermint_url = os.getenv('TM_NODE')
        self.blocks_file = self.storage_path / 'blocks.csv'
        self.last_processed_height = 1
        self.running = True
        
        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Check if we can acquire the lock
        if not self._check_and_acquire_lock():
            logger.info({
                "event": "init",
                "message": "Exiting due to existing processor"
            })
            sys.exit(0)
            
        # Initialize or read existing blocks file
        self._init_blocks_file()
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)

    def _check_and_acquire_lock(self):
        """Check if another processor is running and acquire lock if not"""
        self.state_file = self.storage_path / 'processor.state'
        
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                state = f.read().strip()
                if state == "processing":
                    logger.info({
                        "event": "init",
                        "message": "Another processor is running, exiting"
                    })
                    return False
        
        with open(self.state_file, 'w') as f:
            f.write("processing\n")
        return True
        
    def _init_blocks_file(self):
        """Initialize blocks.csv file and get last processed height"""
        if not self.blocks_file.exists():
            # Create file with header
            with open(self.blocks_file, 'w') as f:
                f.write("height,hash\n")
            logger.info({
                "event": "init",
                "message": "Created new blocks.csv file"
            })
        else:
            # Read last processed height
            try:
                with open(self.blocks_file, 'r') as f:
                    lines = f.readlines()
                    if len(lines) > 1:  # If we have data beyond header
                        last_line = lines[-1].strip()
                        self.last_processed_height = int(last_line.split(',')[0])
                        logger.info({
                            "event": "init",
                            "message": "Found existing blocks.csv",
                            "last_height": self.last_processed_height
                        })
            except Exception as e:
                logger.error({
                    "event": "error",
                    "message": "Error reading blocks.csv",
                    "error": str(e)
                })

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info({
            "event": "shutdown_initiated",
            "message": f"Received signal {signum}, initiating graceful shutdown",
            "last_processed_height": self.last_processed_height
        })
        # Remove state file on shutdown
        if hasattr(self, 'state_file') and self.state_file.exists():
            self.state_file.unlink()
        self.running = False

    def get_block(self, height: Optional[int] = None) -> Tuple[Optional[int], Optional[str]]:
        """Get block information from Tendermint node"""
        try:
            url = f"{self.tendermint_url}/block"
            if height is not None:
                url = f"{url}?height={height}"
            
            logger.info({
                "event": "request",
                "message": "Making request to tendermint",
                "url": url
            })
            
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            block_height = int(data['result']['block']['header']['height'])
            block_hash = data['result']['block_id']['hash']
            
            return block_height, block_hash
            
        except Exception as e:
            logger.error({
                "event": "error",
                "message": "Error fetching block",
                "height": height,
                "error": str(e)
            })
            return None, None

    def append_block(self, height: int, block_hash: str) -> bool:
        """Append block information to blocks.csv"""
        try:
            with open(self.blocks_file, 'a') as f:
                f.write(f"{height},{block_hash}\n")
            self.last_processed_height = height
            return True
        except Exception as e:
            logger.error({
                "event": "error",
                "message": "Error appending block",
                "height": height,
                "error": str(e)
            })
            return False

    def process_missing_blocks(self, current_height: int):
        """Process any missing blocks between last processed and current"""
        if self.last_processed_height < current_height:
            for height in range(self.last_processed_height + 1, current_height + 1):
                if not self.running:
                    logger.info({
                        "event": "shutdown_processing",
                        "message": "Stopping block processing due to shutdown signal",
                        "last_height": self.last_processed_height
                    })
                    return
                
                block_height, block_hash = self.get_block(height)
                if block_height is not None and block_hash is not None:
                    if self.append_block(block_height, block_hash):
                        logger.info({
                            "event": "block_processed",
                            "height": block_height,
                            "hash": block_hash
                        })
                    else:
                        # If we fail to append, stop processing to maintain linearity
                        break
                else:
                    # If we can't get a block, stop processing to maintain linearity
                    break

    def run(self):
        """Main processing loop"""
        logger.info({
            "event": "startup",
            "message": "Starting block explorer",
            "tendermint_url": self.tendermint_url,
            "storage_path": str(self.storage_path)
        })
        
        while self.running:
            try:
                # Get latest block
                current_height, current_hash = self.get_block()
                
                if current_height is not None:
                    # Process any missing blocks
                    self.process_missing_blocks(current_height)
                
                # Wait a bit before next check
                time.sleep(1)
                
            except Exception as e:
                logger.error({
                    "event": "error",
                    "message": "Error in main loop",
                    "error": str(e)
                })
                time.sleep(5)
                
        # Shutdown sequence
        logger.info({
            "event": "shutdown_complete",
            "message": "Block explorer shutdown complete",
            "final_height": self.last_processed_height
        })

if __name__ == "__main__":
    explorer = BlockExplorer()
    explorer.run()