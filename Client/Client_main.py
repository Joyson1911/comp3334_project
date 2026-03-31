from messaging import Message
import os
#from network import Client_API
from getpass import getpass
import threading
import time

class Status:
    
    def __init__(self, sender: str):
        self.alive = True
        self.sender = sender
        self.recipent = None
        self.friends = []
        self.msg_buff: list[Message] = []

    def printMessage(self):
        for msg in self.msg_buff:
            print(f"{msg.sender}: {msg.message}")

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

    def checkIfExpired(self):
        while self.alive:
            for i in range(len(self.msg_buff)-1, -1, -1):
                if self.msg_buff[i].isExpired():
                    del self.msg_buff[i]
            time.sleep(1)

def main():
    
    print("Started")
    running = True

    while running:
        loggedIn = False
        #connection = Client_API()

        #Log in interface
        while not loggedIn:
            print("Select Operation:\n" \
                "1. Login\n" \
                "2. Register\n" \
                "3. Exit program")
            userInput = readInteger(4)

            if userInput == 1:
                while True:
                    email = input("Email Address: ")
                    verCode = input("Verification Code: ")
                    if True:# if verCode is correct break
                        print("Email successfully verified.\n")
                        break
                while True:
                    password = getpass("Password: ")
                    if True: #if password is correct
                        break
                    print("Password incorrect. Please try again.\n")
                print("Logging in...\n")
                loggedIn = True

            elif userInput == 2:
                while True:
                    email = input("Email Address: ")
                    #Ask server to send OTP
                    verCode = input("Verfication Code: ")
                    if True:#if verCode is correct
                        print("Email successfully verified.\n")
                        break
                    print("Verification Code incorrect. Please try again.\n")

                password1 = "1"
                password2 = "2"
                while True:
                    password1 = getpass("Set password: ")
                    password2 = getpass("Enter password again: ")
                    if password1 == password2:
                        print("Passwords match.\n")
                        break
                    print("Passwords do not match. Please try again.\n")
                #registering account...
                print("Account registered successfully. You may now log in.\n")
            elif userInput == 3:
                print("Program ended.\n")
                running = False
                break

        #User account interface
        status = Status("senderEmail")
        expiryChecker = threading.Thread(target=status.checkIfExpired)
        expiryChecker.start()
        print("Logged in")
        while loggedIn:

            status.printMessage()
            print("Select Operation:\n" \
                "1. Select friends\n" \
                "2. Send messages\n" \
                "3. Send friend request\n"\
                "4. Log out")
            
            userInput = readInteger(5)
            #Select friend
            if userInput == 1:
                status.readFriends()
                status.printFriends()
                if len(status.friends) == 0:
                    print("You have no friends at the moment. Send friend request to invite them.\n")
                    continue
                userInput = readInteger(len(status.friends)+1)
                status.recipent = status.friends[userInput-1]
                status.updateMsgBuffer()
                
            #Send message
            elif userInput == 2:
                if status.recipent == None:
                    print("Please select the recipent first.\n")
                    continue
                content = input("Enter message: ")
                msg = Message(content, status.sender, status.recipent)
                #Modify message buffer...
                #send the message out...
                print(f"Message sent to user: {status.recipent}.\n")

            #Send friend request
            elif userInput == 3:
                while True:
                    name = input("Send friend request with the email of the user: ")
                    if True: #if email is valid
                        break
                #Send friend request to server
                print(f"Friend request sent to user: {name}.\n")

            #Log out
            elif userInput == 4:
                loggedIn = False  
                status.alive = False
                expiryChecker.join()
                status = None
                os.system("cls")
                print("Logged out.\n")
                break

#Read an integer in the range from 1 to limit-1
#e.g. read(4) accept input of 1,2,3 only and reject anything else
def readInteger(limit: int):
    valid = False
    while not valid:
        try:
            userInput = int(input("Enter: "))
        except ValueError:
            print("Invalid input. Please try again.\n")
            continue
        #read only positive integer within the range
        if userInput>=limit or userInput<1:
            print("Invalid input. Please try again.\n")
            continue
        valid = True

    return userInput

if __name__ == "__main__":
    main()