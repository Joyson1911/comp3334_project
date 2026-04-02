from messaging import Message
#from network import Client_API
import threading
import time
import sys
import curses
from UserInterface import UI
from storage import SecureStorage
from session import Account, Recipient
from datetime import datetime, timedelta

def main(stdscr):

    ui = UI(stdscr)
    while True:

        #Load login page
        result = loginPage(ui)
        ui.clearMsgWindow()
        ui.clearFeedback()
        status = Status(.....)
        #Load contact page
        result = {"nextPage": "contact"}
        while True:
            ui.clearMsgWindow()
            if result["nextPage"]=="contact":
                result = contactPage(ui, status)

            elif result["nextPage"]=="chatroom":
                result = chatroomPage(ui, status.sender, result["recipent"])

            elif result["nextPage"]=="relationship":
                result = relationshipPage(ui, status)

            elif result["nextPage"]=="request":
                result = requestPage(ui, status)

            elif result["nextPage"]=="login":
                status = None
                break



def notificationPage(ui: UI, status: Status):
    ui.setTitle("Notification")
    #print notification
    ...

#The login page
def loginPage(ui: UI):
    ui.setTitle("Welcome to happy chat!")
    ui.drawMenu("Menu: 1. Log in | 2. Register | 3. Exit program")
    registerLockExpiry = datetime.now()
    while True:
        userInput = ui.getInteger("Enter: ", 4)
        if userInput == 1:
            email = ui.getString("Email: ")
            #ask server to send OTP
            if False: #if email is unregistered
                ui.showFeedback("Login failed. Please enter a valid and registered email.")
                continue
            ui.showFeedback("Verification code sent to your email.")
            password = ui.getPassword("Password: ")
            verCode = ui.getString("Verification Code: ")
            if False: #if password or verCode is incorrect
                ui.showFeedback("Login failed. Verification code incorrect.")
                continue
            #Read local storage and server message
            storage = SecureStorage(email)
            session = Session(user=email, )
            return {"email":email, "session":session}

        elif userInput == 2:
            if datetime.now() < registerLockExpiry:
                ui.showFeedback(f"Registration locked. Please try again in {(registerLockExpiry - datetime.now()).total_seconds} seconds.") 
                continue
            email = ui.getString("Email: ")
            if False:# if email is registered
                ui.showFeedback("Register failed. Please provide an unregistered email.")
                registerLockExpiry = datetime.now() + timedelta(seconds=60)
                continue
            ui.showFeedback("Verification code sent to your email.")
            verCode = ui.getString("Verification Code: ")
            if False: #if verification code is incorrect
                ui.showFeedback("Register failed. Please provide the correct and latest verification code sent.")
                registerLockExpiry = datetime.now() + timedelta(seconds=60)
                continue
            while True:
                password1 = ui.getPassword("Set password: ")
                password2 = ui.getPassword("Enter password again: ")
                if password1 == password2:
                    ui.showFeedback("Passwords match.")
                    break
                ui.showFeedback("Passwords do not match. Please try again.")
            #Send to server
            ui.showFeedback("Account registered successfully.")
            registerLockExpiry = datetime.now() + timedelta(seconds=60)
        elif userInput == 3:
            sys.exit(0)
        
        

#The contact page, a list of chatroom
def contactPage(ui: UI, account: Account):
    ui.setTitle("Contacts:")
    ui.drawMenu("Menu: 1. Enter chatroom | 2. Manage contacts | 3. Log out | 4. Exit program")
    ui.displayFriend(account.friendlist)
    while True:
        userInput = ui.getInteger("Enter: ", 5)
        if userInput == 1:
            if len(account.friendlist)<1:
                ui.showFeedback("You have no friends at the moment. Add new friends to start a conversation.")
                continue
            userInput = ui.getInteger("Enter chatroom ID: ", len(account.friendlist)+1)
            return {"nextPage":"chatroom", "recipent": account.friendlist[userInput-1]}
        elif userInput == 2:
            return {"nextPage":"relationship"}
            break
        elif userInput == 3:
            return {"nextPage":"login"}
            break

    
