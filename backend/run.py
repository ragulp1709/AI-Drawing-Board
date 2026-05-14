# run.py — Start the AI Drawing Board web server
import os
import sys
import uvicorn

if __name__ == "__main__":
    # Put the project root on sys.path so uvicorn can resolve 'backend.server'
    projectRoot = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(projectRoot)
    sys.path.insert(0, projectRoot)
    print("[INFO] Starting AI Drawing Board at http://localhost:8000")
    uvicorn.run("backend.server:app", host="0.0.0.0", port=8000, reload=False)
