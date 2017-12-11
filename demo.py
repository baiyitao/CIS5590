#!/usr/bin/python
"""
iRobot Create 2 Navigate
Jan 2017
Stephanie Littler
Neil Littler
Python 2
Uses the well constructed Create2API library for controlling the iRobot through a single
'Create2' class.
Implemented OI codes:
- Start (enters Passive mode)
- Reset (enters Off mode)
- Stop (enters Off mode. Use when terminating connection)
- Baud
- Safe
- Full
- Clean
- Max
- Spot
- Seek Dock
- Power (down) (enters Passive mode. This a cleaning command)
- Set Day/Time
- Drive
- Motors PWM
- Digit LED ASCII
- Sensors
Added Create2API function:
def buttons(self, button_number):
# Push a Roomba button
# 1=Clean 2=Spot 4=Dock 8=Minute 16=Hour 32=Day 64=Schedule 128=Clock

noError = True
if noError:
 self.SCI.send(self.config.data['opcodes']['buttons'], tuple([button_number]))
else:
raise ROIFailedToSendError("Invalid data, failed to send")
The iRobot Create 2 has 4 interface modes:
- Off : When first switched on (Clean/Power button). Listens at default baud (115200
8N1). Battery charges.
- Passive : Sleeps (power save mode) after 5 mins (1 min on charger) of inactivity and stops
serial comms.
 Battery charges. Auto mode. Button input. Read only sensors information.
- Safe : Never sleeps. Battery does not charge. Full control.
 If a safety condition occurs the iRobot reverts automatically to Passive mode.
- Full : Never sleeps. Battery does not charge. Full control.
 Turns off cliff, wheel-drop and internal charger safety features.
iRobot Create 2 Notes:
- A Start() command or any clean command the OI will enter into Passive mode.
- In Safe or Full mode the battery will not charge nor will iRobot sleep after 5 mins,
so you should issue a Passive() or Stop () command when you finish using the iRobot.
- A Stop() command will stop serial communication and the OI will enter into Off mode.
- A Power() command will stop serial communication and the OI will enter into Passive mode.
- Sensors can be read in Passive mode.
- The following conditions trigger a timer start that sleeps iRobot after 5 mins (or 1 min on
charger):
+ single press of Clean button (enters Passive mode)
+ Start() command not followed by Safe() or Full() commands
+ Reset() command
- When the iRobot is off and receives a (1 sec) low pulse of the BRC pin the OI (awakes and)
listens at the default baud rate for a Start() command
- Command a 'Dock' button press (while docked) every 30 secs to prevent iRobot sleep
- Pulse BRC pin LOW every 30 secs to prevent Create2 sleep when undocked
- iRobot beeps once to acknowledge it is starting from Off mode when undocked
Tkinter reference:
- ttk widget classes are Button Checkbutton Combobox Entry Frame Label LabelFrame Menubutton
Notebook
 PanedWindow Progressbar Radiobutton Scale Scrollbar Separator Sizegrip Treeview
- I found sebsauvage.net/python/gui/# a good resource for coding good practices
Navigation:
- navigation is calculated using wavefront algorithm. Code snipets provided by
www.societyofrobots.com
- guidance is by dead-reckoning, tactile sensing (bump detection) and proximity sensing (light
bumper)
- irobot will take advantage of paths along walls by tracking parallel
"""

import sys, traceback  # trap exceptions
import ttk
from Tkinter import *  # causes tk widgets to be upgraded by ttk widgets

import datetime  # time comparison for Create2 sleep prevention routine
import time  # sleep function
import threading  # used to timeout Create2 function calls if iRobot has gone to sleep
# import create2api


