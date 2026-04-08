from messaging import Message
from network import Client_API
import threading
import time
import sys
import curses
from UserInterface import UI
from storage import SecureStorage
from session import Account, getMacAddress
from datetime import datetime, timedelta
from network import Client_API
from crypto import RSA, SHA256
from typing import List
import re

def main(stdscr):

    ui = UI(stdscr)
    while True:

        #Establish connection with server    
        api = Client_API()
        api.connect()

        #Load login page
        storage = SecureStorage()
        storage.initiate()

        pageInfo = {"currentPage": "login"}
        account = login(ui, api, storage)
        storage.set_email(account.user)
        
        
        
        conversation = {"currentChat": None, "messageList": None, "page": None}
        #Check buffer
        stop_event = threading.Event()
        bufferReader = threading.Thread(target=messageReader, args=(ui, api.receiveBuffer, pageInfo, account, conversation, stop_event, storage))
        bufferReader.start()

        #Handle unexpected termination of the process
        pageInfo["currentPage"] = "contact"
        while True:
            ui.clearMsgWindow()
            if pageInfo["currentPage"]=="contact":
                contactPage(ui, account, storage, api, pageInfo, conversation)

            elif pageInfo["currentPage"]=="chatroom":
                chatroomPage(ui, account, storage, conversation, api, pageInfo)

            elif pageInfo["currentPage"]=="relationship":
                relationshipPage(ui, account, api, pageInfo)

            elif pageInfo["currentPage"]=="request":
                requestPage(ui, account, api, pageInfo)

            elif pageInfo["currentPage"]=="logout":
                ui.showFeedback("Logging out...")
                #End thread
                stop_event.set()
                bufferReader.join()

                for i in range(len(account.friendlist["friends"])):
                    storage.set_unread_count(account.friendlist["friends"][i], account.friendlist["unread"][i])
                account = None

                api.logout()
                ui.showFeedback("Logged out.")
                break
            elif pageInfo["currentPage"]=="exit":
                ui.showFeedback("Cleaning resource...")
                #End thread
                stop_event.set()
                bufferReader.join()

                storage.update_session(account.token, account.user)
                for i in range(len(account.friendlist["friends"])):
                    storage.set_unread_count(account.friendlist["friends"][i], account.friendlist["unread"][i])
                account = None
                storage.save_client_info()

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
            email = email.strip().lower()
            if not isValidEmail(email):
                ui.showFeedback("Invalid email. Please try again.")
                continue
            #Request OTP from server
            otp_result = api.otp_request(email, "login")
            if not otp_result.get("success"):
                ui.showFeedback(otp_result.get("error"))
                continue
            # otp = str(otp_result.get("otp"))
            ui.showFeedback("Verification code sent to your email.")
            #Read password and verification code
            verCode = ui.getString("Verification Code: ")
            password = ui.getPassword("Password: ")
            if not password:
                ui.showFeedback("Password can not be empty.")
                continue
            ## if verCode != otp:
            ##     ui.showFeedback("Login failed. Incorrect verification code.")
            ##     continue
            digest = SHA256.compute(password, email)
            login_result = api.login(None, email, digest, verCode, getMacAddress(), storage.client_info.rsa.pub_key_str())
            if not login_result.get("success"):
                ui.showFeedback(f"Login failed. {login_result.get("error")}")
                continue
            
            #Build user session 
            storage.set_email(email)
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
            email = email.strip().lower()
            if not isValidEmail(email):
                ui.showFeedback("Invalid email. Please try again.")
                continue
            #Request otp from server
            otp_result = api.otp_request(email, "register")
            if not otp_result.get("success"):
                ui.showFeedback(otp_result.get("error"))
                continue
            # otp = str(otp_result.get("otp"))
            ui.showFeedback("Verification code sent to your email.")
            verCode = ui.getString("Verification Code: ")
            ## if verCode != otp:
            ##     ui.showFeedback("Incorrect verification code.")
            ##     continue
            ## ui.showFeedback("Email verified.")
            while True:
                password1 = ui.getPassword("Set password: ")
                if not isValidPassword(password1):
                    ui.showFeedback("Password must has a length between 12 to 64, with characters of both cases, digit and special character.")
                    continue
                password2 = ui.getPassword("Enter password again: ")
                if password1 == password2:
                    ui.showFeedback("Passwords match.")
                    break
                
                ui.showFeedback("Passwords do not match. Please try again.")
                
            digest = SHA256.compute(password1, email)
            register_result = api.register(email, digest, verCode)
            if not register_result.get("success"):
                ui.showFeedback(f"Register failed. {register_result.get('error')}")
                registerLockExpiry = datetime.now() + timedelta(seconds=60)
                continue
            storage.set_email(email)
            ui.showFeedback("Account registered successfully.")
            registerLockExpiry = datetime.now() + timedelta(seconds=60)
        elif userInput == 3:
            sys.exit(0)

