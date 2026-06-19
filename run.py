"""
run.py
Launches Sprandy locally. Usage: python run.py
Visit http://127.0.0.1:8000 once it's running.
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