class Dashboard():
    def __init__(self, master):
        self.master = master
        self.InitialiseVars()
        self.paintGUI()

    def on_press_start(self):
        if self.btnwavefront.get() == 'Start':
            self.btnwavefront.set('Stop')
            self.runwavefront = True

        elif self.btnwavefront.get() == 'Stop':
            self.btnwavefront.set('Reset')
            self.runwavefront = False

        elif self.btnwavefront.get() == 'Reset':
            self.btnwavefront.set('Start')
            self.runwavefront = False

            self.map_place_piece("irobot", self.irobot_posn[1], self.irobot_posn[0])
            self.map_place_piece("goal", self.goal_posn[1], self.goal_posn[0])

    #baiyi
    def on_press_room(self):
        self.runClean = True

    def on_press_demo(self):
        if self.roomNumber.get() == 'A':
            self.goal_posn = [1,1]
        elif self.roomNumber.get() == 'B':
            self.goal_posn = [8, 6]
        elif self.roomNumber.get() == 'C':
            self.goal_posn = [16, 2]
        self.rundemo = True


    def on_exit(self):
        # Uses 'import tkMessageBox as messagebox' for Python2 or 'import tkMessageBox' for Python3 and 'root.protocol("WM_DELETE_WINDOW", on_exit)'
        # if messagebox.askokcancel("Quit", "Do you want to quit?"):
        print "Exiting irobot-navigate"
        self.exitflag = True
        # self.master.destroy()

    def on_select_datalinkconnect(self):
        if self.rbcomms.cget('selectcolor') == 'red':
            self.dataconn.set(True)
        elif self.rbcomms.cget('selectcolor') == 'lime green':
            self.dataretry.set(True)


    def on_mode_change(self, *args):
        self.modeflag.set(True)
        print "OI mode change from " + self.mode.get() + " to " + self.chgmode.get()

    def on_map_refresh(self, event):
        # redraw the map, possibly in response to window being resized
        xsize = int((event.width - 10) / self.map_columns)
        ysize = int((event.height - 150) / self.map_rows)
        self.map_squaresize = min(xsize, ysize)
        self.canvas.delete("square")
        colour = self.map_colour2

        for row in range(self.map_rows):
        # colour = self.map_colour1 if colour == self.map_colour2 else self.map_colour2
            for col in range(self.map_columns):
                if self.floormap[row][col] == 999:
                    colour = self.map_colour2
                else:
                    colour = self.map_colour1
                    x1 = (col * self.map_squaresize)
                    y1 = (row * self.map_squaresize)
                    x2 = x1 + self.map_squaresize
                    y2 = y1 + self.map_squaresize
                    self.canvas.create_rectangle(x1, y1, x2, y2, outline="black", fill=colour,tags="square")
        # resize goal and irobot images to fit into square
        # self.goal = self.goal.copy()
        self.img_flag.configure(image=self.goal)
        self.img_flag.image = self.goal  # keep a reference
        newsize = int((self.goal.width() * 1.4) / self.map_squaresize)
        self.img_flag.image = self.img_flag.image.subsample(newsize)
        self.canvas.itemconfig("goal", image=self.img_flag.image)
        # self.create2 = self.create2.copy()
        self.img_create2.configure(image=self.create2)
        self.img_create2.image = self.create2  # keep a reference
        newsize = int((self.create2.width() * 1.4) / self.map_squaresize)
        self.img_create2.image = self.img_create2.image.subsample(newsize)
        self.canvas.itemconfig("irobot", image=self.img_create2.image)
        for name in self.pieces:
            self.map_place_piece(name, self.pieces[name][0], self.pieces[name][1])

        self.canvas.tag_raise("piece")
        self.canvas.tag_lower("square")

        print "Resize map"


    def map_add_piece(self, name, image, row=0, column=0):
        # add an image to the map
        self.canvas.create_image(0, 0, image=image, tags=(name, "piece"), anchor="c")
        self.map_place_piece(name, row, column)


    def map_place_piece(self, name, row, column):
        # place an image at the given row/column
        self.pieces[name] = (row, column)
        x0 = (column * self.map_squaresize) + int(self.map_squaresize / 2)
        y0 = (row * self.map_squaresize) + int(self.map_squaresize / 2)
        self.canvas.coords(name, x0, y0)


    def InitialiseVars(self):
        '''
        wall = 999
        goal = 001
        irobot = 254
        '''

        # self.floormap =[[999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999, 999, 999, 999, 999, 999, 999, 000, 000, 000, 000, 000, 999, 999, 999, 999, 999, 999, 999, 999, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 999, 999, 999, 999, 000, 000, 000, 000, 000, 999, 999, 999, 999, 999, 999, 999, 999, 999, 001, 000, 000, 000, 000, 000, 000, 999, 999, 999, 999, 999, 999, 999],
        #  [999, 999, 999, 999, 999, 999, 999, 999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999, 999, 999, 999, 999, 999, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 000, 999, 999, 999, 999, 999, 999, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 999, 999, 999, 999, 999, 999, 000, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 254, 000, 000, 000, 000, 000, 000, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999],
        #  [999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 000, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999],
        #  [999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999]]


        self.floormap =\
        [[999, 999 , 999 , 999 , 999 , 999 , 999 , 999, 999 , 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999],
         [999, 254 , '0a', '0a', '0a', '0a', '0a', 999, '0b', '0b', '0b', 999 , '0b', '0b', '0b', 999, '0c', '0c', '0c', '0c', '0c', 999, 999],
         [999, '0a', '0a', '0a', '0a', '0a', '0a', 999, '0b', '0b', '0b', '0b', '0b', '0b', '0b', 666, '0c', '0c', '0c', '0c', '0c', 999, 999],
         [999, 999 , '0a', '0a', '0a', '0a', '0a', 999, '0b', '0b', '0b', '0b', '0b', '0b', '0b', 999, '0c', '0c', '0c', '0c', '0c', 999, 999],
         [999, '0a', '0a', '0a', '0a', '0a', '0a', 999, '0b', '0b', '0b', 999 , '0b', '0b', '0b', 999, '0c', '0c', '0c', '0c', '0c', '0c', 999],
         [999, '0a', '0a', '0a', '0a', '0a', '0a', 999, '0b', '0b', '0b', '0b', '0b', '0b', '0b', 999, '0c', '0c', '0c', '0c', '0c', '0c', 999],
         [999, '0a', '0a', '0a', '0a', '0a', '0a', 666, '0b', '0b', '0b', '0b', '0b', '0b', '0b', 999, '0c', '0c', '0c', '0c', '0c', '0c', 999],
         [999, 999 , 999 , 999 , 999 , 999 , 999 , 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999]]


        self.flag_gif = '''R0lGODlhmACYAPcAAAAAAAAAMwAAZgAAmQAAzAAA/wArAAArMwArZgArmQArzAAr/wBVAABVMwBV
        ZgBVmQBVzABV/wCAAACAMwCAZgCAmQCAzACA/wCqAACqMwCqZgCqmQCqzACq/wDVAADVMwDVZgDV
        mQDVzADV/wD/AAD/MwD/ZgD/mQD/zAD//zMAADMAMzMAZjMAmTMAzDMA/zMrADMrMzMrZjMrmTMr
        zDMr/zNVADNVMzNVZjNVmTNVzDNV/zOAADOAMzOAZjOAmTOAzDOA/zOqADOqMzOqZjOqmTOqzDOq
        /zPVADPVMzPVZjPVmTPVzDPV/zP/ADP/MzP/ZjP/mTP/zDP//2YAAGYAM2YAZmYAmWYAzGYA/2Yr
        AGYrM2YrZmYrmWYrzGYr/2ZVAGZVM2ZVZmZVmWZVzGZV/2aAAGaAM2aAZmaAmWaAzGaA/2aqAGaq
        M2aqZmaqmWaqzGaq/2bVAGbVM2bVZmbVmWbVzGbV/2b/AGb/M2b/Zmb/mWb/zGb//5kAAJkAM5kA
        ZpkAmZkAzJkA/5krAJkrM5krZpkrmZkrzJkr/5lVAJlVM5lVZplVmZlVzJlV/5mAAJmAM5mAZpmA
        mZmAzJmA/5mqAJmqM5mqZpmqmZmqzJmq/5nVAJnVM5nVZpnVmZnVzJnV/5n/AJn/M5n/Zpn/mZn/
        zJn//8wAAMwAM8wAZswAmcwAzMwA/8wrAMwrM8wrZswrmcwrzMwr/8xVAMxVM8xVZsxVmcxVzMxV
        /8yAAMyAM8yAZsyAmcyAzMyA/8yqAMyqM8yqZsyqmcyqzMyq/8zVAMzVM8zVZszVmczVzMzV/8z/
        AMz/M8z/Zsz/mcz/zMz///8AAP8AM/8AZv8Amf8AzP8A//8rAP8rM/8rZv8rmf8rzP8r//9VAP9V
        M/9VZv9Vmf9VzP9V//+AAP+AM/+AZv+Amf+AzP+A//+qAP+qM/+qZv+qmf+qzP+q///VAP/VM//V
        Zv/Vmf/VzP/V////AP//M///Zv//mf//zP///wAAAAAAAAAAAAAAACH5BAEAAPwALAAAAACYAJgA
        AAj/APcJHEiwoMGDCBMqXMiwocOHECNKnEixosWLGDNqNAigI4CNIEOKHCnQo0dlJFOqXLnQZEeW
        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
        '''

        self.createRob = '''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'''


        # declare variable classes=StringVar, BooleanVar, DoubleVar, IntVar
        self.map_rows = IntVar();   self.map_rows = len(self.floormap)
        self.map_columns = IntVar();   self.map_columns = len(self.floormap[0])
        self.map_squaresize = IntVar();   self.map_squaresize = 32  # initial GUI map square size
        self.map_colour1 = StringVar();   self.map_colour1 = "white"  # floor colour
        self.map_colour2 = StringVar();   self.map_colour2 = "blue"  # wall colour
        self.pieces = {}  # dictionary containing map objects
        self.irobot_posn = [0, 0]  # irobot location  initally     read   from self.floormap
        self.goal_posn = [1, 1]  # goal location       initally       read       from self.floormap
        self.unitsize = IntVar();   self.unitsize = 347  # unit size per     movement in mm
        self.orientation = StringVar();   self.orientation.set('Up')  # initial orientation    of  irobot  at  stating  location
        self.dataconn = BooleanVar();   self.dataconn.set(True)  # Attempt a data link  connection with iRobot
        self.dataretry = BooleanVar();  self.dataretry.set(False)  # Retry a data link  connection with iRobot
        self.chgmode = StringVar();   self.chgmode.set('')  # Change OI mode
        self.chgmode.trace('w', self.on_mode_change)  # Run function when  value  changes
        self.modeflag = BooleanVar();  self.modeflag.set(False)  # Request to change OI  mode
        self.mode = StringVar()  # Current operating OIode
        self.powersource = StringVar();  self.powersource.set('')  # Power source:  Homebase or Battery
        self.speed = StringVar()  # Maximum drive speed



        self.leftbuttonclick = BooleanVar();     self.leftbuttonclick.set(False)
        self.commandvelocity = IntVar();     self.commandvelocity.set(0)
        self.commandradius = IntVar();     self.commandradius.set(0)


        self.xorigin = IntVar();    self.xorigin = 0  # mouse x coord
        self.yorigin = IntVar();   self.yorigin = 0  # mouse x coord
        self.docked = BooleanVar();      self.docked = False

        self.btnwavefront = StringVar();    self.btnwavefront.set('Start')

        self.rundemo = BooleanVar();   self.rundemo = False
        self.runwavefront = BooleanVar();   self.runwavefront = False
        self.return_to_base = BooleanVar()  # irobot will return to  base  after  finding   goal

        self.exitflag = BooleanVar();   self.exitflag = False  # Exit program flag
        self.runClean = BooleanVar();   self.runClean = False  #baiyi
        self.roomNumber = StringVar();   self.roomNumber.set('NULL')


    def paintGUI(self):

        self.master.geometry('1080x670+20+50')
        self.master.wm_title("iRobot Navigate")
        self.master.configure(background='white')
        self.master.protocol("WM_DELETE_WINDOW", self.on_exit)
        s = ttk.Style()


        s.theme_use('clam')

        # TOP LEFT FRAME - DRIVE
        frame = Frame(self.master, bd=1, width=330, height=130, background='white',
                      relief=GROOVE)
        # labels



        # MIDDLE FRAME - START / STOP
        frame = Frame(self.master, bd=1, width=280, height=130, background='white',
        relief = GROOVE)
        # labels
        Label(frame, text="FIND THE GOAL", background='white').pack()
        label = Label(frame, text="Initial Orientation", background='white')
        label.pack()
        label.place(x=10, y=95)
        # buttons

        button = ttk.Button(frame, text='DemoClean', command=self.on_press_room)
        button.pack()
        button.place(x=10, y=20)


        button = ttk.Button(frame, text='DemoNav', command=self.on_press_demo)
        button.pack()
        button.place(x=10, y=55)

        changeRoom = ttk.Combobox(frame, values=('A', 'B', 'C'), textvariable = self.roomNumber, width = 10)
        changeRoom.pack()
        changeRoom.place(x=150, y=60)





        # frame.pack()
        frame.pack_propagate(0)  # prevents frame autofit
        frame.place(x=10, y=10)
        # combobox
        self.cmbOrientation = ttk.Combobox(frame, values=('Up', 'Down', 'Left', 'Right'),
        textvariable = self.orientation, width = 10)
        self.cmbOrientation.pack()
        self.cmbOrientation.place(x=150, y=95)



        # TOP RIGHT FRAME - DATA LINK
        frame = Frame(self.master, bd=1, width=310, height=130, background='white',
        relief = GROOVE)
        # labels
        Label(frame, text="DATA LINK", background='white').pack()
        self.rbcomms = Radiobutton(frame, state=DISABLED, background='white', value=1,
        command = self.on_select_datalinkconnect, relief = FLAT, disabledforeground = 'white',
        selectcolor = 'red', borderwidth = 0)
        self.rbcomms.pack()
        self.rbcomms.place(x=208, y=1)
        label = Label(frame, text="OI Mode", background='white')
        label.pack()
        label.place(x=10, y=35)
        label = Label(frame, text="Change OI Mode", background='white')
        label.pack()
        label.place(x=10, y=65)
        label = Label(frame, text="Power Source", background='white')
        label.pack()
        label.place(x=10, y=95)
        # telemetry display
        label = Label(frame, textvariable=self.mode, anchor=W, background='snow2', width=10)
        label.pack()
        label.place(x=150, y=34)
        label = Label(frame, textvariable=self.powersource, anchor=W, background='snow2',
        width = 10)
        label.pack()
        label.place(x=150, y=94)
        # combobox
        self.cmbMode = ttk.Combobox(frame, values=('Passive', 'Safe', 'Full', 'Seek Dock'),
        textvariable = self.chgmode, width = 10)
        # self.cmbMode['values'] = ('Passive', 'Safe', 'Full', 'Seek Dock')
        self.cmbMode.pack()
        self.cmbMode.place(x=150, y=63)

        # frame.pack()
        frame.pack_propagate(0)  # prevents frame autofit
        frame.place(x=350, y=10)








        # button = ttk.Button(frame, text='Room A', command=self.on_press_room("A"))
        # button.pack()
        # button.place(x=10, y=25)
        #
        # button = ttk.Button(frame, text='Room B', command=self.on_press_room("B"))
        # button.pack()
        # button.place(x=10, y=60)
        # frame.pack()
        frame.pack_propagate(0)  # prevents frame autofit
        frame.place(x=680, y=10)





        # BOTTOM FRAME - FLOOR MAP
        # iRobot Create 2 image
        '''
        image = Image.open('create2.png') # uses 'from PIL import Image'
        image = create.rotate(90)
        image = create.resize((100,100))
        image.show()
        #create2 = PhotoImage(Image.open('create2.gif'))
        '''
        # self.create2 = PhotoImage(file='/Users/baiyi/Desktop/CIS5590-master/create2.gif')
        self.create2 = PhotoImage(data=self.createRob)
        self.img_create2 = Label(self.master, image=self.create2, background='white')
        self.img_create2.image = self.create2  # keep a reference
        # self.img.pack() ; self.img.place(x=465, y=80)
        # goal image
        self.goal = PhotoImage(data=self.flag_gif)
        self.img_flag = Label(self.master, image=self.goal, background='white')
        self.img_flag.image = self.goal  # keep a reference
        '''
        # test to see image change
        self.img_flag.configure(image=self.create2)
        self.img_flag.image = self.create2
        '''
        # canvas
        canvas_width = 1080
        canvas_height = 670
        self.canvas = Canvas(self.master, borderwidth=0, highlightthickness=0,
        width = canvas_width, height = canvas_height, background = "white")
        self.canvas.pack(side="top", fill="both", expand=True, padx=2, pady=2)
        self.canvas.place(x=10, y=150)
        xsize = int((1080 - 10) / self.map_columns)
        ysize = int((670 - 160) / self.map_rows)
        self.map_squaresize = min(xsize, ysize)
        colour = self.map_colour2
        for row in range(self.map_rows):
        # colour = self.map_colour1 if colour == self.map_colour2 else self.map_colour2
            for col in range(self.map_columns):
                if self.floormap[row][col] == 999:
                    colour = self.map_colour2
                    x1 = (col * self.map_squaresize)
                    y1 = (row * self.map_squaresize)
                    x2 = x1 + self.map_squaresize
                    y2 = y1 + self.map_squaresize
                    self.canvas.create_rectangle(x1, y1, x2, y2, outline="black", fill=colour, tags="square")
                elif self.floormap[row][col] == 666:
                    colour = "red"
                    x1 = (col * self.map_squaresize)
                    y1 = (row * self.map_squaresize)
                    x2 = x1 + self.map_squaresize
                    y2 = y1 + self.map_squaresize
                    self.canvas.create_rectangle(x1, y1, x2, y2, outline="black", fill=colour, tags="square")
                else:
                    colour = self.map_colour1
                    x1 = (col * self.map_squaresize)
                    y1 = (row * self.map_squaresize)
                    x2 = x1 + self.map_squaresize
                    y2 = y1 + self.map_squaresize
                    self.canvas.create_rectangle(x1, y1, x2, y2, outline="black", fill=colour, tags = "square")
                # resize goal and irobot images to fit into square
                if self.floormap[row][col] == 001:
                    self.goal_posn = [col, row]
                    newsize = int((self.goal.width() * 1.4) / self.map_squaresize)
                    self.img_flag.image = self.img_flag.image.subsample(newsize)
                    self.map_add_piece("goal", self.img_flag.image, row, col)

                if self.floormap[row][col] == 254:
                    self.irobot_posn = [col, row]
                    newsize = int((self.create2.width() * 1.4) / self.map_squaresize)
                    self.img_create2.image = self.img_create2.image.subsample(newsize)
                    self.map_add_piece("irobot", self.img_create2.image, row, col)

        self.canvas.tag_raise("piece")
        self.canvas.tag_lower("square")


    def comms_check(self, flag):
        if flag == 1:  # have comms
            self.rbcomms.configure(state=NORMAL, selectcolor='lime green', foreground='lime green')
            self.rbcomms.select()
        elif flag == 0:  # no comms
            self.rbcomms.configure(state=NORMAL, selectcolor='red', foreground='red')
            self.rbcomms.select()
        elif flag == -1:  # for flashing radio button
            self.rbcomms.configure(state=DISABLED)



