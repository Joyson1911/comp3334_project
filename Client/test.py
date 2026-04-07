from datetime import datetime

a = datetime.now()
a = a.strftime("%Y-%m-%d %H:%M:%S") 
a = datetime.strptime(a, "%Y-%m-%d %H:%M:%S")
if isinstance(a, datetime):
    print("This is datetime")