#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#----------------------------------------------------------------------------
# Created By  : Nick Santucci
# Created Date: February 14 2022 
# version ='1.0.0'
# ---------------------------------------------------------------------------

class Motor:  

    """

    Class Overview
    ----------

    A class used to represent a "Motor" that can serve as an agitator or pump for example, in industrial processes.           

    Attributes
    ----------    

    CmdStart (When set "True" used to turn Motor to "On", set "False" to turn Motor to "Off")
    AuxContact (When CmdStart is set "True", AuxContact is also set "true", when CmdStart is set "False", AuxContact is also set "False")
    PV (Motor Process Variable Actual, "Started" when CmdStart is True, "Stopped" when CmdStart is False)

    Methods
    -------

    __init__(self, EquipmentName) - Class Constructor
    Run(self) - method to simulate equipment data

    """  

    # Class Constructor
    def __init__(self, EquipmentName):
        
        self.EquipmentName = EquipmentName 
        self.CmdStart = False
        self.presentPosition = 0
        self.AuxContact = False
        self.PV = ""

    # Run method to simulate equipment data 
    def Run(self):
    
        if self.CmdStart:
            if (self.presentPosition <= 25):
                self.presentPosition = self.presentPosition + 8
            else:
                self.AuxContact = True
                self.PV = "Started"
        else:
            if (self.presentPosition >= 0):
                self.presentPosition = self.presentPosition - 8
            else:
                self.AuxContact = False
                self.PV = "Stopped"