def login(ui: UI, api: Client_API, storage: SecureStorage):
        try: 
            token = storage.client_info.token
            #token = ui.getString("Enter token: ")
            if token == None:
                raise Exception("Auto login failed.")
            #try auto login
            login_result = api.login(token, None, None, None, getMacAddress(), storage.client_info.rsa.pub_key_str())
            if  login_result.get("success")==False:
                raise Exception("Auto login failed.")
            
            userEmail = storage.client_info.last_email
            storage.set_email(userEmail)
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
   

def contactPage(ui: UI, account: Account, storage: SecureStorage, api: Client_API, pageInfo: dict, conversation: dict):
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

            messages = storage.load_chat_msg(account.friendlist["friends"][userInput-1])
            conversation["currentChat"]=account.friendlist["friends"][userInput-1]
            conversation["messageList"]=messages
            pageInfo["currentPage"] = "chatroom"
            return
        elif userInput == 2:
            pageInfo["currentPage"] = "relationship"
            return
        elif userInput == 3:
            storage.remove_session()
            storage.save_client_info()
            for i in range(len(account.friendlist["friends"])):
                storage.set_unread_count(account.friendlist["friends"][i], account.friendlist["unread"][i])
            api.logout()
            account = None
            pageInfo["currentPage"] = "logout"
            return
        elif userInput == 4:
            userInput = ui.getInteger("Are you sure to exit without logging out? Yes(1)/No(2): ", 3)
            if userInput == 2:
                continue
            pageInfo["currentPage"] = "exit"
            return

