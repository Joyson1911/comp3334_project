import smtplib

def emailVerification(verCode: int, receiverMailAddress: str):
    message = "Verification Code: " + verCode
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login("comp3334.project.group60@gmail.com", "nqmx mbam rrhe avyc")
        server.sendmail("comp3334.project.group60@gmail.com", receiverMailAddress, message)
    except Exception as e:
        print("Error: failed to send verification code")
    finally:
        server.quit()