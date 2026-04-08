import curses
from typing import List

class UI:
    
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.start_color()
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK) 
        curses.curs_set(1)  #Show cursor
        curses.echo()       #Show user typing: on

        self.locked = False

        self.h, self.w = stdscr.getmaxyx() #Get height(row) and width(col) of terminal
        self.msgWinSize = self.h-5
        """
        Title window: Responsible for displaying page title, one line only

        Message window: Responsible for displaying user messages and friend lists

        Input window: Responsible for displaying input prompt, UI feedback and the menu
        Line 0: Dividing line
        Line 1: Feedback line
        Line 2: Menu line
        Line 3: Input line
        """
        # Create windows
        self.title_win = curses.newwin(1, self.w, 0, 0)
        self.msg_win = curses.newwin(self.h - 5, self.w, 1, 0)   # Top: Display chatroom
        self.input_win = curses.newwin(4, self.w, self.h - 4, 0) # Bottom: Input window: input, menu, error
        
        self.msg_win.scrollok(True) #Scrolling = True

        self.typing_point = [3, 0] 
        # Divider line
        self.input_win.hline(0, 0, curses.ACS_HLINE, 10)
        self.input_win.refresh()

    def lock(self):
        while self.locked:
            pass
        self.locked = True

    def unlock(self):
        self.locked = False

    def displayMessage(self, messages: List):
        #Display messages in the message window
        self.lock()
        self.msg_win.clear()
        for i in range(len(messages)):
            if messages[i].delivered:
                self.msg_win.addstr(i, 0, f"{messages[i].sender}: {messages[i].message}")
            else:
                self.msg_win.addstr(i, 0, f"{messages[i].sender}: {messages[i].message}", curses.color_pair(1))
        self.msg_win.refresh()
        self.input_win.move(self.typing_point[0], self.typing_point[1])
        self.input_win.refresh()
        self.unlock()

    def displayFriend(self, friends: List[str], unread: List[int]):
        #Display friend in the message window
        self.lock()
        self.msg_win.clear()
        for i in range(len(friends)):
            self.msg_win.addstr(i, 0, f"{i+1}: {friends[i]}")
            if unread[i]>0:
                self.msg_win.addstr(f" ({unread[i]})") 
        self.msg_win.refresh()
        self.input_win.move(self.typing_point[0], self.typing_point[1])
        self.input_win.refresh()
        self.unlock()

    def displayRequest(self, sentRequests: List[str], rcvRequests: List[str]):
        #Display sent and received requests in the message window
        self.lock()
        self.msg_win.clear()
        self.msg_win.addstr(0, 0, "Users who wants to add you:")
        row = 1
        for i in range(len(rcvRequests)):
            self.msg_win.addstr(row, 0, f"{i+1}: {rcvRequests[i]}")
            row+=1
        self.msg_win.addstr(row, 0, "Requests you sent that are still pending:")
        row+=1
        for i in range(len(sentRequests)):
            self.msg_win.addstr(row, 0, f"{i+1}: {sentRequests[i]}")
            row+=1
        self.msg_win.refresh()
        self.input_win.move(self.typing_point[0], self.typing_point[1])
        self.input_win.refresh()
        self.unlock()

    def setTitle(self, title: str):
        #Set the title of the feedback message in the first line of message window
        self.title_win.addstr(0, 0, title)
        self.title_win.clrtoeol()
        self.title_win.refresh()

    def clearMsgWindow(self):
        #Clear message window
        self.msg_win.clear()
        self.msg_win.refresh()

    def showFeedback(self, feedback: str):
        #Display the feedback message in the line 1 of input window.
        self.input_win.addstr(1, 0, feedback)
        self.input_win.clrtoeol()
        self.input_win.refresh()

    def clearFeedback(self):
        #Clear feedback line in input window
        self.input_win.move(1,0)
        self.input_win.clrtoeol()
        self.input_win.refresh()

    def drawMenu(self, menuMessage: str):
        #Display the menu in the line 2 of input window.
        self.input_win.addstr(2, 0, menuMessage)
        self.input_win.clrtoeol()
        self.input_win.refresh()

    def getInteger(self, inputMessage: str, limit: int):
        #Display the input prompt in the line 3 of input window
        self.input_win.addstr(3, 0, inputMessage)
        self.typing_point = list(self.input_win.getyx())
        self.input_win.refresh()
        valid = False
        while not valid: 
            self.input_win.move(self.typing_point[0], self.typing_point[1])
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
        self.typing_point = list(self.input_win.getyx())
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
            userInput = self.getString(inputMessage)
            try:    
                value = int(userInput[:-1])
                unit = userInput[-1].lower()
                if unit not in units:
                    self.showFeedback("Invalid input. Enter a number + an unit (s/m/h)")
                    continue
                time = value * units[unit]
                if time<5 or time>86400:
                    self.showFeedback("Message lifetime must be between 30s and 24h.")
                    continue
                return time
            except Exception as e:
                self.showFeedback("Invalid input. Enter a number + an unit (s/m/h)")