class WavefrontMachine:
    def __init__(self, map, robot_posn, goal_posn, slow=False):
        self.__slow = slow
        self.__map = map
        self.__height, self.__width = len(self.__map), len(self.__map[0])
        self.__nothing = 0
        self.__wall = 999
        self.__goal = 1
        self.__path = "PATH"
        # Robot value
        self.__robot = 254
        # Robot default Location
        self.__robot_col, self.__robot_row = robot_posn
        # default goal location
        self.__goal_col, self.__goal_row = goal_posn
        self.__steps = 0  # determine how processor intensive the algorithm was
        # when searching for a node with a lower value
        self.__minimum_node = 250
        self.__min_node_location = 250
        self.__new_state = 1
        self.__reset_min = 250  # above this number is a special (wall or robot)
        self.orientation_in_degrees = 0


    def setRobotPosition(self, row, col):
        """
        Sets the robot's current position
        """
        self.__robot_row = row
        self.__robot_col = col


    def setGoalPosition(self, row, col):
        """
        Sets the goal position.
        """
        self.__goal_row = row
        self.__goal_col = col


    def robotPosition(self):
        return (self.__robot_row, self.__robot_col)


    def goalPosition(self):
        return (self.__goal_row, self.__goal_col)


    def irobot_rotate(self, bot, orientate):
        timelimit(1, bot.get_packet, (20,), {})  # resets angle counter
        angle = 0
        if orientate > 0: bot.drive(40, 1)  # anti-clockwise
        if orientate < 0: bot.drive(40, -1)  # clockwise
        while angle < abs(orientate):
            timelimit(1, bot.get_packet, (20,), {})
            angle = angle + abs(bot.sensor_state['angle'])
            time.sleep(.02)  # irobot updates sensor and internal state variables every 15ms
        bot.drive(0, 32767)  # stop


    def run(self, dashboard, bot, return_path, prnt=False, demo=True, alarm=False):
        """
        The entry point for the robot algorithm to use wavefront propagation.
        """
        dashboard.comms_check(1)  # set datalink LED to solid green
        counter_rotate_adjustment = False  # does irobot need to counter rotate after a bump  rotation
        rotation_angle = 0  # angle to rotate irobot after a bump
        orientate = 0  # orientate irobot in degrees before next move  forward
        next_move = ''  # next irobot forward move relative to map (Left, Right, Up, Down, < blank > if rotating)
        adjacent_wall = ''  # Starboard or Port if irobot is running along a wall. < blank > if no adjacent wall.
        current_robot_row = 0
        current_robot_col = 0
        later_robot_row = 0  # 2nd move ahead
        later_robot_col = 0  # 2nd move ahead

        # set irobot starting position orientation in degrees
        if not return_path:
            if dashboard.orientation.get() == 'Up':
                self.orientation_in_degrees = 0
            elif dashboard.orientation.get() == 'Right':
                self.orientation_in_degrees = 90
            elif dashboard.orientation.get() == 'Down':
                self.orientation_in_degrees = 180
            elif dashboard.orientation.get() == 'Left':
                self.orientation_in_degrees = 270
        print "Starting coords : x=%d y=%d" % (self.__robot_col, self.__robot_row)
        print "Orientation : %d degrees" % self.orientation_in_degrees

        # undock irobot (if docked) when not demo mode
        if not demo:
            if dashboard.docked and not return_path:
                bot.digit_led_ascii(' REV')
                print "Undocking..."

                timelimit(1, bot.get_packet, (19,), {})  # resets distance counter
                dist = 0
                bot.drive(int(dashboard.speed.get()) * -1, 32767)  # reverse
                while dist < (dashboard.unitsize - int(dashboard.speed.get()) / 2.5):
                    timelimit(1, bot.get_packet, (34,), {})
                    if bot.sensor_state['charging sources available']['home base']:
                        dashboard.powersource.set('Home Base')
                    else:
                        dashboard.powersource.set('Battery')

                    timelimit(1, bot.get_packet, (19,), {})
                    dist = dist + abs(bot.sensor_state['distance'])
                    time.sleep(.02)  # irobot updates sensor and internal state variables every 15  ms
                bot.drive(0, 32767)  # stop
                dist = 0
                if dashboard.orientation.get() == 'Left':
                    self.__robot_col += 1
                elif dashboard.orientation.get() == 'Right':
                    self.__robot_col += -1
                elif dashboard.orientation.get() == 'Up':
                    self.__robot_row += 1
                elif dashboard.orientation.get() == 'Down':
                    self.__robot_row += -1

                # reposition irobot on map after undocking (reversing from dock)
                dashboard.map_place_piece("irobot", self.__robot_row, self.__robot_col)
                dashboard.master.update()
                dashboard.master.update()

        # calculate next irobot move using wavefront algorithm
        path = []  # not utilised but holds entire path xy coordinates
        while self.__map[self.__robot_row][self.__robot_col] != self.__goal and \
                not dashboard.exitflag and (dashboard.runwavefront or dashboard.rundemo):
            if self.__steps > 20000:
                print "Cannot find a path"
                return

            # timelimit(1, bot.get_packet, (34,), {})
            # if bot.sensor_state['charging sources available']['home base']:
            #     dashboard.powersource.set('Home Base')
            # else:
            #     dashboard.powersource.set('Battery')

            current_robot_row = self.__robot_row
            current_robot_col = self.__robot_col

            # determine new irobot location to move to
            self.__new_state = self.propagateWavefront()
            # update irobot xy varaiables
            if self.__new_state == 1: self.__robot_row -= 1
            if self.__new_state == 2: self.__robot_col += 1
            if self.__new_state == 3: self.__robot_row += 1
            if self.__new_state == 4: self.__robot_col -= 1

            # determine later irobot location to move to
            self.__new_state = self.propagateWavefront()
            if self.__new_state == 1: later_robot_row = self.__robot_row - 1
            if self.__new_state == 2: later_robot_col = self.__robot_col + 1
            if self.__new_state == 3: later_robot_row = self.__robot_row + 1
            if self.__new_state == 4: later_robot_col = self.__robot_col - 1
            self.__map[later_robot_row][later_robot_col] = self.__nothing  # clear that space
            self.__map[self.__goal_row][self.__goal_col] = self.__goal  # in case goal was overwritten

            # reposition irobot on map for new location
            print "Move to x=%d y=%d" % (self.__robot_col, self.__robot_row)

            time.sleep(.1)
            dashboard.map_place_piece("irobot", self.__robot_row, self.__robot_col)
            dashboard.master.update()

            # rotate irobot to correct orientation in preparation for moving to new location
            if (self.__robot_row - current_robot_row) == 1:  # navigate down
                orientate = self.orientation_in_degrees - 180
                self.orientation_in_degrees = 180  # set to orientation after     move
            elif (self.__robot_row - current_robot_row) == -1:  # navigate up
                orientate = self.orientation_in_degrees - 0
                self.orientation_in_degrees = 0  # set to orientation after      move
            elif (self.__robot_col - current_robot_col) == 1:  # navigate right
                orientate = self.orientation_in_degrees - 90
                self.orientation_in_degrees = 90  # set to orientation after  move
            elif (self.__robot_col - current_robot_col) == -1:  # navigate left
                orientate = self.orientation_in_degrees - 270
                self.orientation_in_degrees = 270  # set to orientation after    move
            if orientate == 270: orientate = -90
            if orientate == -270: orientate = 90

            path.append((self.__robot_row, self.__robot_col, self.orientation_in_degrees))




            # move irobot if not in demo mode
            if not demo:

                # orientate irobot before next move
                if orientate <> 0:
                    bot.digit_led_ascii(str(orientate)[:4].rjust(4))
                    print "Orientating %s degrees..." % str(orientate)
                    self.irobot_rotate(bot, int(orientate + orientate * 0.13))  # add 10% for error
                    next_move = ''

                # check for adjacent walls if driving straight ahead
                else:
                    # irobot moves right
                    if (self.__robot_row == current_robot_row) and (self.__robot_col >  current_robot_col):
                        next_move = 'Right'
                        if self.__map[self.__robot_row + 1][self.__robot_col] == 999:
                            adjacent_wall = 'Starboard'
                        elif self.__map[self.__robot_row - 1][self.__robot_col] == 999:
                            adjacent_wall = 'Port'
                        else:
                            adjacent_wall = ''

                    # irobot moves left
                    elif (self.__robot_row == current_robot_row) and (self.__robot_col < current_robot_col):
                        next_move = 'Left'
                        if self.__map[self.__robot_row + 1][self.__robot_col] == 999:
                            adjacent_wall = 'Port'
                        elif self.__map[self.__robot_row - 1][self.__robot_col] == 999:
                            adjacent_wall = 'Starboard'
                        else:
                            adjacent_wall = ''

                    # irobot moves down
                    elif (self.__robot_row > current_robot_row) and (self.__robot_col == current_robot_col):
                        next_move = 'Down'
                        if self.__map[self.__robot_row][self.__robot_col + 1] == 999:
                            adjacent_wall = 'Port'
                        elif self.__map[self.__robot_row][self.__robot_col - 1] == 999:
                            adjacent_wall = 'Starboard'
                        else:
                            adjacent_wall = ''

                    # irobot moves up
                    elif (self.__robot_row < current_robot_row) and (self.__robot_col == current_robot_col):
                        next_move = 'Up'
                        if self.__map[self.__robot_row][self.__robot_col + 1] == 999:
                            adjacent_wall = 'Starboard'
                        elif self.__map[self.__robot_row][self.__robot_col - 1] == 999:
                            adjacent_wall = 'Port'
                        else:
                            adjacent_wall = ''

                # does irobot needs to counter rotate after a prior bump rotation
                # or is irobot running adjacent a wall
                if counter_rotate_adjustment:
                    bot.digit_led_ascii(' ADJ')
                    print "Orientation adjustment..."
                    self.irobot_rotate(bot, int(rotation_angle * -1 / 2))  # counter rotate
                    counter_rotate_adjustment = False
                elif adjacent_wall == 'Port':
                    bot.digit_led_ascii('-HUG')
                    print "Hug left wall..."
                    self.irobot_rotate(bot, 2)  # rotate anti-clockwise
                elif adjacent_wall == 'Starboard':
                    bot.digit_led_ascii('HUG-')
                    print "Hug right wall..."
                    self.irobot_rotate(bot, -2)  # rotate clockwise
                # navigate irobot ahead one unit
                bot.digit_led_ascii('FWRD')
                print "Drive forward..."
                timelimit(1, bot.get_packet, (19,), {})  # resets distance counter
                dist = 0

                # if bumped head on don't drive forward
                timelimit(1, bot.get_packet, (45,), {})  # light bumper detect
                if (bot.sensor_state['light bumper']['center right'] == True and bot.sensor_state['light bumper']['center left'] == True):
                        pass
                else:
                    # if irobot reaches goal 2 moves out and
                    # is on a return path back to a docking station then dock
                    if later_robot_row == self.__goal_row and later_robot_col == self.__goal_col and dashboard.docked and return_path:
                        self.__robot_row = self.__goal_row
                        self.__robot_col = self.__goal_col
                        dashboard.chgmode.set('Seek Dock')
                        dist = 1000
                    else:
                        bot.drive(int(dashboard.speed.get()), 32767)  # forward

                while dist < (dashboard.unitsize - int(dashboard.speed.get()) / 3.5) and dashboard.runwavefront:
                    timelimit(1, bot.get_packet, (19,), {})
                    dist = dist + abs(bot.sensor_state['distance'])

                    # detect and adjust for obstacles
                    timelimit(1, bot.get_packet, (45,), {})  # light bumper detect
                    timelimit(1, bot.get_packet, (7,), {})  # bumper detect
                    # format a bump string for printing bump status
                    b = 0
                    if bot.sensor_state['light bumper']['right'] == True:
                        b = b + 1
                    if bot.sensor_state['light bumper']['front right'] == True:
                        b = b + 2
                    if bot.sensor_state['light bumper']['center right'] == True:
                        b = b + 4
                    if bot.sensor_state['light bumper']['center left'] == True:
                        b = b + 8
                    if bot.sensor_state['light bumper']['front left'] == True:
                        b = b + 16
                    if bot.sensor_state['light bumper']['left'] == True:
                        b = b + 32
                    bstr = format(b, '06b')
                    bstr = bstr.replace("1", "X")
                    bstr = bstr[:3] + "-" + bstr[3:]

                    # if bumped head on
                    if (bot.sensor_state['light bumper']['center right'] == True and bot.sensor_state['light bumper']['center left'] == True) or (bot.sensor_state['wheel drop and bumps']['bump left'] == True and bot.sensor_state['wheel drop and bumps']['bump right'] == True):
                        print "Proximity bump %s" % bstr
                        if (bot.sensor_state['wheel drop and bumps']['bump left'] == True and bot.sensor_state['wheel drop and bumps']['bump right'] == True):
                            print "Bumped head"
                        bot.drive(0, 32767)  # always stop if bumped head on
                        dist = 1000  # exit while to stop irobot moving forward

                        # if previous move was an orientation (turn) then back out and move forward to try again
                        if orientate <> 0:
                            bot.digit_led_ascii('BACK')
                            print "Reversing move and re-orientating %s degrees..." %str(orientate * -1)
                            self.irobot_rotate(bot, int((orientate + orientate * 0.1) * -1))  # add 10 % for error
                            self.__robot_row, self.__robot_col, self.orientation_in_degrees = path.pop()
                            self.__map[self.__robot_row][self.__robot_col] = self.__nothing
                            # clear that space

                            self.__robot_row, self.__robot_col, self.orientation_in_degrees = path.pop()
                            self.__map[self.__robot_row][self.__robot_col] = self.__nothing
                            # clear that space

                            self.__robot_row, self.__robot_col, self.orientation_in_degrees = path[len(path) - 1]
                            print "Probable position : x=%d y=%d" % (self.__robot_col, self.__robot_row)
                            dashboard.map_place_piece("irobot", self.__robot_row, self.__robot_col)
                            dashboard.master.update()
                        else:
                        # determine if next irobot movement is a turn,
                        # if so loop returns to calculate next move, else abort
                        # irobot is still travelling in straight line and therefore has no  idea where to go
                            if (later_robot_row - self.__robot_row) == 1:  # navigate down
                                if (self.orientation_in_degrees - 180) == 0:
                                    bot.digit_led_ascii('STOP')
                                    print "Cannot determine path... Stopping."
                                    dashboard.runwavefront = False
                            elif (later_robot_row - self.__robot_row) == -1:  # navigate up
                                if (self.orientation_in_degrees - 0) == 0:
                                    bot.digit_led_ascii('STOP')
                                    print "Cannot determine path... Stopping."
                                    dashboard.runwavefront = False
                            elif (later_robot_col - self.__robot_col) == 1:  # navigate right
                                if (self.orientation_in_degrees - 90) == 0:
                                    bot.digit_led_ascii('STOP')
                                    print "Cannot determine path... Stopping."
                                    dashboard.runwavefront = False
                            elif (later_robot_col - self.__robot_col) == -1:  # navigate left
                                if (self.orientation_in_degrees - 270) == 0:
                                    bot.digit_led_ascii('STOP')
                                    print "Cannot determine path... Stopping."
                                    dashboard.runwavefront = False

                    # if light bumper sensors trigger with an adjacent wall (prevent head on triggers)
                    elif (bot.sensor_state['light bumper']['right'] == True or bot.sensor_state['light bumper']['front right'] == True) and adjacent_wall <> "":
                        bot.digit_led_ascii('BUMP')
                        print "Proximity bump %s" % bstr
                        bot.drive(0, 32767)  # stop
                        rotation_angle = 5
                        self.irobot_rotate(bot, rotation_angle)  # rotate anti-clockwise
                        bot.digit_led_ascii('FWRD')
                        bot.drive(int(dashboard.speed.get()), 32767)  # forward
                        counter_rotate_adjustment = True

                    elif (bot.sensor_state['light bumper']['front left'] == True or bot.sensor_state['light bumper']['left'] == True) and adjacent_wall <> "":
                        bot.digit_led_ascii('BUMP')
                        print "Proximity bump %s" % bstr
                        bot.drive(0, 32767)  # stop
                        rotation_angle = -5
                        self.irobot_rotate(bot, rotation_angle)  # rotate clockwise
                        bot.digit_led_ascii('FWRD')
                        bot.drive(int(dashboard.speed.get()), 32767)  # forward
                        counter_rotate_adjustment = True

                    # if outside bump sensors trigger
                    elif bot.sensor_state['wheel drop and bumps']['bump left'] == True:
                        bot.digit_led_ascii('BUMP')
                        print "Bump left..."
                        bot.drive(0, 32767)  # stop
                        rotation_angle = -12
                        self.irobot_rotate(bot, rotation_angle)  # rotate clockwise
                        bot.digit_led_ascii('FWRD')
                        bot.drive(int(dashboard.speed.get()), 32767)  # forward
                        counter_rotate_adjustment = True

                    elif bot.sensor_state['wheel drop and bumps']['bump right'] == True:
                        bot.digit_led_ascii('BUMP')
                        print "Bump right..."
                        bot.drive(0, 32767)  # stop
                        rotation_angle = 12
                        self.irobot_rotate(bot, rotation_angle)  # rotate anti-clockwise
                        bot.digit_led_ascii('FWRD')
                        bot.drive(int(dashboard.speed.get()), 32767)  # forward
                        counter_rotate_adjustment = True

                    time.sleep(.02)  # irobot updates sensor and internal state variables every 15 ms
                    timelimit(1, bot.get_packet, (35,), {})  # oi mode
                    if bot.sensor_state['oi mode'] == 1:  # if tripped into Passive mode
                        dashboard.runwavefront = False

                bot.drive(0, 32767)  # stop # can this command be excluded??
                dist = 0

        if dashboard.runwavefront or dashboard.rundemo:
            msg = "Found the goal in %i steps:" % self.__steps
            # msg += "Map size= %i %i\n" % (self.__height, self.__width)
            print msg
            if prnt: self.printMap()

        if dashboard.runwavefront:
            bot.play_song(0,'A4,40,A4,40,A4,40,F4,30,C5,10,A4,40,F4,30,C5,10,A4,80')
            if alarm:
                # bot.play_song(0, 'C5,5,C5,10,C5,5,C5,10,C5,5,C5,10,C5,5,C5,10,C5,5,C5,10,C5,5,C5,10,G5,5,E5,10,G5, 5, E5, 10, G5, 5, E5, 10, C5, 5, C5, 10, C5, 5, C5, 10, C5, 5, C5, 10, C5, 5, C5, 10, C5, 5, C5, 10, C5, 5, C5, 10, G5, 5, E5, 10, G5, 5, E5, 10, G5, 5, E5, 10, C5, 45')
                if alarm: bot.play_test_sound()
                # bot.play_song(0,'B6,5,rest,6,A6,5,rest,7,G6,5,rest,8,F6,5,rest,9,E6,5,rest,10,D6,5,rest,11,C6, 5, rest, 12, B6, 5, rest, 13, A6, 5, rest, 14, B5, 5, rest, 15, A5, 5, rest, 16, G5, 5, rest, 17, F5, 5, rest, 18, E5, 5,rest, 19, D5, 5, rest, 20, C5, 5, rest, 21, B5, 5, rest, 22, A5, 5, rest, 23, B4, 5, rest, 24, A4, 5, rest, 25, G4, 5, rest, 26, F4, 5, rest, 27, E4, 5, rest, 28, D4, 5, rest, 29, C4, 5')
        elif not dashboard.rundemo:
            print "Aborting Wavefront"
            bot.play_song(0, 'G3,16,C3,32')

        self.resetmap(dashboard.irobot_posn, dashboard.goal_posn)
        return path


    def propagateWavefront(self, prnt=False):
        """
        """
        self.unpropagate()
        # old robot location was deleted, store new robot location in map
        self.__map[self.__robot_row][self.__robot_col] = self.__robot
        self.__path = self.__robot
        # start location to begin scan at goal location
        self.__map[self.__goal_row][self.__goal_col] = self.__goal
        counter = 0
        while counter < 200:  # allows for recycling until robot is found
            x = 0
            y = 0
            time.sleep(0.00001)
            # while the map hasnt been fully scanned
            while y < self.__height and x < self.__width:
                # if this location is a wall or the goal, just ignore it
                if self.__map[y][x] != self.__wall and \
                    self.__map[y][x] != self.__goal:
                    # a full trail to the robot has been located, finished!
                    minLoc = self.minSurroundingNodeValue(x, y)
                    if minLoc < self.__reset_min and \
                        self.__map[y][x] == self.__robot:
                        if prnt:
                            print "Finished Wavefront:\n"
                            self.printMap()
                        # Tell the robot to move after this return.
                        return self.__min_node_location
                    # record a value in to this node
                    elif self.__minimum_node != self.__reset_min:
                        # if this isnt here, 'nothing' will go in the location
                        self.__map[y][x] = self.__minimum_node + 1
                # go to next node and/or row
                x += 1
                if x == self.__width and y != self.__height:
                    y += 1
                    x = 0
            # print self.__robot_row, self.__robot_col
            if prnt:
                print "Sweep #: %i\n" % (counter + 1)
                self.printMap()
            self.__steps += 1
            counter += 1
        return 0


    def unpropagate(self):
        """
        clears old path to determine new path
        stay within boundary
        """
        for y in range(0, self.__height):
            for x in range(0, self.__width):
                if self.__map[y][x] != self.__wall and self.__map[y][x] != self.__goal and self.__map[y][x] != self.__path:
                    # if this location is a wall or goal, just ignore it
                    self.__map[y][x] = self.__nothing  # clear that space


    def minSurroundingNodeValue(self, x, y):
        """
        this method looks at a node and returns the lowest value around that
        node.
        """

        # reset minimum
        self.__minimum_node = self.__reset_min
        # down
        if y < self.__height - 1:
            if self.__map[y + 1][x] < self.__minimum_node and \
                self.__map[y + 1][x] != self.__nothing:
                # find the lowest number node, and exclude empty nodes (0's)
                self.__minimum_node = self.__map[y + 1][x]
                self.__min_node_location = 3
        # up
        if y > 0:
            if self.__map[y - 1][x] < self.__minimum_node and \
                self.__map[y - 1][x] != self.__nothing:
                self.__minimum_node = self.__map[y - 1][x]
                self.__min_node_location = 1
        # right
        if x < self.__width - 1:
            if self.__map[y][x + 1] < self.__minimum_node and \
                self.__map[y][x + 1] != self.__nothing:
                self.__minimum_node = self.__map[y][x + 1]
                self.__min_node_location = 2
        # left
        if x > 0:
            if self.__map[y][x - 1] < self.__minimum_node and \
                self.__map[y][x - 1] != self.__nothing:
                self.__minimum_node = self.__map[y][x - 1]
                self.__min_node_location = 4
        return self.__minimum_node


    def printMap(self):
        """
        Prints out the map of this instance of the class.
        """

        msg = ''
        for temp_B in range(0, self.__height):
            for temp_A in range(0, self.__width):
                if self.__map[temp_B][temp_A] == self.__wall:
                    msg += "%04s" % "[#]"
                elif self.__map[temp_B][temp_A] == self.__robot:
                    msg += "%04s" % "-"
                elif self.__map[temp_B][temp_A] == self.__goal:
                    msg += "%04s" % "G"
                else:
                    msg += "%04s" % str(self.__map[temp_B][temp_A])
            msg += "\n\n"
        msg += "\n\n"
        print msg
                #
        if self.__slow == True:
            time.sleep(0.05)


    def resetmap(self, irobot_posn, goal_posn):
        """
        clears path
        """

        for y in range(0, self.__height):
            for x in range(0, self.__width):
                if self.__map[y][x] != self.__wall:  # if this location is a wall just ignore it
                    self.__map[y][x] = self.__nothing  # clear that space

        # robot and goal location was deleted, store original robot location on map
        self.__map[irobot_posn[1]][irobot_posn[0]] = self.__robot
        self.__map[goal_posn[1]][goal_posn[0]] = self.__goal
        self.setRobotPosition(irobot_posn[1], irobot_posn[0])
        self.setGoalPosition(goal_posn[1], goal_posn[0])


