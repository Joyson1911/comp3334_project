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
from typing import List

def main(stdscr):

    ui = UI(stdscr)
    while True:

        #Establish connection with server    
        api = Client_API("http://localhost:3000")
        api.connect()

        #Load login page
        storage = SecureStorage()
        storage.initiate()

        account = login(ui, api, storage)       
            
        
        pageInfo = {"currentPage": "contact"}
        conversation = {"currentChat": None, "messageList": None, "page": None}
        #Check buffer
        api.receiveBuffer = account.receiveBuffer
        stop_event = threading.Event()
        bufferReader = threading.Thread(target=messageReader, args=(ui, account.receiveBuffer, pageInfo))
        bufferReader.start()

        while True:
            ui.clearMsgWindow()
            if pageInfo["currentPage"]=="contact":
                pageInfo = contactPage(ui, account, storage)

            elif pageInfo["currentPage"]=="chatroom":
                pageInfo = chatroomPage(ui, account, pageInfo["recipent"], storage)

            elif pageInfo["currentPage"]=="relationship":
                pageInfo = relationshipPage(ui, account, api)

            elif pageInfo["currentPage"]=="request":
                pageInfo = requestPage(ui, account, api)

            elif pageInfo["currentPage"]=="logout":
                ui.showFeedback("Logging out...")
                #End thread
                stop_event.set()
                messageReader.join()

                for i in range(len(account.friendlist["friends"])):
                    storage.set_unread_count(account.friendlist["friends"][i], account.friendlist["unread"][i])
                account = None

                api.logout()
                break
            elif pageInfo["currentPage"]=="exit":
                ui.showFeedback("Cleaning resource...")
                #End thread
                stop_event.set()
                bufferReader.join()

                for i in range(len(account.friendlist["friends"])):
                    storage.set_unread_count(account.friendlist["friends"][i], account.friendlist["unread"][i])
                account = None
                
                api.disconnect()
                sys.exit(0)

#The login page
def loginPage(ui: UI, api: Client_API, storage: SecureStorage):
    ui.setTitle("Welcome to happy chat!")
    ui.drawMenu("Menu: 1. Log in | 2. Register | 3. Exit program")
    registerLockExpiry = datetime.now()
    while True:
        userInput = ui.getInteger("Enter: ", 4)
        if userInput == 1:
            email = ui.getString("Email: ")
            #Request OTP from server
            otp_result = api.otp_request(email, "login")
            if not otp_result.get("success"):
                ui.showFeedback("Server failed to sent verification code. Please retry.")
                continue
            otp = str(otp_result.get("otp"))
            ui.showFeedback("Verification code sent to your email.")
            #Read password and verification code
            verCode = ui.getString("Verification Code: ")
            password = ui.getPassword("Password: ")
            if verCode != otp:
                ui.showFeedback("Login failed. Incorrect verification code.")
                continue
            login_result = api.login(None, email, password, verCode)
            if not login_result.get("success"):
                ui.showFeedback(f"Login failed. {login_result.get("error")}")
                continue
            
            #Build user session 
            token = login_result.get("token")
            friends = login_result.get("friends_list")
            blacklist = login_result.get("block_list")
            unread = []
            for frd in friends:
                unread.append(storage.get_unread_count(frd))
            account = Account(email, friends, unread, blacklist, token)
            
            return account

        elif userInput == 2:
            if datetime.now() < registerLockExpiry:
                ui.showFeedback(f"Registration locked. Please try again in {(registerLockExpiry - datetime.now()).total_seconds()} seconds.") 
                continue
            email = ui.getString("Email: ")
            #Request otp from server
            otp_result = api.otp_request(email, "register")
            if not otp_result.get("success"):
                ui.showFeedback("Server failed to sent verification code. Please retry.")
                continue
            otp = str(otp_result.get("otp"))
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

def login(ui: UI, api: Client_API, storage: SecureStorage):
        try: 
            token = storage.client_info.token
            if token == None:
                raise Exception("Auto login failed.")
            #try auto login
            
            login_result = api.login(token, None, None, None)
            if  login_result.get("success")==False:
                raise Exception("Auto login failed.")
            userEmail = storage.client_info.last_email
            token = login_result.get("token")
            friends = login_result.get("friends_list")
            blacklist = login_result.get("blacklist")
            unread = []
            for frd in friends:
                unread.append(storage.get_unread_count(frd))
            account = Account(userEmail, friends, unread, blacklist, token)
            return account
        except Exception as e:
            account = loginPage(ui, api, storage)
            return account
   

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
            return {"currentPage":"chatroom", "recipent": account.friendlist["friends"][userInput-1]}
        elif userInput == 2:
            return {"currentPage":"relationship"}
        elif userInput == 3:
            #Clear token
            return {"currentPage":"logout"}
        elif userInput == 4:
            #set token
            userInput = ui.getInteger("Are you sure to exit without logging out? Yes(1)/No(2): ", 3)
            if userInput == 2:
                continue
            return {"currentPage":"exit"}