def updateMessageBuffer(recipent: str, messageBuffer):
    #fetch 10 messages from server
    ...

#Chatroom page: chatroom between the user and the recipent
def chatroomPage(ui: UI, sender: str, recipent: str):
    password = "pw"
    ui.setTitle(f"Chatroom with {recipent}", password)
    ui.drawMenu("Menu: 1. Send message | 2. Set life for messages | 3. Return to contacts")

    storage = SecureStorage(f"{recipent}.enc", )

    messageBuffer = []
    life = -1
    #Set thread for checking message expiry
    running = True
    stop_event = threading.Event()
    expiryChecker = threading.Thread(target=checkIfExpired, args=(ui, running, messageBuffer))
    expiryChecker.start()
    while True:
        if len(messageBuffer)<10:
            updateMessageBuffer(recipent, messageBuffer)
        ui.displayMessage(messageBuffer)
        ui.showFeedback("Page Number: ....")
        userInput = ui.getInteger("Enter: ", 4)
        if userInput == 1:
            content = ui.getString("Enter message: ")
            msg = Message(content, sender, recipent, lifetime=life)
            #Send message to server
            #Update message buffer
        elif userInput == 2:
            ui.showFeedback("Units of message lifetime are s(second), m(minute) and h(hour). Min: 30s, Max: 24h")
            life = ui.getTime("Enter message lifetime: ")
        elif userInput == 3:
            ret = {"nextPage": "contact"}
            break
    running = False
    stop_event.set()
    expiryChecker.join()
    return ret

def relationshipPage(ui: UI, status: Status):
    ui.setTitle("Manage your contacts: ")
    ui.displayFriend(status.friends)
    ui.drawMenu("Menu: 1. Send friend request | 2. Unfriend user | 3. Block user | 4. Check request | 5. Return to contacts")
    while True:
        userInput = ui.getInteger("Enter: ", 6)
        if userInput == 1:
            userInput = ui.getString("Enter user email: ")
            #Ask server
            if False: #if user does not exist
                ui.showFeedback("User does not exist.")
                continue
            #Send request
            ui.showFeedback(f"Friend request sent to {userInput}")
        elif userInput == 2:
            userInput = ui.getString("Enter user email: ")
            if userInput not in status.friends: # user does not exist in friend list
                ui.showFeedback("The user is not in your friend list.")
                continue
            status.friends.remove(userInput)
            ui.showFeedback(f"Removed user: {userInput} from your friends list.")
        elif userInput == 3:
            userInput = ui.getString("Enter user email: ")
            #Ask server
            if False: # user does not exist
                ui.showFeedback("User does not exist")
                continue
            if userInput in status.friends:
                status.friends.remove(userInput)
            ui.showFeedback(f"Blocked user: {userInput}.")
        elif userInput == 4:
            return {"nextPage": "request"}
        elif userInput == 5:
            return  {"nextPage": "contact"}

def requestPage(ui: UI, status: Status):
    ui.setTitle("Friend requests:")
    ui.displayIncomingRequest("")
    ui.displaySentRequest("")
    ui.drawMenu("Menu: 1. Accept request | 2. Decline request | 3. Cancel request | 4. Return to manage page")
    while True:
        userInput = ui.getInteger("Enter: ", 5)
        if userInput == 1:
            ...
        elif userInput == 2:
            ...
        elif userInput == 3:
            ...
        elif userInput == 4:
            return {"nextPage": "relationship"}

def checkIfExpired(ui: UI, running: bool, messages):
        while not stop_event.is_set():
            for i in range(len(messages)-1, -1, -1):
                if messages[i].isExpired():
                    del messages[i]
                    ui.displayMessages(messages)
            time.sleep(1)
                

if __name__ == "__main__":
    curses.wrapper(main)
