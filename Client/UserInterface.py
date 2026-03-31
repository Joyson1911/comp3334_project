import curses

class UI:


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
        #Display messages in line 1 to 10 of the message window
        for i in range(len(messages)):
            self.msg_win.addstr(i+1, 0, f"{messages[i].sender}: {messages[i].message}")
            self.msg_win.clrtoeol()
        #This part is needed if the messages size could be smaller than 10
        for i in range(len(messages)+1, 11):
            self.msg_win.move(i, 0)
            self.msg_win.clrtoeol()
        self.msg_win.refresh()

    def displayFriend(self, friends):
        #Display friend in line 1 to 10 of the message window
        for i in range(1, len(friends)+1):
            self.msg_win.addstr(i, 0, f"{i}: {friends[i-1]}")
            self.msg_win.clrtoeol()
        self.msg_win.refresh()

    def displayIncomingRequest(self, incomingRequest):
        ...

    def displaySentRequest(self, sentRequest):
        ...

    def setTitle(self, title):
        #Set the title of the feedback message in the first line of message window
        self.msg_win.addstr(0, 0, title)
        self.msg_win.clrtoeol()
        self.msg_win.refresh()

    def clearMsgWindow(self):
        #Clear message window
        self.msg_win.clear()
        self.msg_win.refresh()

    def showFeedback(self, feedback):
        #Display the feedback message in the line 1 of input window.
        self.input_win.addstr(1, 0, feedback)
        self.input_win.clrtoeol()
        self.input_win.refresh()

    def clearFeedback(self):
        #Clear feedback line in input window
        self.input_win.move(1,0)
        self.input_win.clrtoeol()
        self.input_win.refresh()

    def drawMenu(self, menuMessage):
        #Display the menu in the line 2 of input window.
        self.input_win.addstr(2, 0, menuMessage)
        self.input_win.clrtoeol()
        self.input_win.refresh()

    def getInteger(self, inputMessage, limit):
        #Display the input prompt in the line 3 of input window
        self.input_win.addstr(3, 0, inputMessage)
        y, x = self.input_win.getyx()
        self.input_win.refresh()
        valid = False
        while not valid:
            self.input_win.move(y, x) 
            self.input_win.clrtoeol()
            self.input_win.refresh()
            try:
                userInput = int(self.input_win.getstr().decode())
            except ValueError:
                self.showFeedback("Invalid input. Please try again.")   
                continue
            #read only positive integer within the range
            if userInput>=limit or userInput<1:
                self.showFeedback("Invalid input. Please try again.")
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
    
    def getTime(self, inputMessage):
        units = {"s": 1, "m": 60, "h": 3600}
        while True:
            userInput = self.getString()
            try:    
                value = int(userInput[:-1])
                unit = userInput[-1].lower()
                if unit not in units:
                    self.showFeedback("Invalid input. Enter a number + an unit (s/m/h)")
                    continue
                time = value * units[unit]
                if time<30 or time>86400:
                    self.showFeedback("Message lifetime must be between 30s and 24h.")
                    continue
                return time
            except Exception as e:
                self.showFeedback("Invalid input. Enter a number + an unit (s/m/h)")