def chatroomPage(ui: UI, account: Account, recipientEmail: str, storage: SecureStorage, conversation: dict, api: Client_API):
    recipientKey =  storage.get_public_key(recipientEmail)
    latestKey = api.get_public_key(recipientEmail)
    if latestKey!=recipientKey:
        ui.showFeedback("WARNING: This user has switched to a new device. Are you sure to continue?")
        userInput = ui.getInteger("Continue with warning(1), Leave the chatroom(2): ", 3)
        if userInput == 2:
            return {"currentPage": "contact"}
        
    #storage.save_public_key(recipientEmail, latestKey)
    account.friendlist["unread"][account.friendlist["friends"].index(recipientEmail)] = 0
    page = [1]
    messages = storage.load_chat_msg(recipientEmail)
    lifetime = -1

    #Set thread for checking message expiry
    stop_event = threading.Event()
    expiryChecker = threading.Thread(target=checkIfExpired, args=(ui, messages, page))
    expiryChecker.start()

    conversation["currentChat"]=recipientEmail
    conversation["messageList"]=messages
    conversation["page"]=page[0]
    ui.drawMenu("Menu: 1. Send message | 2. Set message lifetime | 3. Remove message lifetime  | 4. Last page | 5. Next page | 6. Return to contacts")
    ui.displayMessage.messages[-page*10-1:-(page-1)*10-1]
    while True:
        ui.setTitle(f"Chatroom with {recipientEmail}: Page {page+1}")
        userInput = ui.getInteger("Enter: ", 7)
        if userInput == 1:
            content = ui.getString("Enter message: ")
            msg = Message(content, account.user, recipientEmail, lifetime)
            #Ask server for ID
            messages.append(msg)
            ui.displayMessage(messages[page*10:page*10+10])
        elif userInput == 2:
            ui.showFeedback("Units of message lifetime are s(second), m(minute) and h(hour). Min: 30s, Max: 24h")
            life = ui.getTime("Enter message lifetime: ")
        elif userInput == 3:
            lifetime = -1
        elif userInput == 4:
            page[0]-=1
            ui.displayMessage(messages[page*10:page*10+10])
        elif userInput == 5:
            page[0]+=1
            ui.displayMessage(messages[page*10:page*10+10])
        elif userInput == 6:
            ret = {"currentPage": "contact"}
            break

    stop_event.set()
    expiryChecker.join()
    storage.write_chat_msg(recipientEmail, messages)
    return ret

def relationshipPage(ui: UI, account: Account, api: Client_API):
    ui.setTitle("Manage your contacts: ")
    ui.displayFriend(account.friendlist["friends"], account.friendlist["unread"])
    ui.drawMenu("Menu: 1. Send friend request | 2. Unfriend user | 3. Block user | 4. Check request | 5. Return to contacts")
    while True:
        userInput = ui.getInteger("Enter: ", 6)
        if userInput == 1:
            userInput = ui.getString("Enter user email: ")
            send_result = api.send_friend_request(userInput)
            
            if not send_result["success"]: #if user does not exist
                ui.showFeedback(send_result.get("error"))
                continue
            ui.showFeedback(f"Friend request sent to {userInput}")
        elif userInput == 2:
            if len(account.friendlist["friends"])<1:
                ui.showFeedback("You have no friends at the moment.")
                continue
            userInput = ui.getString("Enter user email: ")
            if userInput not in account.friendlist["friends"]: # user does not exist in friend list
                ui.showFeedback("The user is not in your friend list.")
                continue
            unfrd_result = api.unfriend_request(userInput, "remove")
            if not unfrd_result.get("success"):
                ui.showFeedback(f"Failed to unfriend. {unfrd_result.get("error")}")
                continue
            account.friendlist["friends"].remove(userInput)
            ui.showFeedback(f"Removed user: {userInput} from your friends list.")
        elif userInput == 3:
            userInput = ui.getString("Enter user email: ")

            block_result = api.unfriend_request(userInput, "block")
            if not block_result.get("success"): # user does not exist
                ui.showFeedback(block_result.get("error"))
                continue
            account.blacklistUser(userInput)
            ui.showFeedback(f"Blocked user: {userInput}.")
        elif userInput == 4:
            return {"currentPage": "request"}
        elif userInput == 5:
            return  {"currentPage": "contact"}

def requestPage(ui: UI, account: Account, api: Client_API):
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
            return {"currentPage": "relationship"}

def checkIfExpired(ui: UI, messages, page):
        while not stop_event.is_set():
            for i in range(len(messages)-1, -1, -1):
                if messages[i].isExpired():
                    del messages[i]
                    ui.displayMessages(messages)
            time.sleep(1)

def messageReader(ui: UI, receiveBuffer: List[dict], pageInfo: dict, account: Account, conversation: dict):
    #constantly checking some message buffer, or triggered by a message arrival event
    while not stop_event.is_set():
        while len(receiveBuffer)>1:
            #Read the first message
            packet = receiveBuffer[0]
            if packet["type"]=="message":
                msg = packet["content"]
                friend = msg.sender if msg.receiver==account.user else msg.receiver
                if conversation["currentChat"]==friend:
                    conversation["messageList"].append(msg)
                    page = conversation["page"]
                    ui.displayMessage.messages[-page*10-1:-(page-1)*10-1]
                else:
                    #write message to file
                    account.friendlist["unread"][account.friendlist["friends"].index(friend)]+=1
                    if pageInfo["currentPage"]=="contact":
                        ui.displayFriend(account.friendlist["friends"], account.friendlist["unread"])

            elif packet["type"]=="request":
                if packet["sender"]==account.user:
                    account.addSentRequest(packet["receiver"])
                else:
                    account.addRcvdRequest(packet["sender"])

                if pageInfo["currentPage"]=="request":
                    ui.displayRequest(account.request["sent"], account.request["received"])

            elif packet["type"]=="response":
                if packet["accepted"]:
                    account.addFriend(account.request["sent"].index(packet["sender"]))
                else: 
                    account.removeFriend(account.request["sent"].index(packet["sender"]))
                #Update relationship page at real time
                if pageInfo["currentPage"]=="relationship":
                    ui.displayFriend(account.friendlist["friends"], account.friendlist["unread"])

            receiveBuffer.pop(0)

if __name__ == "__main__":
    curses.wrapper(main)
