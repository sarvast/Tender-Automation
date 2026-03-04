import os
from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import pandas as pd
from datetime import datetime

from models import SessionLocal, Tender
from excel_exporter import sync_latest_bids_to_excel

app = FastAPI(title="GeM Tender Auto-Tracker")

# Set up templates
templates = Jinja2Templates(directory="templates")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request, db: Session = Depends(get_db)):
    """
    Main dashboard view. Fetches all tenders from SQLite and renders the UI.
    """
    # Fetch all tenders, newest first
    tenders = db.query(Tender).order_by(Tender.bid_end_date.desc()).all()
    
    # Process item_categories if it's stored as JSON list
    for t in tenders:
        if isinstance(t.item_categories, list):
            t.items_str = ", ".join(t.item_categories)
        else:
            t.items_str = t.item_categories if t.item_categories else "N/A"
            
    return templates.TemplateResponse("index.html", {
        "request": request,
        "tenders": tenders,
        "total_tenders": len(tenders),
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.get("/download-excel")
async def download_excel():
    """
    Endpoint that triggers the Excel generation script and returns the file download.
    """
    # Force a sync run to ensure the excel file exists and is up to date
    try:
        sync_latest_bids_to_excel()
    except Exception as e:
        print(f"Error generating fresh excel on download request: {e}")
        
    excel_filename = "latest_poct_tenders.xlsx"
    
    # Check if file exists, if not generate an empty one as fallback
    if not os.path.exists(excel_filename):
        df = pd.DataFrame(columns=['gem_bid_number', 'department_name', 'No Data Found'])
        df.to_excel(excel_filename, index=False)
        
    return FileResponse(
        path=excel_filename, 
        filename=excel_filename,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
