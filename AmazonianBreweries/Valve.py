#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#----------------------------------------------------------------------------
# Created By  : Nick Santucci @nictooch
# Created Date: February 14 2022 
# version ='1.0.0'
# ---------------------------------------------------------------------------

class Valve:    

    """

    Class Overview
    ----------

    A class used to represent a "Valve" that are used to regulate liquids, gases, and slurries. The flow of 
    liquids or gases can be controlled using these valves. This can be done through pipes and other passageways 
    by opening, closing, and partially obstructing the passageway or pipe.           

    Attributes
    ----------    

    CmdOpen (When set "True" used to turn Valve to "Open", set "False" to turn Valve to "Closed")    
    PV (Valve Process Variable Actual, "Opened" when CmdOpen is True, "Closed" when CmdStart is False, and "InTransition" when traveling in between)
    CLS (Closed Limit Switch)
    OLS (Open Limit Switch)

    Methods
    -------

    __init__(self, EquipmentName) - Class Constructor
    Run(self) - method to simulate equipment data

    """

    # Class Constructor
    def __init__(self, EquipmentName):
        
        self.EquipmentName = EquipmentName 
        self.CmdOpen = False
        self.presentPosition = 0
        self.PV = ""
        self.CLS = False
        self.OLS = False

    # Run method to simulate equipment data 
    def Run(self):
    
        if self.CmdOpen:
            if (self.presentPosition <= 20):
                self.presentPosition = self.presentPosition + 8
                self.CLS = False
                self.OLS = False
                self.PV = "InTransition"
            else:
                self.OLS = True
                self.PV = "Opened"
        else:
            if (self.presentPosition >= 0):
                self.presentPosition = self.presentPosition - 8
                self.CLS = False
                self.OLS = False
                self.PV = "InTransition"
            else:
                self.CLS = True
                self.PV = "Closed"