def timelimit(timeout, func, args=(), kwargs={}):
    """ Run func with the given timeout. If func didn't finish running
    within the timeout, raise TimeLimitExpired
    """
    class FuncThread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.result = None

        def run(self):
            self.result = func(*args, **kwargs)

    it = FuncThread()
    it.start()
    it.join(timeout)
    if it.isAlive():
        return False
    else:
        return True


def change_orientation(head,goal,bot):
    # Left 0, Up 1, Right 2, Down 3
    # 0-0 0-1 0-2 0-3:   0 -1 -2 -3
    # 1-0,1-1 1-2 1-3:   1  0 -1 -2
    # 2-0 2-1 2-2 2-3:   2  1  0 -1
    # 3-0 3-1 3-2 3-3:   3  2  1  0

    print "in change_ori, head, goal: " + str(head) +" " + str(goal)

    result = head - goal

    if result == -3 or result == 1:
        bot_rotate(bot, -90)
    elif result == -2 or result == 2:
        #-180
        bot_rotate(bot, 180)
    elif result == -1 or result == 3:
        #90
        bot_rotate(bot, 90)
    elif result == 0:
        pass

def bot_rotate(bot, orientate):
    print "orientate "+ str(orientate)
    # bot.digit_led_ascii(dashboard.mode.get()[:4].rjust(4))
    timelimit(1, bot.get_packet, (20,), {})  # resets angle counter
    angle = 0
    if orientate > 0: bot.drive(40, -1)  # anti-clockwise
    if orientate < 0: bot.drive(40, 1)  # clockwise
    while angle < abs(orientate ) + 10:
        timelimit(1, bot.get_packet, (20,), {})
        angle = angle + abs(bot.sensor_state['angle'])
        time.sleep(.02)  # irobot updates sensor and internal state variables every 15ms
        print angle
    print "stop"


    bot.drive(0, 32767)  # stop


