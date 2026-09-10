import os
import zipfile
import shutil
import uuid
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

jobs = {}
BASE_DIR = os.getcwd()

def process_audio(job_id: str, input_path: str, targets_str: str, folder_name: str):
    try:
        os.system(f"python -m demucs.separate -n htdemucs \"{input_path}\" -o \"{BASE_DIR}/output\"")
        out_dir = os.path.join(BASE_DIR, "output", "htdemucs", folder_name)
        zip_path = os.path.join(BASE_DIR, f"{job_id}_stems.zip")
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for stem in targets_str.split(","):
                stem_file = os.path.join(out_dir, f"{stem}.wav")
                if os.path.exists(stem_file):
                    zipf.write(stem_file, arcname=f"{stem}.wav")
        jobs[job_id] = "DONE"
    except Exception:
        jobs[job_id] = "ERROR"
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)

@app.get("/")
def read_root():
    return {"status": "TRẠM AI RENDER ĐANG CHẠY MƯỢT MÀ! 🚀"}

@app.post("/separate")
async def separate_audio(background_tasks: BackgroundTasks, file: UploadFile = File(...), targets: str = Form("vocals,bass,drums,other")):
    job_id = str(uuid.uuid4().hex)
    jobs[job_id] = "PROCESSING"
    
    safe_name = file.filename.replace(" ", "_")
    input_path = os.path.join(BASE_DIR, f"{job_id}_{safe_name}")
    folder_name = input_path.split(os.sep)[-1].rsplit('.', 1)[0]
    
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    background_tasks.add_task(process_audio, job_id, input_path, targets, folder_name)
    return {"job_id": job_id}

@app.get("/status/{job_id}")
async def check_status(job_id: str):
    return {"status": jobs.get(job_id, "NOT_FOUND")}

@app.get("/download/{job_id}")
async def download_result(job_id: str):
    zip_path = os.path.join(BASE_DIR, f"{job_id}_stems.zip")
    if os.path.exists(zip_path):
        return FileResponse(zip_path, media_type="application/zip", filename="stems.zip")
    return {"error": "File not found"}
