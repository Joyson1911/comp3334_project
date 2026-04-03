from messaging import Message
from network import Client_API
import threading
import time
import sys
import curses
from UserInterface import UI
from storage import SecureStorage
from session import Account, Recipient
from datetime import datetime, timedelta
from network import Client_API
from crypto import RSA

def main(stdscr):

    ui = UI(stdscr)
    api.connect()
    while True:

        #Establish connection with server    
        api = Client_API("http://localhost:3000")
        api.connect()

        #Load login page
        storage = SecureStorage()
        storage.initiate()

        
        try: 
            token = storage.client_info.token
            #...

        except Exception as e:

            userEmail = loginPage(ui, api)
        finally:
            #read frd list
            ...
        #Check buffer
        receiveBuffer = []
        stop_event = threading.Event()
        bufferReader = threading.Thread(target=messageReader, args=(ui, receiveBuffer))
        bufferReader.start()

        #Account
        friends = []
        unread = []
        blacklist = []
        publicKey = ""
        privateKey = ""
        sent = []
        received = []

        account = Account(userEmail, friends, unread, blacklist, sent, received)
        #Load contact page
        pageInfo = {"nextPage": "contact"}
        while True:
            ui.clearMsgWindow()
            if pageInfo["nextPage"]=="contact":
                pageInfo = contactPage(ui, account)

            elif pageInfo["nextPage"]=="chatroom":
                pageInfo = chatroomPage(ui, account.sender, pageInfo["recipent"])

            elif pageInfo["nextPage"]=="relationship":
                pageInfo = relationshipPage(ui, account)

            elif pageInfo["nextPage"]=="request":
                pageInfo = requestPage(ui, account)

            elif pageInfo["nextPage"]=="logout":
                account = None
                stop_event.set()
                messageReader.join()
                break
            elif pageInfo["nextPage"]=="exit":
                account = None
                stop_event.set()
                messageReader.join()
                break

#The login page
def loginPage(ui: UI, api: Client_API):
    ui.setTitle("Welcome to happy chat!")
    ui.drawMenu("Menu: 1. Log in | 2. Register | 3. Exit program")
    registerLockExpiry = datetime.now()
    while True:
        userInput = ui.getInteger("Enter: ", 4)
        if userInput == 1:
            email = ui.getString("Email: ")
            #Request OTP from server
            otp = api.otp_request(email, "login")
            if otp == None:
                ui.showFeedback("Server failed to sent verification code. Please retry.")
                continue
            ui.showFeedback("Verification code sent to your email.")
            #Read password and verification code
            password = ui.getPassword("Password: ")
            verCode = ui.getString("Verification Code: ")

            if verCode != otp:
                ui.showFeedback("Login failed. Incorrect verification code.")
                continue
            login_result = api.login(email, password, verCode)
            if not register_result.get("success"):
                ui.showFeedback(f"Login failed. {login_result.get("error")}")
                continue
            
            return email

        elif userInput == 2:
            if datetime.now() < registerLockExpiry:
                ui.showFeedback(f"Registration locked. Please try again in {(registerLockExpiry - datetime.now()).total_seconds()} seconds.") 
                continue
            email = ui.getString("Email: ")
            #Request otp from server
            otp = api.otp_request(email, "register")
            if otp == None:
                ui.showFeedback("Server failed to sent verification code. Please retry.")
                registerLockExpiry = datetime.now() + timedelta(seconds=60)
                continue
            ui.showFeedback("Verification code sent to your email.")

            verCode = ui.getString("Verification Code: ")
            if verCode != otp:
                ui.showFeedback("Incorrect verification code.")
                continue
            ui.showFeedback("Email verified.")
            while True:
                password1 = ui.getPassword("Set password: ")
                password2 = ui.getPassword("Enter password again: ")
                if password1 == password2:
                    ui.showFeedback("Passwords match.")
                    break
                ui.showFeedback("Passwords do not match. Please try again.")
                
            register_result = api.register(email, password1, verCode)
            if not register_result.get("success"):
                ui.showFeedback(f"Register failed. {register_result.get('error')}")
                registerLockExpiry = datetime.now() + timedelta(seconds=60)
                continue
            ui.showFeedback("Account registered successfully.")
            registerLockExpiry = datetime.now() + timedelta(seconds=60)
        elif userInput == 3:
            sys.exit(0)
        

def contactPage(ui: UI, account: Account, storage: SecureStorage):
    ui.setTitle("Contacts:")
    ui.drawMenu("Menu: 1. Enter chatroom | 2. Manage contacts | 3. Log out | 4. Exit program")
    ui.displayFriend(account.friendlist["friends"], account.friendlist["unread"])

    while True:
        userInput = ui.getInteger("Enter: ", 5)
        if userInput == 1:
            if len(account.friendlist["friends"])<1:
                ui.showFeedback("You have no friends at the moment. Add new friends to start a conversation.")
                continue
            userInput = ui.getInteger("Enter chatroom ID: ", len(account.friendlist["friends"])+1)
            return {"nextPage":"chatroom", "recipent": account.friendlist["friends"][userInput-1]}
        elif userInput == 2:
            return {"nextPage":"relationship"}
        elif userInput == 3:
            return {"nextPage":"logout"}
        elif userInput == 4:
            #Exchange token and 
            return {"nextPage":"exit"}