def cleaning(bot):
    # args: start, room1_martix, room_info
    # this part need more modification
    #start = room_martix[2, 0]
    robot_y = 1
    robot_x = 1



    # fake
    # room_martix = [
    #     [999,999,999,999,999,999,999],
    #     [999,000,000,000,000,999,999],
    #     [999,000,000,000,000,000,999],
    #     [999,000,000,000,000,000,999],
    #     [999,000,000,000,000,999,000],
    #     [999,000,000,000,000,'aaa',000],
    #     [999,999,999,999,999,999,000]
    # ]

    room_martix = [[999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999,
      999],
     [999, 254, 000, 000, 000, 000, 000, 999, 000, 000, 000, 999, 000, 000, 000, 999, 000, 000, 000, 000, 000, 999,
      999],
     [999, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 'b', 001, 000, 000, 000, 000, 999,
      999],
     [999, 999, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 999,
      999],
     [999, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 999, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000,
      999],
     [999, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000,
      999],
     [999, 000, 000, 000, 000, 000, 000, 'a', 000, 000, 000, 000, 000, 000, 000, 999, 000, 000, 000, 000, 000, 000,
      999],
     [999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999,
      999]]

    # orientation Down
    head = 3
    robot_row = 1
    robot_col = 1



    """
    orientation = dashboard.orientation.get() # get the orientation
    if orientation == "Up":
        direct_x = x
        direct_y = y + 1
    elif orientation == "Left":
        direct_x = x - 1
        direct_y = y
    elif orientation == "Right":
        direct_x = x + 1
        direct_y = y
    elif orientation == "Down":
        direct_x = x
        direct_y = y - 1
    """

    while True:
        # and irobot is not round by obstacle
        if room_martix[robot_row][robot_col - 1] == 000:
            # if left is 0, means a grid waiting for cleaning
            # move to left
            # clean the grid
            # update the coordinate of robot
            print "turn left"
            print "head: " +str(head)
            # change_orientation(head,0, bot)
            head = 0
            print "forward"

            # bot.drive(100, 32767)
            # time.sleep(3)
            # bot.drive(0, 32767)
            # time.sleep(1)
            room_martix[robot_row][robot_col]  = -1
            robot_col = robot_col -1
            print_max(room_martix)

        elif room_martix[robot_row - 1][robot_col] == 000:
            # if up is 0
            # move to up
            # clean the grid
            # update the coordinate of robot
            print "turn up"
            print "head: " + str(head)
            # change_orientation(head, 1,bot)
            head = 1
            # bot.drive(100, 32767)
            # time.sleep(3)
            # bot.drive(0, 32767)
            # time.sleep(1)
            room_martix[robot_row][robot_col] = -1
            robot_row =robot_row -1
            print_max(room_martix)

        elif room_martix[robot_row][robot_col + 1] == 000:
            # if right is 0
            # move to right
            # clean the grid
            # update the coordinate of robot
            print "turn right"
            print "head: " + str(head)
            # change_orientation(head, 2,bot)
            head = 2
            print "forward"
            # bot.drive(100, 32767)
            # time.sleep(3)
            # bot.drive(0, 32767)
            # time.sleep(1)
            room_martix[robot_row][robot_col] = -1
            robot_col =robot_col +1
            print_max(room_martix)

        elif room_martix[robot_row + 1][robot_col] == 000:
            # if down is 0
            # move to down
            # clean the grid
            # update the coordinate of robot
            print "turn down"
            print "head: " + str(head)
            # change_orientation(head, 3,bot)
            head = 3
            print "forward"
            # bot.drive(100, 32767)
            # time.sleep(3)
            # bot.drive(0, 32767)
            # time.sleep(1)
            room_martix[robot_row][robot_col] = -1
            robot_row = robot_row +1
            print_max(room_martix)

        else:
            # the whole room is cleaned up (really?)
            # stop the irobot
            print "done"
            # bot.drive(0, 32767)
            room_martix[robot_row][robot_col] = -1
            print_max(room_martix)
            break



