from messaging import Message
#from network import Client_API
import threading
import time
import curses
import sys

def main(stdscr):

    ui = UI(stdscr)
    while True:
        loggedIn = False
        #connection = Client_API()

        #Log in interface
        ui.drawMenu(loggedIn)
        ui.setTitle("Welcome to happy chat!")
        while not loggedIn:
        
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
                        break
                    ui.showFeedback("Password incorrect. Please try again.")
                loggedIn = True

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
                        ui.showFeedback("Passwords match.\n")
                        break
                    ui.showFeedback("Passwords do not match. Please try again.\n")
                #registering account...
                ui.showFeedback("Account registered successfully. You may now log in.\n")
            elif userInput == 3:
                sys.exit(0)

        #User account interface
        status = Status("senderEmail")
        expiryChecker = threading.Thread(target=checkIfExpired, args=(status, ui))
        expiryChecker.start()
        ui.drawMenu(loggedIn)
        ui.showFeedback("Logged In")
        while loggedIn:
            #print message
            userInput = ui.getInteger("Enter: ",5)
            #Select friend
            if userInput == 1:
                status.readFriends()
                ui.displayFriend(status.friends)
                if len(status.friends) == 0:
                    ui.showFeedback("You have no friends at the moment. Send friend request to invite them.\n")
                    continue
                userInput = ui.getInteger("Select friend: ",len(status.friends)+1)
                status.recipent = status.friends[userInput-1]
                status.updateMsgBuffer(0)
                ui.setTitle(f"Chatroom with {status.recipent}")
                ui.displayMessage(status.msg_buff)
                
            #Send message
            elif userInput == 2:
                if status.recipent == None:
                    ui.showFeedback("Please select the recipent first.\n")
                    continue
                content = ui.getString("Enter message: ")
                msg = Message(content, status.sender, status.recipent)
                #Modify message buffer...
                #send the message out...
                ui.showFeedback(f"Message sent to user: {status.recipent}.\n")

            #Send friend request
            elif userInput == 3:
                while True:
                    name = ui.getString("Send friend request with the email of the user: ")
                    if True: #if email is valid
                        break
                #Send friend request to server
                ui.showFeedback(f"Friend request sent to user: {name}.\n")

            #Log out
            elif userInput == 4:
                loggedIn = False  
                status.alive = False
                expiryChecker.join()
                status = None
                ui.clearMsgWindow()
                ui.showFeedback("Logged out.\n")
                break

class Status:
    
    def __init__(self, sender: str):
        self.alive = True
        self.sender = sender
        self.recipent = None
        self.friends = []
        self.msg_buff:Message = []

        #Testing Data
        self.friends.append("Alice")
        self.friends.append("Bob")
        msg1 =Message("Hey Alice.","Sender","Alice")
        msg2 =Message("Yes? ","Alice","Sender")
        self.msg_buff.append(msg1)
        self.msg_buff.append(msg2)

    def printMessage(self):
        for msg in self.msg_buff:
            print(f"{msg.sender}: {msg.content}")

    def printFriends(self):
        count = 1
        for frd in self.friends:
            print(f"{count}. {frd}")
            count+=1

    def updateMsgBuffer(self, index):
        #fetch messages from server
        ...

    def readFriends(self):
        #read friends from file
        ...


class UI:
    loginMenu = "Menu: 1. Log in | 2. Register | 3. Exit program"
    userMenu = "Menu: 1. Select friends | 2. Send message | 3. Send friend request | 4. Log out"

    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(1)  #Show cursor
        curses.echo()       #Show user typing: on

        self.h, self.w = stdscr.getmaxyx() #Get height(row) and width(col) of terminal

        """
        Message window: Responsible for displaying user messages and friend lists
        Line 0: Title of chatroom
        Line 1-10: Messages between the user and the recipent
        Line >=11: Friend lists

        Input window: Responsible for displaying input prompt, UI feedback and the menu
        Line 0: Dividing line
        Line 1: Feedback line
        Line 2: Menu line
        Line 3: Input line
        """
        # Create windows
        self.msg_win = curses.newwin(self.h - 4, self.w, 0, 0)   # Top: Display chatroom
        self.input_win = curses.newwin(4, self.w, self.h - 4, 0) # Bottom: Input window: input, menu, error
        
        self.msg_win.scrollok(True) #Scrolling = True

        # Divider line
        self.input_win.hline(0, 0, curses.ACS_HLINE, self.w)

        # Refresh
        self.input_win.refresh()
        self.msg_win.refresh()

    def displayMessage(self, messages):
        #Display messages in line 1 to 10
        for i in range(len(messages)):
            self.msg_win.addstr(i+1, 0, f"{messages[i].sender}: {messages[i].message}")
            self.msg_win.clrtoeol()
        #This part is needed if the messages size could be smaller than 10
        for i in range(len(messages)+1, 11):
            self.msg_win.move(i, 0)
            self.msg_win.clrtoeol()
        self.msg_win.refresh()

    def displayFriend(self, friends):
        #Display friend list at 11 and following lines
        self.msg_win.addstr(11, 0, "Friend lists: ")
        self.msg_win.clrtoeol()
        for i in range(1, len(friends)+1):
            self.msg_win.addstr(i+11, 0, f"{i}: {friends[i-1]}")
            self.msg_win.clrtoeol()
        self.msg_win.refresh()

    def setTitle(self, title):
        #Set the title of the feedback message in the first line of message window
        self.msg_win.addstr(0, 0, title)
        self.msg_win.clrtoeol()
        self.msg_win.refresh()

    def clearMsgWindow(self):
        self.msg_win.clear()
        self.msg_win.refresh()

    def showFeedback(self, feedback):
        #Display the feedback message in the line 1 of input window.
        self.input_win.addstr(1, 0, feedback)
        self.input_win.clrtoeol()
        self.input_win.refresh()

    def clearFeedback(self):
        self.input_win.move(1,0)
        self.input_win.clrtoeol()
        self.input_win.refresh()

    def drawMenu(self, loggedIn):
        #Display the menu in the line 2 of input window.
        menu = UI.userMenu if loggedIn else UI.loginMenu
        self.input_win.addstr(2, 0, menu)
        self.input_win.refresh()

    def getInteger(self, inputMessage, limit):
        #Display the input prompt in the line 3 of input window
        self.input_win.addstr(3, 0, inputMessage)
        y, x = self.input_win.getyx()
        self.input_win.refresh()
        valid = False
        while not valid:
            self.input_win.clrtoeol()
            self.input_win.refresh()
            try:
                userInput = int(self.input_win.getstr().decode())
            except ValueError:
                self.showFeedback("Invalid input. Please try again.")
                self.input_win.move(y, x) 
                continue
            #read only positive integer within the range
            if userInput>=limit or userInput<1:
                self.showFeedback("Invalid input. Please try again.")
                self.input_win.move(y, x) 
                continue
            valid = True
            self.clearFeedback()

        return userInput

    def getString(self, inputMessage):
        self.input_win.addstr(3, 0, inputMessage)
        self.input_win.clrtoeol()
        self.input_win.refresh()
        return  self.input_win.getstr().decode()

    def getPassword(self, inputMessage):
        curses.noecho()
        userInput = self.getString(inputMessage)
        curses.echo()
        return userInput


def checkIfExpired(status: Status, ui: UI):
        while status.alive:
            for i in range(len(status.msg_buff)-1, -1, -1):
                if status.msg_buff[i].isExpired():
                    del status.msg_buff[i]
                    ui.displayMessages(status.message)
            time.sleep(1)

if __name__ == "__main__":
    curses.wrapper(main)
