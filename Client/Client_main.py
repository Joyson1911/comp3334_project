from messaging import Message
#from network import Client_API
import threading
import time
import sys
import curses
from UserInterface import UI
from enum import Enum

def main(stdscr):

    ui = UI(stdscr)
    while True:

        #Load login page
        user = loginPage(ui)
        ui.clearMsgWindow()
        ui.clearFeedback()
        status = Status(user)
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

class Status:
    
    def __init__(self, sender: str):
        self.sender = sender
        self.recipent = None
        self.friends = ["alice", "bob"]

    def updateMsgBuffer(self, index):
        #fetch messages from server
        ...

    def readFriends(self):
        #read friends from file
        ...

def notificationPage(ui: UI, status: Status):
    ui.setTitle("Notification")
    #print notification
    ...

#The login page
def loginPage(ui: UI):
    ui.setTitle("Welcome to happy chat!")
    ui.drawMenu("Menu: 1. Log in | 2. Register | 3. Exit program")
    while True:
        userInput = ui.getInteger("Enter: ", 4)
        if userInput == 1:
            while True:
                email = ui.getString("Email: ")
                verCode = ui.getString("Verification Code: ")
                if True:# if verCode is correct break
                    ui.showFeedback("Email verified.")
                    break
            while True:
                password = ui.getPassword("Password: ")
                if True: #if password is correct
                    return email
                ui.showFeedback("Password incorrect. Please try again.")

        elif userInput == 2:
            while True:
                email = ui.getString("Email: ")
                #Ask server to send OTP
                verCode = ui.getString("Verfication Code: ")
                if True:#if verCode is correct
                    ui.showFeedback("Email successfully verified.")
                    break
                ui.showFeedback("Verification Code incorrect. Please try again.\n")
            password1 = "1"
            password2 = "2"
            while True:
                password1 = ui.getPassword("Set password: ")
                password2 = ui.getPassword("Enter password again: ")
                if password1 == password2:
                    ui.showFeedback("Passwords match.")
                    break
                ui.showFeedback("Passwords do not match. Please try again.")
            #registering account...
            ui.showFeedback("Account registered successfully. You may now log in.")
        elif userInput == 3:
            sys.exit(0)

#The contact page, a list of chatroom
def contactPage(ui: UI, status: Status):
    ui.setTitle("Contacts:")
    ui.drawMenu("Menu: 1. Enter chatroom | 2. Manage contacts | 3. Log out")
    ui.displayFriend(status.friends)
    #Start thread: check message list until the chat ends
    running = True
    expiryChecker = threading.Thread(target=checkIfExpired, args=(status, ui))
    expiryChecker.start()
    while True:
        userInput = ui.getInteger("Enter: ", 4)
        if userInput == 1:
            if len(status.friends)<1:
                ui.showFeedback("You have no friends at the moment. Add new friends to start a conversation.")
                continue
            recipent = ui.getInteger("Enter chatroom ID: ", len(status.friends)+1)
            result =  {"nextPage":"chatroom", "recipent": status.friends[recipent-1]}
            break
        elif userInput == 2:
            result =  {"nextPage":"relationship"}
            break
        elif userInput == 3:
            result = {"nextPage":"login"}
            break
    #End thread
    running = False
    expiryChecker.join()
    return result

    
def updateMessageBuffer(recipent: str, messageBuffer):
    #fetch 10 messages from server
    ...

#Chatroom page: chatroom between the user and the recipent
def chatroomPage(ui: UI, sender: str, recipent: str):
    ui.setTitle(f"Chatroom with {recipent}")
    ui.drawMenu("Menu: 1. Send message | 2. Set life for messages | 3. Return to contacts")
    messageBuffer = []
    life = -1
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
            return {"nextPage": "contact"}

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
        while running:
            for i in range(len(messages)-1, -1, -1):
                if messages[i].isExpired():
                    del messages[i]
                    ui.displayMessages(messages)
            time.sleep(1)

if __name__ == "__main__":
    curses.wrapper(main)
