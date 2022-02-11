#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#----------------------------------------------------------------------------
# Created By  : Nick Santucci @nictooch
# Created Date: February 14 2022 
# version ='1.0.0'
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import time

class Timer:    

    """

    Class Overview
    ----------

    A class used to represent a "Timer" that can be used to delay input and output signals.  This Timer Class is modeled after 
    a "On delay" PLC timer which are used when an action is to begin a specified time after the input (Enable) becomes true. 
    For example, a certain step in the manufacturing is to begin 45 seconds after a signal is received from a limit switch. 
    The 45 seconds delay is the on-delay timers preset value.              

    Attributes
    ----------    

    Name (Name provided by calling Class)
    Enabled (Determines if the Timer will begin counting up towards the timer preset value)
    PT (Preset Time)
    ET (Elapsed Time)
    DN (Done bit, is true if PT == ET)
    RST (Reset Timer)
    
    Methods
    -------

    __init__(self, EquipmentName) - Class Constructor
    Run(self) - method to simulate equipment data

    """

    # Class Constructor
    def __init__(self, Name):
        
        self.Name = Name 
        self.t0 = 0        
        self.ET = 0
        self.PT = 0
        self.DN = False
        self.RST = False
        self.Enabled = False   
        self.EnabledOS = False     

    # Run method to execute Timer functionality 
    def Run(self):

        if (self.Enabled and (not self.EnabledOS)):
            self.t0 = int(time.time())
            self.EnabledOS = True        

        if ((not self.DN) and self.Enabled):
            # Check elpased time
            self.ET = int(time.time()) - self.t0

        if self.RST:
            self.ET = 0
            self.DN = False
            self.EnabledOS = False

        self.DN = False
        if (self.ET >= self.PT):
            self.DN = True

        if self.DN:
            self.ET = self.PT  