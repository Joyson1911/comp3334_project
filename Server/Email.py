import smtplib
from config import Config
from email.utils import formataddr
from email.message import EmailMessage

def emailVerification(verCode: str, receiverMailAddress: str):
    Conf = Config.get()
    ADDR = Conf['EMAIL']['address']
    PW = Conf['EMAIL']['password']
    message = EmailMessage()
    message['Subject'] = "Your Happy Chat Verification Code"
    message["From"] = formataddr(("Happy Chat", ADDR))
    message['To'] = receiverMailAddress
    message.set_content(f'Your Happy chat code is {verCode}.')
    
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(ADDR, PW)
        server.send_message(message, ADDR, receiverMailAddress)
    except Exception as e:
        print(f"Error: failed to send verification code:\n{e}")
    finally:
        server.quit()