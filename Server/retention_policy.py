import eventlet
from datetime import datetime, timedelta
from database import db, Message

def run_retention_policy(app):
    """Background task to delete expired and older delivered messages."""
    with app.app_context():
        while True:
            try:
                # 1. Calculate the 7-hour cutoff for standard delivered messages (using utcnow)
                seven_hours_ago = datetime.utcnow() - timedelta(hours=7)
                
                # 2. Get the current local time string for del_time comparisons (using now)
                current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Find messages that are delivered AND older than 7 hours
                expired_delivered = Message.query.filter(
                    Message.delivered == True,
                    Message.timestamp < seven_hours_ago
                ).all()

                # Find messages that have a del_time set AND have passed that time
                expired_del_time = Message.query.filter(
                    Message.del_time != None,
                    Message.del_time < current_time_str
                ).all()

                # Combine both lists and use a set to avoid duplicate deletions 
                # (in case a message matches both conditions)
                messages_to_delete = set(expired_delivered + expired_del_time)

                if messages_to_delete:
                    for msg in messages_to_delete:
                        db.session.delete(msg)
                    
                    db.session.commit()
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Retention Policy: Swept and deleted {len(messages_to_delete)} messages.")

            except Exception as e:
                db.session.rollback()
                print(f"Retention Policy Database Error: {str(e)}")

            # Sleep for 60 seconds before checking again
            eventlet.sleep(60)

def start_retention_worker(app):
    """Spawns the background task via eventlet."""
    print("Starting background message retention worker...")
    eventlet.spawn(run_retention_policy, app)