import time
import os
import schedule
from scraper import run_scraper
from excel_exporter import sync_latest_bids_to_excel
from notifier import send_email_alert

def execute_pipeline():
    """
    Master orchestrator function that runs the complete tender tracking pipeline.
    """
    print("\n" + "="*50)
    print(f"Starting GeM Scraper Pipeline at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    # Target Excel filename based on our exporter configuration
    excel_filename = "latest_poct_tenders.xlsx"
    
    # Store the modification time of the file BEFORE the sync if it exists
    # This helps us detect if the file was updated during the sync
    last_modified_before = 0
    if os.path.exists(excel_filename):
        last_modified_before = os.path.getmtime(excel_filename)

    try:
        # Step 1: Run the scraper core engine to extract new data
        print("\n>>> Phase 1: Executing Scraper Engine")
        run_scraper()
        
        # Step 2: Sync un-notified raw SQL data to Pandas and export cleanly
        print("\n>>> Phase 2: Syncing data to Excel")
        sync_latest_bids_to_excel()
        
        # Step 3: Check if new Excel file was successfully generated/updated
        print("\n>>> Phase 3: Validating Alert Triggers")
        
        file_updated = False
        if os.path.exists(excel_filename):
            last_modified_after = os.path.getmtime(excel_filename)
            # If the file is newer, or it didn't exist before
            if last_modified_after > last_modified_before:
                file_updated = True
                
        if file_updated:
            print("  New bids detected! Preparing to send email alert...")
            send_email_alert(excel_filename)
        else:
             print("  No new bids synced to Excel. Skipping email alert.")
             
        print("\nPipeline execution completed successfully.")
             
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Pipeline execution failed: {e}")

if __name__ == "__main__":
    # You can call the function once manually to test
    print("Initializing Auto-Tracker Master Service...")
    
    # Note: For production initialization, uncomment this to run immediately upon startup before entering loop
    # execute_pipeline()
    
    # Define the hands-free schedule
    schedule.every(2).hours.do(execute_pipeline)
    
    print("\nScheduler configured. Engine will automatically run every 2 hours.")
    print("Press Ctrl+C to terminate the tracker.")
    
    # Infinite loop to keep the background process alive
    try:
        while True:
            schedule.run_pending()
            time.sleep(1) # Check schedule periodically without maxing out CPU
    except KeyboardInterrupt:
        print("\nGeM Auto-Tracker shut down gracefully by user.")
