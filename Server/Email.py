import smtplib
from common.config import Config



def emailVerification(verCode: int, receiverMailAddress: str):
    Conf = Config.get()
    ADDR = Conf['EMAIL']['address']
    PW = Conf['EMAIL']['password']
    message = "Verification Code: " + str(verCode)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(ADDR, PW)
        server.sendmail(ADDR, receiverMailAddress, message)
    except Exception as e:
        print("Error: failed to send verification code")
    finally:
        server.quit()