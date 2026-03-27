from messaging import Message


def main():
    
    print("Started")

    running = True
    loggedIn = False

    while not loggedIn:
        print("Select Operation:\n" \
              "1. Login\n" \
              "2. Register\n" \
              "3. Exit program")
        
        userInput = readInteger(4)
        if userInput == 1:
            #logging in...
            loggedIn = True
            print("Logged in successfully\n")
        elif userInput == 2:
            #registering account...
            print("Account registered successfully.\n")
            continue
        elif userInput == 3:
            running = False
            break
    
    sender = "SenderMailAddress"
    while running:
        recipent = None
        friends =["Alice","Bob"]
        #readFriends(friends)

        print("Select Operation:\n" \
              "1. Select friends\n" \
              "2. Send messages\n" \
              "3. Send friend request\n"
              "4. Exit program")
        
        userInput = readInteger(5)
        #Select friend
        if userInput == 1:
            count = 1
            for frd in friends:
                print(f"{count}. {frd}")
                count+=1
            userInput = readInteger(len(friends)+1)
            recipent = friends[userInput-1]
            
        #Send message
        elif userInput == 2:
            if recipent == None:
                "Please select the recipent first.\n"
                continue
            content = input("Enter message: ")
            msg = Message(content, sender, recipent)
            #send the message out...
            print("Message sent successfully\n")
        #Send friend request
        elif userInput == 3:
            #Send friend request
            ...
        elif userInput == 4:
            running = False


def readFriends(friends):
    ...

#read an integer in the range from 1 to limit-1
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