def chatroomPage(ui: UI, account: Account, storage: SecureStorage, conversation: dict, api: Client_API, pageInfo: dict):
    recipientEmail = conversation["currentChat"]
    recipientKey =  storage.get_public_key(recipientEmail)
    key_result = api.get_public_key(recipientEmail)
    id_result = api.latest_message_id(recipientEmail)
    pageSize = ui.msgWinSize
    if not id_result.get("success"):
        ui.showFeedback(id_result.get("error"))
        return
    if not key_result.get("success"):
        ui.showFeedback(key_result.get("error"))
        return
    latestKey = key_result.get("public_key")
    if recipientKey!=None and latestKey!=RSA.get_pub_str(recipientKey):
        ui.showFeedback("WARNING: This user has switched to a new device. Are you sure to continue?")
        userInput = ui.getInteger("Continue with warning(1), Leave the chatroom(2): ", 3)
        if userInput == 2:
            storage.write_chat_msg(recipientEmail, conversation["messageList"])
            pageInfo["currentPage"] = "contact"
            conversation["messageList"] = None
            conversation["currentChat"] = None
            return
        
    latestID = id_result.get("latest_message_id")
    storage.save_public_key(recipientEmail, RSA.read_pub_key(latestKey))
    account.clearUnread(recipientEmail)
    lifetime = None
    page = [1]
    conversation["page"] = page[0]
    messages = conversation["messageList"]
    for i in range(len(messages) - 1, -1, -1):
        
        if latestID >= messages[i].id:

            while i >= 0:
                messages[i].delivered = True
                i -= 1
            break

    #Set thread for checking message expiry
    stop_event = threading.Event()
    expiryChecker = threading.Thread(target=checkIfExpired, args=(ui, messages, stop_event, conversation))
    expiryChecker.start()
    end = len(messages)- ((page [0]- 1) * pageSize)
    start = max(0, end - pageSize)
    ui.displayMessage(messages[start:end])
    while True:
        ui.drawMenu("Menu: 1. Send message | 2. Set message lifetime | 3. Remove message lifetime  | 4. Last page | 5. Next page | 6. Return to contacts")
        end = len(messages)- ((page [0]- 1) * pageSize)
        start = max(0, end - pageSize)
        ui.setTitle(f"Chatroom with {recipientEmail}: Page {page[0]}")
        userInput = ui.getInteger("Enter: ", 7)
        if userInput == 1:
            content = ui.getString("Enter message: ")
            if not content:
                ui.showFeedback("You can not send an empty message.")
                continue
            msg = Message(None, content, account.user, recipientEmail, None, None)
            cipher = RSA.encrypt_msg(msg.message.encode(), latestKey)
            send_result = api.send_message(recipientEmail, cipher, None if lifetime==None else (datetime.now()+timedelta(seconds=lifetime)).strftime("%Y-%m-%d %H:%M:%S"))
            if not send_result.get("success"):
                ui.showFeedback(send_result.get("error"))
                continue
            msg.delivered = send_result.get("delivered")
            msg.id = send_result.get("message_id")
            msg.delete_time = send_result.get("del_time")
            messages.append(msg)
            end = len(messages)- ((page [0]- 1) * pageSize)
            start = max(0, end - pageSize)
            ui.displayMessage(messages[start:end])
        elif userInput == 2:
            ui.showFeedback("Units of message lifetime are s(second), m(minute) and h(hour). Min: 30s, Max: 24h")
            lifetime = ui.getTime("Enter message lifetime: ")
        elif userInput == 3:
            lifetime = None
        elif userInput == 4:
            if page[0]==1:
                ui.showFeedback("You are at the first page.")
                continue
            page[0]-=1
            end = len(messages)- ((page [0]- 1) * pageSize)
            start = max(0, end - pageSize)
            ui.displayMessage(messages[start:end])
        elif userInput == 5:
            if page[0] >= (len(messages) + pageSize-1) // pageSize:
                ui.showFeedback("You are at the last page.")
                continue
            page[0]+=1
            end = len(messages)- ((page [0]- 1) * pageSize)
            start = max(0, end - pageSize)
            ui.displayMessage(messages[start:end])
        elif userInput == 6:
            storage.write_chat_msg(recipientEmail, messages)
            pageInfo["currentPage"] = "contact"
            conversation["currentChat"] = None
            conversation["messageList"] = None
            conversation["page"] = None
            break

    stop_event.set()
    expiryChecker.join()
    storage.write_chat_msg(recipientEmail, messages)
    return

def relationshipPage(ui: UI, account: Account, api: Client_API, pageInfo: dict):
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
            account.addSentRequest(userInput)
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
            account.removeFriend(userInput)
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
            pageInfo["currentPage"] = "request"
            return
        elif userInput == 5:
            pageInfo["currentPage"] = "contact"
            return

def requestPage(ui: UI, account: Account, api: Client_API, pageInfo: dict):
    ui.setTitle("Pending requests:")
    ui.drawMenu("Menu: 1. Accept request | 2. Decline request | 3. Cancel request | 4. Return to manage page")
    while True:
        ui.displayRequest(account.request["sent"], account.request["received"])
        userInput = ui.getInteger("Enter: ", 5)
        if userInput == 1:
            if len(account.request["received"])<1:
                ui.showFeedback("You have no pending friend requests at the moment.")
                continue
            userInput = ui.getInteger("Enter request ID: ", len(account.request["received"])+1)
            accept_result = api.respond_to_friend_request(account.request["received"][userInput-1], "accept")
            if not accept_result.get("success"):
                ui.showFeedback(accept_result.get("error"))
                continue
            account.addFriend(account.request["received"][userInput-1], "received")
            account.removeRcvdRequest(account.request["received"][userInput-1])
        elif userInput == 2:
            if len(account.request["received"])<1:
                ui.showFeedback("You have no pending friend requests at the moment.")
                continue
            userInput = ui.getInteger("Enter request ID: ", len(account.request["received"])+1)
            decline_result = api.respond_to_friend_request(account.request["received"][userInput-1], "reject")
            if not decline_result.get("success"):
                ui.showFeedback(decline_result.get("error"))
                continue
            account.removeRcvdRequest(account.request["received"][userInput-1])   
        elif userInput == 3:
            if len(account.request["sent"])<1:
                ui.showFeedback("You have no pending friend requests at the moment.")
                continue
            userInput = ui.getInteger("Enter request ID: ", len(account.request["sent"])+1)
            cancel_result = api.cancel_friend_request(account.friendlist["friends"][userInput-1])
            if not cancel_result.get("success"):
                ui.showFeedback(f"Failed to cancel request. {cancel_result.get("error")}")
                continue
            account.request["sent"].pop(userInput-1)
        elif userInput == 4:
            pageInfo["currentPage"] =  "relationship"
            return

