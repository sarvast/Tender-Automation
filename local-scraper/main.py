import time
import os
import schedule
from scraper import run_scraper

def execute_pipeline():
    """
    Master orchestrator function that runs the complete tender tracking pipeline locally.
    """
    print("\n" + "="*50)
    print(f"Starting Local GeM Scraper Pipeline at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    try:
        # Step 1: Run the scraper core engine to extract new data and push via HTTP Post
        print("\n>>> Phase 1: Executing Scraper Engine")
        run_scraper()
        print("\nPipeline execution completed successfully.")
             
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Pipeline execution failed: {e}")

if __name__ == "__main__":
    # You can call the function once manually to test
    print("Initializing Auto-Tracker Master Service...")
    
    # Run the pipeline immediately upon startup before entering the schedule loop
    execute_pipeline()
    
    # With ~80+ keywords, one full run takes ~3-4 hours.
    # Schedule next run every 4 hours so runs don't overlap.
    schedule.every(4).hours.do(execute_pipeline)
    
    print("\nScheduler configured. Engine will automatically run every 4 hours.")
    print("Press Ctrl+C to terminate the tracker.")
    
    # Infinite loop to keep the background process alive
    try:
        while True:
            schedule.run_pending()
            time.sleep(1) # Check schedule periodically without maxing out CPU
    except KeyboardInterrupt:
        print("\nGeM Auto-Tracker shut down gracefully by user.")
