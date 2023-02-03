#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#----------------------------------------------------------------------------
# Created By  : Nick Santucci
# Created Date: February 14 2022 
# version ='0.1.0'
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import datetime
import random
from random import randint, choice
from Motor import Motor
from Timer import Timer
from pidLoop import pidLoop
from GlobalVariables import NewStateEnum, NewStatusEnum, UtilizationList, UtilizationStateList

class Roaster:    

    """

    Class Overview
    ----------

    A class used to represent a "Roaster" equipment asset that consumes raw barley, roasts the barley, and produces roasted barley.  
    The produced material, Raw Barley, goes to an inventory lot/location, and then is consumed by the downstream 
    MashTun (100/200) equipment asset.           

    Raw barley is heated in a roaster to temperatures of up to 230°C until the desired color is reached.

    Roasted barley is most closely associated with stouts and is almost a prerequisite for brewing stouts. 
    Occasionally roasted barley is used in porters but almost always along with caramel malts and chocolate malt 
    to balance out any coffee like roastiness.  Another attribute that roasted barley provides is that when 
    used in small amounts it imparts a deep mahogany red to a beer so red ales often see a small amount of 
    roasted barley in the grain bill.

    Operational sequence steps: 
    
    1) The Roaster begins in the Ready/Idle state 
    2) Automatically transitions to Running/Filling where Raw Barley is pushed into the Roaster by the MaltAuger motor
    3) Once the malt fill (lbs) setpoint is reached it moves to Running/RampingUp where gas is used to heat up the temperature
    4) Once the temperature setpoint is reached, it moves to Running/Holding (360-720 seconds) to allow barley to roast
    5) Once the HoldTime preset is reached, it moves to Running/RampingDown where the temperature is brought to a safe level (100 Deg F)
    6) Once the temperature is at a safe level, it moves to Running/Done, then back go Ready/Idle (Step 1) for next production run

    Equipment Utilization (Availability component of OEE):

    In parallel to the above Operational sequence steps, every one minute the Roaster checks to see if it should go into a "Downtime" state.
    By default the Roaster is set to have 98% uptime (self.PerformanceTargetPercent).  If it is determined (randomly) that
    the Roaster should go to a Downtime state, the machine is set to Running/Paused and a Utilization State is set to a random value of 
    ('Demand','Downtime','Maintenance') and Utilization is set to a random value of ('No Orders','Starved Supply','Running (Slow)',
    'Unknown','EStop','Sticking Valve','Pump Overload','Faulty Wiring','Tripped Breaker','Planned Maintenance',
    'Unplanned Maintenance') for a randomly selected amount of time (97-600 seconds).  Once the downtime is complete all states go
    back to runtime.  

    Dependencies (Asset material transfers & data handshaking)
    ----------

    Upstream - None
    Downstream - None

    Attributes (exposed to OPC UA Client)
    ----------    

    MaltPV (Malt Process Variable Actual)
    MaltSP (Malt Setpoint Desired)
    TemperaturePV (Temperature Process Variable Actual)
    TemperatureSP (Temperature Setpoint Desired)
    HoldTime.PT (Holdtime Timer Preset Time)  
    HoldTime.ET (Holdtime Timer Elapsed Time)
    NewState (Machine State - "Done", "Ready", "Running", "Paused" (Downtime), "Aborted")
    NewStatus (Machine Status - "Idle", "Filling", "Ramping Up", "Holding", "Ramping Down")
    MaterialID (Current item being produced - randomly selects 'Red','Pale','Dark','Green' Malt per production cycle)
    ProductionID (Current Production/Work Order to make Roasted Barley - randomly created per production cycle)
    Cons_RawBarley_Item (Consumed Raw Barley Item/Material)
    Cons_RawBarley_FromLot (Consumed Raw Barley inventory lot/location attained from)
    Prod_RoastedBarley_ToLot (Produced Roasted Barley To inventory Lot/Location)
    Prod_RoastedBarley_Item (Produced Roasted Barley Item/Material)
    UtilizationState ('Demand','Downtime','Maintenance')
    Utilization ('No Orders','Starved Supply','Running (Slow)','Unknown','EStop','Sticking Valve','Pump Overload',
                 'Faulty Wiring','Tripped Breaker','Planned Maintenance','Unplanned Maintenance')
    MaltAuger.PV (The MaltAuger motors actual state - Started/Stopped)
    MaltAuger.AuxContact (The MaltAuger motors auxiliary contact state - True/False)
    Scrap (How much material loss due to an equipment downtime condition)

    Methods
    -------

    __init__(self, EquipmentName) - Class Constructor
    Run(self) - method to simulate equipment data

    """

    # Class Constructor
    def __init__(self, EquipmentName):

        self.EquipmentName = EquipmentName 
        self.ScanRate = .1
        self.NewState = NewStateEnum.Ready
        self.NewStatus = NewStatusEnum.Idle
        self.UtilizationState = "Runtime"
        self.Utilization = "Running (Normal)"
        self.StartCmd = False
        self.StopCmd = False
        self.RestartCmd = False
        self.EStopCmd = False
        self.ResetCmd = False
        self.AbortCmd = False
        self.ScanTime = 100
        self.TemperatureSP = 0
        self.TemperaturePV = 1000.0 
        self.TemperatureSafe = 100.0        
        self.MaltSP = 0
        self.MaltPV = 0.0    
        self.Scrap = 0.0
        self.newScrap = 0.0
        self.PerformanceTargetPercent = 98 
        self.ProductionID = ""
        self.MaterialID = ""
        self.Cons_RawBarley_Item = ""
        self.Cons_RawBarley_FromLot = ""
        self.Prod_RoastedBarley_ToLot = ""
        self.Prod_RoastedBarley_Item = ""
        self.SelectedProduct = ""
        self.ProductNames = ['Red','Pale','Dark','Green']         

        # Create contained assets
        self.MaltAuger = Motor("MaltAuger")
        self.HoldTime = Timer("HoldTime")
        self.SettleTime = Timer("SettleTime")
        self.CheckDownTime = Timer("CheckDownTime")
        self.DownTime = Timer("DownTime")
        self.TemperatureControl = pidLoop("TemperatureControl", 0.1, 4, 1.0, 15000, 1.0)

        self.SettleTime.PT = randint(10,25)

        # Set timer for 1 minute to check for random downtime event
        self.CheckDownTime.PT = 60

    # Run method to simulate equipment data 
    def Run(self):                  
    
        if self.StartCmd:
            self.StartCmd = False
            if self.NewState == NewStateEnum.Ready:
                self.NewState = NewStateEnum.Running
                self.NewStatus = NewStatusEnum.Filling

        if self.RestartCmd:
            self.RestartCmd = False
            if self.NewState == NewStateEnum.Paused:
                self.NewState = NewStateEnum.Running

        if self.StopCmd:
            self.StopCmd = False
            if self.NewState == NewStateEnum.Running:
                self.NewState = NewStateEnum.Paused

        if self.EStopCmd:        
            if self.NewState == NewStateEnum.Running:
                self.NewState = NewStateEnum.Paused  
        
        if self.ResetCmd:    
            self.ResetCmd = False    
            if self.NewState == NewStateEnum.Done or self.NewState == NewStateEnum.Aborted:
                self.NewState = NewStateEnum.Ready

        if self.AbortCmd:
            self.AbortCmd = False
            if self.NewState == NewStateEnum.Paused:
                self.NewState = NewStateEnum.Aborted

        match self.NewState:

            case NewStateEnum.Aborted:
                # Put everything in safe state
                self.MaltPV = 0.0
                self.TemperaturePV = 80.0
                self.HoldTime.Enabled = False
                self.MaltAuger.CmdStart = False

            case NewStateEnum.Done:
                self.NewState = NewStateEnum.Ready
                self.NewStatus = NewStatusEnum.Idle
                self.HoldTime.Enabled = False
                self.SettleTime.RST = False
                self.SettleTime.PT = randint(10,25) 

            case NewStateEnum.Paused:
                self.NewState = NewStateEnum.Paused
                self.MaltAuger.CmdStart = False
                self.HoldTime.Enabled = False
                self.CheckDownTime.Enabled = False 

                if (self.MaltPV > 100) and (self.Scrap < self.MaltPV):
                    self.newScrap = self.MaltPV * 0.00001
                    self.Scrap = round(self.Scrap + self.newScrap, 2)                 

                self.DownTime.Enabled = True
                if (self.DownTime.DN):
                    self.RestartCmd = True
                    self.UtilizationState = "Runtime"
                    self.Utilization = "Running (Normal)"
                    self.DownTime.RST = True

            case NewStateEnum.Ready:
                self.NewStatus = NewStatusEnum.Idle

                # Reset inital values for next production run
                self.MaltPV = 0.0
                self.TemperatureSP = 0
                self.Scrap = 0.0
                self.newScrap = 0.0
                self.ProductionID = ""
                self.MaterialID = ""
                self.Cons_RawBarley_Item = ""
                self.Cons_RawBarley_FromLot = ""
                self.Prod_RoastedBarley_ToLot = ""
                self.Prod_RoastedBarley_Item = ""                
                self.HoldTime.RST = True

                self.SettleTime.Enabled = True
                if (self.SettleTime.DN):
                    # Randomize measurements for next Production Run                
                    self.MaltSP = randint(750,3000)
                    self.TemperatureSP = randint(430,495)
                    self.HoldTime.PT = randint(6,12) * 60   

                    #uniquePre = choice(self.ProductNames)  
                    self.SelectedProduct = choice(self.ProductNames)                
                    self.MaterialID = "{0}{1}".format(self.SelectedProduct," Malt")                    
                    self.Cons_RawBarley_Item = "{0}{1}".format(self.SelectedProduct," Barley")

                    self.Cons_RawBarley_FromLot = "{0}{1}".format("BL-A", str(randint(1,10001)).zfill(5))

                    now = datetime.datetime.now()
                    self.ProductionID = "{0}{1}{2}".format("PR-A", self.EquipmentName[-3], now.strftime("%m%d%H%S"))
                    self.Prod_RoastedBarley_ToLot = "{0}{1}{2}".format("RB-", self.EquipmentName[-3], now.strftime("%H%d%S%m"))
                    self.Prod_RoastedBarley_Item = self.MaterialID

                    self.SettleTime.Enabled = False
                    self.SettleTime.RST = True

                    self.NewState = NewStateEnum.Running
                    self.NewStatus = NewStatusEnum.Filling

            case NewStateEnum.Running:

                match self.NewStatus:

                    case NewStatusEnum.Idle:
                        # Automatically set it to the first phase, Filling
                        self.NewStatus = NewStatusEnum.Filling

                    case NewStatusEnum.Filling:
                        # Ramp up the Malt
                        if (self.MaltPV <= self.MaltSP):
                            self.MaltAuger.CmdStart = True
                        else:
                            self.MaltAuger.CmdStart = False
                            # Set to next phase in process
                            self.NewStatus = NewStatusEnum.RampingUp

                        self.HoldTime.RST = True      

                    case NewStatusEnum.RampingUp:
                        # Ramp up the Temperature
                        if (self.TemperaturePV >= self.TemperatureSP):
                            self.NewStatus = NewStatusEnum.Holding
                            self.HoldTime.RST = False

                    case NewStatusEnum.Holding:
                        self.HoldTime.Enabled = True
                        if self.HoldTime.DN:
                            self.HoldTime.Enabled = False
                            self.NewStatus = NewStatusEnum.RampingDown
                            
                    case NewStatusEnum.RampingDown:
                        # Simulate Temperature drop off to "Safe" level 
                        self.TemperaturePV = round(self.TemperaturePV - ((self.TemperaturePV - (self.TemperatureSafe - 10.0)) / (2000.0 / 99.0)), 2)

                        if (self.TemperatureSafe >= self.TemperaturePV):
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

        # Reduce the weight of the barley the longer it gets roasted above 180 Deg. (if not in paused state)
        if (self.NewState != NewStateEnum.Paused):
            if (self.TemperaturePV > 180.0):
                if (self.MaltPV > (self.MaltSP * 0.5)):
                    self.MaltPV = round(self.MaltPV - (self.TemperaturePV - 180.0) * 0.000131, 2)

            # Emulate a PI Loop
            if (self.NewStatus == NewStatusEnum.RampingUp) or (self.NewStatus == NewStatusEnum.Holding):
                self.TemperatureControl.Enabled = True                                
            else:
                self.TemperatureControl.Enabled = False

        if (self.TemperatureControl.Enabled):
            self.TemperaturePV = round(self.TemperatureControl.Run(self.TemperatureSP, self.TemperaturePV), 2)

        if (self.MaltAuger.AuxContact):
            self.MaltPV = round(self.MaltPV + ((self.ScanTime/100) * 1.1091), 2)    

        # Run contained objects
        self.MaltAuger.Run()
        self.HoldTime.Run() 
        self.SettleTime.Run() 
        self.CheckDownTime.Run()   
        self.DownTime.Run() 