def checkIfExpired(ui: UI, messages: List[Message], stop_event, conversation: dict):
        while not stop_event.is_set():
            for i in range(len(messages)-1, -1, -1):
                if messages[i].isExpired():
                    del messages[i]
                    a = -conversation["page"]*10-1
                    b = len(conversation["messageList"])-10*(conversation["page"]-1)
                    ui.displayMessage(conversation["messageList"][a:b])
            time.sleep(1)
            
def messageReader(ui: UI, receiveBuffer: List[dict], pageInfo: dict, account: Account, conversation: dict, stop_event, storage: SecureStorage):
    #constantly checking some message buffer, or triggered by a message arrival event
    while not stop_event.is_set():
        while len(receiveBuffer)>0:
            #Read the first message
            packet = receiveBuffer[0]
            if packet["type"]=="message":
                msg = packet["content"]
                msg.message = storage.client_info.rsa.decrypt_msg(packet["content"].message).decode()
                friend = msg.sender if msg.recipient==account.user else msg.recipient
                if conversation["currentChat"]==friend:
                    conversation["messageList"].append(msg)
                    a = -conversation["page"]*10-1
                    b = len(conversation["messageList"])-10*(conversation["page"]-1)
                    ui.displayMessage(conversation["messageList"][a:b])
                else:
                    storage.append_msgs(friend, [packet["content"]])
                    account.unreadIncrement(friend)
                    if pageInfo["currentPage"]=="contact":
                        ui.displayFriend(account.friendlist["friends"], account.friendlist["unread"])

                #Update friendlist
                account.moveToFront(friend)

            elif packet["type"]=="request":
                if packet["sender"]==account.user:
                    account.addSentRequest(packet["receiver"])
                else:
                    account.addRcvdRequest(packet["sender"])

                if pageInfo["currentPage"]=="request":
                    ui.displayRequest(account.request["sent"], account.request["received"])
                elif pageInfo["currentPage"]=="contact":
                    ui.displayFriend(account.friendlist["friends"], account.friendlist["unread"])

            elif packet["type"]=="response":
                account.addFriend(packet["sender"], "sent")
                account.removeSentRequest(packet["sender"])
                #Update relationship page at real time
                if pageInfo["currentPage"]=="relationship":
                    ui.displayFriend(account.friendlist["friends"], account.friendlist["unread"])
                elif pageInfo["currentPage"]=="contact":
                    ui.displayFriend(account.friendlist["friends"], account.friendlist["unread"])

            receiveBuffer.pop(0)

def isValidEmail(email: str):

    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if re.match(regex, email):
        return True
    return False

def isValidPassword(password: str) -> bool:

    if not (12 <= len(password) <= 64):
        return False
    
    if not password.isascii():
        return False

    hasLower = re.search(r'[a-z]', password)
    hasUpper = re.search(r'[A-Z]', password)
    hasDigit = re.search(r'\d', password)
    hasSpecial = re.search(r'[^a-zA-Z0-9]', password)

    # Return True only if all conditions are met
    return all([hasLower, hasUpper, hasDigit, hasSpecial])


if __name__ == "__main__":
    curses.wrapper(main)

