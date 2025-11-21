#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv

from pdf_vision_processor.cli import main as cli_main

def main():
    """
    Starts the PDF Vision Processor API.
    1. Loads environment variables from .env
    2. Ensures execution within the .venv virtual environment
    3. Runs the Uvicorn server
    """
    # 1. Import environment from .env
    load_dotenv()

    # 2. Use python venv
    # Check if we are running inside the expected venv
    project_root = os.path.dirname(os.path.abspath(__file__))
    venv_path = os.path.join(project_root, ".venv")
    
    # If .venv exists and we aren't using its python, switch to it
    if os.path.exists(venv_path):
        # Normalize paths for comparison
        running_python_prefix = os.path.normpath(sys.prefix)
        venv_path_norm = os.path.normpath(venv_path)
        
        # Check if the current prefix matches the venv path
        # Note: In some venv setups, sys.prefix might be slightly different, 
        # but checking if the binary is inside .venv is a good heuristic.
        if venv_path_norm not in running_python_prefix:
            print(f"Switching to virtual environment at {venv_path}...")
            venv_python = os.path.join(venv_path, "bin", "python")
            
            if os.path.exists(venv_python):
                # Replace current process with venv python
                # We pass the script name as the first argument
                os.execv(venv_python, [venv_python] + sys.argv)
            else:
                print("Warning: .venv found but python binary missing.")
    
    # 3. Start the API via the packaged CLI
    print("Starting PDF Vision Processor API...")
    cli_main(sys.argv[1:])

if __name__ == "__main__":
    main()
