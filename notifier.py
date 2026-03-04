import os
import smtplib
from email.message import EmailMessage
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from dotenv import load_dotenv

# Ensure env vars are loaded
load_dotenv()

def send_email_alert(excel_file_path: str):
    """
    Sends an email alert with the generated Excel file attached.
    """
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")
    SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
    RECEIVER_EMAILS = os.getenv("RECEIVER_EMAILS") # Assuming comma-separated

    # Validate configuration
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAILS]):
        print("[Email Alert Error] Missing email configuration in .env file.")
        return

    # Prepare receiver list
    receiver_list = [email.strip() for email in RECEIVER_EMAILS.split(",") if email.strip()]

    # Construct the email professional message
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = ", ".join(receiver_list)
    msg['Subject'] = "GeM Tender Alert: New Bids Matched for POCT/Q-Line"

    # Write a brief HTML/Text body
    body = """
    <html>
      <body>
        <h2>New GeM Tenders Detected!</h2>
        <p>The Auto-Tracker has successfully extracted new bids matching your configured brands and keywords.</p>
        <p>Please find the generated Excel report attached containing the latest parsed opportunities.</p>
        <br>
        <p><i>Automated System Alert</i></p>
      </body>
    </html>
    """
    msg.attach(MIMEText(body, 'html'))

    # Securely attach the .xlsx file
    try:
        if os.path.exists(excel_file_path):
            with open(excel_file_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            
            # Encode file in base64
            encoders.encode_base64(part)
            
            # Add header with pdf name
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {os.path.basename(excel_file_path)}"
            )
            msg.attach(part)
            print(f"  Successfully attached '{os.path.basename(excel_file_path)}'")
        else:
            print(f"[Email Alert Warning] Attachment '{excel_file_path}' not found. Sending email without it.")
    except Exception as e:
         print(f"[Email Alert Error] Could not attach file: {e}")

    # Connect to the SMTP server and send the email
    try:
        print(f"Connecting to SMTP server ({SMTP_SERVER}:{SMTP_PORT})...")
        # Starting connection
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls() # Secure the connection
        
        # Login
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        # Send
        server.send_message(msg)
        print(f"Alert email sent successfully to: {receiver_list}")
        
    except Exception as e:
        print(f"[Email Alert Error] Failed to send email: {e}")
    finally:
        try:
            server.quit()
        except:
            pass

if __name__ == "__main__":
    # Test block
    send_email_alert("latest_poct_tenders.xlsx")
