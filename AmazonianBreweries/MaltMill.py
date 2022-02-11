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
import datetime
import random
from random import randint, choice
from Motor import Motor
from Timer import Timer
from GlobalVariables import NewStateEnum, NewStatusEnum, UtilizationList, UtilizationStateList

class MaltMill:    

    """
    The Malt Mill is a machine to squeezing of malt grains before the wort brewing process on 
    the brewhouse. Before starting the brewing process it is needed to crush the grain malt 
    in the prescribed manner. It means to ensure an access the grain endosperm without damaging
    their husks.

    Operational sequence steps: 
    
    1) The MaltMill begins in the Ready/Idle state 
    2) Automatically transitions to Running where Roasted Barley is pushed into the MashTun by the MaltMill MaltAuger motor
    3) Once the malt fill (lbs) setpoint is reached it moves to Running/Done, then back go Ready/Idle (Step 1) for next production run

    Equipment Utilization (Availability component of OEE):

    In parallel to the above Operational sequence steps, every one minute the MaltMill checks to see if it should go into a "Downtime" state.
    By default the MaltMill is set to have 98% uptime (self.PerformanceTargetPercent).  If it is determined (randomly) that
    the MaltMill should go to a Downtime state, the machine is set to Running/Paused and a Utilization State is set to a random value of 
    ('Demand','Downtime','Maintenance') and Utilization is set to a random value of ('No Orders','Starved Supply','Running (Slow)',
    'Unknown','EStop','Sticking Valve','Pump Overload','Faulty Wiring','Tripped Breaker','Planned Maintenance',
    'Unplanned Maintenance') for a randomly selected amount of time (97-600 seconds).  Once the downtime is complete all states go
    back to runtime. The outcome of this directly affects the MashTun (Mash.py) as the Malt Mills Utlization State and Utilization attributes
    are passed into the MashTun in the aswBrewOPCUAServer.py file.

    Dependencies (Asset material transfers & data handshaking)
    ----------

    Upstream - Dependency on the MashTun (technically integrated and work in unison), see Mash.py class for more information
    Downstream - Works in Tandem with the MashTun asset, please see Mash.py file for details    

    Attributes (exposed to OPC UA Client)
    ----------    

    MaltPV (Malt Process Variable Actual)
    MaltSP (Malt Setpoint Desired)
    MaltAuger.AuxContact (The MaltAuger motors auxiliary contact state - True/False)
    MaltAuger.PV (The MaltAuger motors actual state - Started/Stopped)
    MaltMill.AuxContact (The MaltMill motors auxiliary contact state - True/False)
    MaltMill.PV (The MaltMill motors actual state - Started/Stopped)
    NewState (Machine State - "Done", "Ready", "Running", "Paused" (Downtime), "Aborted")

    Methods
    -------
    
    __init__(self, EquipmentName) - Class Constructor
    Run(self) - method to simulate equipment data

    """

    # Class Constructor
    def __init__(self, EquipmentName):
        self.EquipmentName = EquipmentName 
        self.NewState = NewStateEnum.Ready
        self.NewStatus = NewStatusEnum.Idle
        self.UtilizationState = "Runtime"
        self.Utilization = "Running (Normal)"
        self.MaltPV = 0.0
        self.MaltSP = 0.0
        self.ScanTime = 100
        self.PerformanceTargetPercent = 98
        self.MaltMillComplete = False
        self.StartCmd = False        
        self.StopCmd = False
        self.RestartCmd = False
        self.EStopCmd = False
        self.ResetCmd = False
        self.AbortCmd = False
        self.MashTunComplete = False

        # Create contained assets
        self.MaltMill = Motor("MaltMill")
        self.MaltAuger = Motor("MaltAuger")
        self.SettleTime = Timer("SettleTime")
        self.CheckDownTime = Timer("CheckDownTime")
        self.DownTime = Timer("DownTime")

        self.SettleTime.PT = randint(10,25)

        # Set timer for 1 minute to check for random downtime event
        self.CheckDownTime.PT = 60

    # Run method to simulate equipment data 
    def Run(self):        

        if self.StartCmd:
                self.StartCmd = False
                if self.NewState == NewStateEnum.Ready:
                    self.NewState = NewStateEnum.Running

        if self.RestartCmd:
            self.RestartCmd = False
            if self.NewState == NewStateEnum.Paused:
                self.NewState = NewStateEnum.Running

        if self.StopCmd:
            self.StopCmd = False
            if self.NewState == NewStateEnum.Running:
                self.NewState = NewStateEnum.Paused

        if self.AbortCmd:
            self.AbortCmd = False
            if self.NewState == NewStateEnum.Paused:
                self.NewState = NewStateEnum.Aborted

        if self.ResetCmd:    
            self.ResetCmd = False    
            if self.NewState == NewStateEnum.Done or self.NewState == NewStateEnum.Aborted:
                self.NewState = NewStateEnum.Ready

        if self.EStopCmd:        
            if self.NewState == NewStateEnum.Running:
                self.NewState = NewStateEnum.Paused

        match self.NewState:

            case NewStateEnum.Aborted:
                # Put everything in safe state
                self.MaltMill.CmdStart = False
                self.MaltAuger.CmdStart = False
                self.MaltPV = 0.0
                self.MaltMillComplete = False

            case NewStateEnum.Done:
                self.MaltMill.CmdStart = False
                self.MaltAuger.CmdStart = False
                self.StartCmd = False
                self.SettleTime.RST = False
                self.SettleTime.PT = randint(10,25)
                self.NewState = NewStateEnum.Ready
                self.NewStatus = NewStatusEnum.Idle

            case NewStateEnum.Ready:
                self.MaltPV = 0.0
                self.NewStatus = NewStatusEnum.Idle
                self.MaltAuger.CmdStart = False
                self.MaltMill.CmdStart = False
                self.MaltMillComplete = False

                self.SettleTime.Enabled = True
                if (self.SettleTime.DN):
                    self.SettleTime.Enabled = False
                    self.SettleTime.RST = True
                    self.NewState = NewStateEnum.Running

            case NewStateEnum.Paused:
                self.MaltMill.CmdStart = False
                self.MaltAuger.CmdStart = False
                self.CheckDownTime.Enabled = False

                self.DownTime.Enabled = True
                if (self.DownTime.DN):                    
                    self.RestartCmd = True
                    self.UtilizationState = "Runtime"
                    self.Utilization = "Running (Normal)"
                    self.DownTime.RST = True

            case NewStateEnum.Running:
                if (self.MaltPV <= self.MaltSP):
                    self.MaltMill.CmdStart = True
                    self.MaltAuger.CmdStart = True
                    self.MaltPV = round(self.MaltPV + ((self.ScanTime/100) * 1.1031), 2)
                else:
                    self.MaltAuger.CmdStart = False
                    self.MaltMillComplete = True
                    if(self.MashTunComplete):
                        self.NewState = NewStateEnum.Done

                # Check for a downtime condition while running once every minute
                self.CheckDownTime.RST = False
                self.CheckDownTime.Enabled = True
                if self.CheckDownTime.DN:
                    dtNow = datetime.datetime.now()
                    random.seed(int(self.EquipmentName[-3]) + int(dtNow.strftime("%f")))
                    dtTest = random.random()
                    self.CheckDownTime.RST = True

                    if (dtTest > (self.PerformanceTargetPercent/100)):
                        # Downtime has occured, put system into pause and randomize downtime timer                        
                        self.StopCmd = True  
                        dtMin = randint(97,121)
                        dtMax = randint(173,600)
                        self.DownTime.PT = randint(dtMin,dtMax) 
                        self.DownTime.RST = False                       

                        # Assign a random dowtime for the asset
                        self.UtilizationState = choice(UtilizationStateList)

                        match self.UtilizationState:
                            case "Demand":
                                self.Utilization = UtilizationList[randint(0,2)]
                            case "Downtime":
                                self.Utilization = UtilizationList[randint(3,8)]
                            case "Maintenance":
                                self.Utilization = UtilizationList[randint(9,10)]

        # Run contained objects
        self.MaltMill.Run()
        self.MaltAuger.Run()
        self.SettleTime.Run()
        self.CheckDownTime.Run()
        self.DownTime.Run()