def getMessages(recipient: str, pageNum: int):
    ...    

def chatroomPage(ui: UI, account: Account, recipientEmail: str, storage: SecureStorage):
    #
    recipientKey =  storage.get_public_key(recipientEmail)
    page = 0
    messageBuffer = storage.load_chat_msg(recipientEmail, page)
    lifetime = -1
    #update message buffer

    #Set thread for checking message expiry
    stop_event = threading.Event()
    expiryChecker = threading.Thread(target=checkIfExpired, args=(ui, messageBuffer))
    expiryChecker.start()

    ui.drawMenu("Menu: 1. Send message | 2. Set message lifetime | 3. Remove message lifetime  | 4. Last page | 5. Next page | 6. Return to contacts")
    while True:
        ui.setTitle(f"Chatroom with {recipientEmail}: Page {page+1}")
        ui.displayMessage(messageBuffer)
        userInput = ui.getInteger("Enter: ", 7)
        if userInput == 1:
            content = ui.getString("Enter message: ")
            msg = Message(content, account.user, recipientEmail, lifetime)
            #Send message to server
            #Update message buffer
        elif userInput == 2:
            ui.showFeedback("Units of message lifetime are s(second), m(minute) and h(hour). Min: 30s, Max: 24h")
            life = ui.getTime("Enter message lifetime: ")
        elif userInput == 3:
            lifetime = -1
        elif userInput == 4:
            ...
        elif userInput == 5:
            ...
        elif userInput == 6:
            ret = {"nextPage": "contact"}
            break

    stop_event.set()
    expiryChecker.join()
    return ret

def relationshipPage(ui: UI, account: Account):
    ui.setTitle("Manage your contacts: ")
    ui.displayFriend(account.friendlist["friends"], account.friendlist["unread"])
    ui.drawMenu("Menu: 1. Send friend request | 2. Unfriend user | 3. Block user | 4. Check request | 5. Return to contacts")
    while True:
        userInput = ui.getInteger("Enter: ", 6)
        if userInput == 1:
            userInput = ui.getString("Enter user email: ")
            #Ask server
            
            send_result = api.send_friend_request(userInput)
            
            if not send_result["success"]: #if user does not exist
                ui.showFeedback("User does not exist.")
                continue
            #Send request
            ui.showFeedback(f"Friend request sent to {userInput}")
        elif userInput == 2:
            if len(account.friendlist["friends"])<1:
                ui.showFeedback("You have no friends at the moment.")
                continue
            userInput = ui.getString("Enter user email: ")
            if userInput not in account.friendlist["friends"]: # user does not exist in friend list
                ui.showFeedback("The user is not in your friend list.")
                continue
            #send server unfrd
            account.friendlist["friends"].remove(userInput)
            ui.showFeedback(f"Removed user: {userInput} from your friends list.")
        elif userInput == 3:
            userInput = ui.getString("Enter user email: ")
            #Ask server
            if False: # user does not exist
                ui.showFeedback("User does not exist.")
                continue
            #send server block
            account.blacklistUser(userInput)
            ui.showFeedback(f"Blocked user: {userInput}.")
        elif userInput == 4:
            return {"nextPage": "request"}
        elif userInput == 5:
            return  {"nextPage": "contact"}

def requestPage(ui: UI, account: Account):
    ui.setTitle("Pending requests:")
    ui.displayRequest(account.request["sent"], account.request["received"])
    ui.drawMenu("Menu: 1. Accept request | 2. Decline request | 3. Cancel request | 4. Return to manage page")
    while True:
        userInput = ui.getInteger("Enter: ", 5)
        if userInput == 1:
            if len(account.request["received"])<1:
                ui.showFeedback("You have no pending friend requests at the moment.")
                continue
            userInput = ui.getInteger("Enter request ID: ", len(account.request["received"])+1)
            #Send accept to server
            account.addFriend(userInput-1)
        elif userInput == 2:
            if len(account.request["received"])<1:
                ui.showFeedback("You have no pending friend requests at the moment.")
                continue
            userInput = ui.getInteger("Enter request ID: ", len(account.request["received"])+1)
            #Send decline to server
            account.removeFriend(userInput-1)
        elif userInput == 3:
            if len(account.request["sent"])<1:
                ui.showFeedback("You have no pending friend requests at the moment.")
                continue
            userInput = ui.getInteger("Enter request ID: ", len(account.request["sent"])+1)
            #Send cancel to server
            account.request["sent"].pop(userInput-1)
        elif userInput == 4:
            return {"nextPage": "relationship"}

def checkIfExpired(ui: UI, messages):
        while not stop_event.is_set():
            for i in range(len(messages)-1, -1, -1):
                if messages[i].isExpired():
                    del messages[i]
                    ui.displayMessages(messages)
            time.sleep(1)

def messageReader(ui: UI, receiveBuffer):
    #constantly checking some message buffer, or triggered by a message arrival event
    while not stop_event.is_set():
        while len(receiveBuffer)>1:
            ui.setTitle(receiveBuffer[0])
            receiveBuffer.pop(0)


if __name__ == "__main__":
    curses.wrapper(main)