def print_max(maxt):

    msg = ''
    for temp_B in range(0, 8):
        for temp_A in range(0, 23):
            if maxt[temp_B][temp_A] == 000:
                msg += "%04s" % "[#]"
            # elif room_martix.__map[temp_B][temp_A] == room_martix.__robot:
            #     msg += "%04s" % "-"
            # elif room_martix.__map[temp_B][temp_A] == room_martix.__goal:
            #     msg += "%04s" % "G"
            else:
                msg += "%04s" % str(maxt[temp_B][temp_A])
        msg += "\n\n"
    msg += "\n\n"
    print msg


def iRobotTelemetry(dashboard):
    create_data = """
                {"OFF" : 0,
                 "PASSIVE" : 1,
                 "SAFE" : 2,
                 "FULL" : 3,
                 "NOT CHARGING" : 0,
                 "RECONDITIONING" : 1,
                 "FULL CHARGING" : 2,
                 "TRICKLE CHARGING" : 3,
                 "WAITING" : 4,
                 "CHARGE FAULT" : 5
                 }
                 """


    # create_dict = json.loads(create_data)
    # a timer for issuing a button command to prevent Create2 from sleeping in Passive mode
    BtnTimer = datetime.datetime.now() + datetime.timedelta(seconds=30)
    battcharging = False
    # pulse BRC pin LOW every 30 sec to prevent Create2 sleep
    # GPIO.setmode(GPIO.BCM)  # as opposed to GPIO.BOARD # Uses 'import RPi.GPIO as GPIO'
    # GPIO.setup(17, GPIO.OUT)  # pin 17 connects to Create2 BRC pin
    # GPIO.output(17, GPIO.HIGH)
    # time.sleep(1)
    # GPIO.output(17, GPIO.LOW)  # pulse BRC low to wake up irobot and listen at default baud
    # time.sleep(1)
    # GPIO.output(17, GPIO.HIGH)

    while True and not dashboard.exitflag:  # outer loop to handle data link retry connect attempts

        if dashboard.dataconn.get() == True:
            print "Map size = %i x %i" % (len(dashboard.floormap[0]), len(dashboard.floormap))
            print "iRobot position : x=%i y=%i" % (dashboard.irobot_posn[0], dashboard.irobot_posn[1])
            print "Goal position : x=%i y=%i" % (dashboard.goal_posn[0], dashboard.goal_posn[1])
            print "Attempting data link connection at %s" % time.asctime(time.localtime(time.time()))

            if dashboard.rundemo:
                print "Running Wavefront Demo"



                floorplan.run(dashboard, bot, return_path=False, prnt=True, demo=True)

                # floorplan.run(dashboard, return_path=False, prnt=True, demo=True)

                dashboard.rundemo = False
                dashboard.map_place_piece("irobot", dashboard.irobot_posn[1],dashboard.irobot_posn[0])
                dashboard.map_place_piece("goal", dashboard.goal_posn[1],dashboard.goal_posn[0])

            dashboard.comms_check(-1)
            dashboard.master.update()

            bot = 0
            # bot = create2api.Create2()
            # bot.digit_led_ascii('    ')  # clear DSEG before Passive mode
            print "Issuing a Start()"
            # bot.start()  # issue passive mode command
            # bot.safe()
            dist = 0  # reset odometer

            while True and not dashboard.exitflag:

                try:
                    # this binding will cause a map refresh if the user interactively changes the window size
                    dashboard.master.bind('<Configure>', dashboard.on_map_refresh)
                    floorplan = WavefrontMachine(dashboard.floormap, dashboard.irobot_posn, dashboard.goal_posn, False)
                    # check if serial is communicating
                    time.sleep(0.25)

                    # if timelimit(1, bot.get_packet, (100,), {}) == False:  # run bot.get_packet(100) with a timeout
                    #     print "Data link down"

                    # else:
                    # DATA LINK
                    if dashboard.dataconn.get() == True:
                        print "Data link up"
                        dashboard.dataconn.set(False)

                    if dashboard.rbcomms.cget('state') == "normal":  # flash radio button
                        dashboard.comms_check(-1)
                    else:
                        dashboard.comms_check(1)

                    # WAVEFRONT
                    current_date = time.strftime("%Y %m %d")


                    if dashboard.runClean:
                        print "running clean room " + dashboard.roomNumber.get()
                        cleaning(bot)
                        dashboard.runClean = False

                    if dashboard.rundemo:
                        print "Running Wavefront Demo"
                        floorplan.run(dashboard, bot, return_path=False, prnt=True,demo=True)
                        dashboard.rundemo = False
                        dashboard.map_place_piece("irobot", dashboard.irobot_posn[1], dashboard.irobot_posn[0])
                        dashboard.map_place_piece("goal", dashboard.goal_posn[1], dashboard.goal_posn[0])


                    # command a 'Dock' button press (while docked) every 30 secs to prevent Create2 sleep(BRC pin pulse not working for me)
                    # pulse BRC pin LOW every 30 secs to prevent Create2 sleep when undocked
                    if datetime.datetime.now() > BtnTimer:
                        # GPIO.output(17, GPIO.LOW)
                        print 'BRC pin pulse 1'
                        BtnTimer = datetime.datetime.now() + datetime.timedelta(seconds=30)

                    # print 'BRC pin pulse 1426'
                    # OI MODE

                    # print 'BRC pin pulse 2'



                    # print 'BRC pin pulse 3'


                    # print 'BRC pin pulse 4'


                    # if bot.sensor_state['charging sources available']['home base']:
                    #     dashboard.docked = True
                    #     dashboard.powersource.set('Home Base')
                    # else:
                    #     dashboard.docked = False
                    #     dashboard.powersource.set('Battery')

                    # print 'BRC pin pulse 5'


                    # if abs(bot.sensor_state['distance']) > 5: dashboard.docked = False

                    # dist = dist + abs(bot.sensor_state['distance'])

                    # 7 SEGMENT DISPLAY
                    # bot.digit_led_ascii("abcd")
                    # bot.digit_led_ascii(dashboard.mode.get()[:4].rjust(4))  # rjustify and pad to 4 chars

                    dashboard.master.update()  # inner loop to update dashboard telemetry

                except Exception:  # , e:
                    print "Aborting telemetry loop"
                    # print sys.stderr, "Exception: %s" % str(e)
                    traceback.print_exc(file=sys.stdout)
                    break

        dashboard.master.update()
        time.sleep(0.5)  # outer loop to handle data link retry connect attempts

    # if bot.SCI.ser.isOpen(): bot.power()
    # GPIO.cleanup()
    dashboard.master.destroy()  # exitflag = True


def main():
    # declare objects
    root = Tk()

    dashboard = Dashboard(root)  # paint GUI


    iRobotTelemetry(dashboard)  # comms with iRobot
    # root.update_idletasks() # does not block code execution
    # root.update([msecs, function]) is a loop to run function after every msec
    # root.after(msecs, [function]) execute function after msecs

    root.mainloop()  # blocks. Anything after mainloop() will only be executed after the window is destroyed

if __name__ == '__main__':
    main()
