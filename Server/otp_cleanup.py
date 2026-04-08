import eventlet
from datetime import datetime

def start_otp_cleanup(pending_otps_dict):
    """
    Starts a background worker to periodically remove expired OTPs.
    :param pending_otps_dict: Reference to the global pending_otps dictionary.
    """
    def cleanup_loop():
        print("[OTP Retention] Background worker initialized.")
        while True:
            # Check for expired OTPs every 60 seconds
            eventlet.sleep(60)
            
            current_time = datetime.now()
            # Convert keys to list to prevent "dictionary changed size during iteration" error
            emails = list(pending_otps_dict.keys())
            
            expired_count = 0
            for email in emails:
                record = pending_otps_dict.get(email)
                if record:
                    expiry = record.get('expiry')
                    # Delete the record if the current time has passed the expiry time
                    if expiry and current_time > expiry:
                        del pending_otps_dict[email]
                        expired_count += 1
            
            if expired_count > 0:
                print(f"[OTP Retention] Successfully purged {expired_count} expired OTP records.")

    # Spawn the cleanup loop as a non-blocking background greenthread
    eventlet.spawn_n(cleanup_loop)