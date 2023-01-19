#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#----------------------------------------------------------------------------
# Created By  : Nick Santucci
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
from Valve import Valve
from pidLoop import pidLoop
from GlobalVariables import NewStateEnum, NewStatusEnum, UtilizationList, UtilizationStateList

class Fermenter: 

    """
    The Fermenter is a brewhouse vessel where yeast converts the glucose in the wort to ethyl alcohol and carbon dioxide gas
    giving the beer both its alcohol content and its carbonation. To begin the fermentation process, the cooled wort is 
    transferred into a fermentation vessel to which the yeast has already been added. If the beer being made is an ale, 
    the wort will be maintained at a constant temperature of 68 F (20 C) for about two weeks. If the beer is a lager, 
    the temperature will be maintained at 48 F (9 C) for about six weeks. Since fermentation produces a substantial amount 
    of heat, the tanks must be cooled constantly to maintain the proper temperature.

    Operational sequence steps: 
    
    1) The Fermenter begins in the Ready/Idle state 
    2) When BoilKettle is in Draining status and BoilKettle OutletPump.AuxContact is true, The Fermenter will transition to Running/Filling
    3) Once the BoilKettle Draining is completed, the Fermenter moves to Running/Holding
    4) Once the HoldTime Setpoint is reached it moves to Running/Draining if the BrightTank (301-305) is in Ready/Idle, else stays in Holding
    5) After Running/Draining is completed, it moves to Done/Draining, then back to Ready/Idle (Step 1) for next production run   

    Equipment Utilization (Availability component of OEE):

    In parallel to the above Operational sequence steps, every one minute the Fermenter checks to see if it should go into a "Downtime" state.
    By default the Fermenter is set to have 98% uptime (self.PerformanceTargetPercent).  If it is determined (randomly) that
    the Fermenter should go to a Downtime state, the machine is set to Running/Paused and a Utilization State is set to a random value of 
    ('Demand','Downtime','Maintenance') and Utilization is set to a random value of ('No Orders','Starved Supply','Running (Slow)',
    'Unknown','EStop','Sticking Valve','Pump Overload','Faulty Wiring','Tripped Breaker','Planned Maintenance',
    'Unplanned Maintenance') for a randomly selected amount of time (97-600 seconds).  Once the downtime is complete all states go
    back to runtime. 

    Dependencies (Asset material transfers & data handshaking)
    ----------

    Upstream - The Fermenter (this asset) needs to be in Ready/Idle for BoilKettle to Drain
    Downstream - The BrightTank (301-305) must be in Ready/Idle for the Fermenter to be able to Drain    

    Attributes (exposed to OPC UA Client)
    ----------    

    ChillWaterValve.CLS (The ChillWaterValve is Closed Limit Switch)
    ChillWaterValve.OLS (The ChillWaterValve is Open Limit Switch)
    ChillWaterValve.PV (The ChillWaterValve actual state - Opened/InTransition/Closed)
    Cons_BrewedWort_FromLot (Consumed Brewed Wort inventory lot/location attained from)
    Cons_BrewedWort_Item (Consumed Brewed Wort Item/Material)
    Cons_Yeast_FromLot (Consumed Yeast inventory lot/location attained from)
    Cons_Yeast_Item (Consumed Yeast Item/Material)
    HoldTime.PT (Holdtime Timer Preset Time)
    HoldTime.ET (Holdtime Timer Elapsed Time)
    LevelPV (Level Process Variable in %)
    MaterialID (Current item being produced - Passed from BoilKettle->Fermenter during Draining->Filling)
    NewState (Machine State - "Done", "Ready", "Running", "Paused" (Downtime), "Aborted")
    NewStatus (Machine Status - "Idle", "Filling", "Holding", "Draining")
    GreenBeerPV (Green Beer Process Variable Actual outflow to BrightTank 301-305)
    InletValve.CLS (The InletValve is Closed Limit Switch)
    InletValve.OLS (The InletValve is Open Limit Switch)
    InletValve.PV (The InletValve actual state - Opened/InTransition/Closed)
    OutletPump.AuxContact (The OutletPump motors auxiliary contact state - True/False)
    OutletPump.PV (The OutletPump motors actual state - Started/Stopped)
    OutletValve.CLS (The OutletValve is Closed Limit Switch)
    OutletValve.OLS (The OutletValve is Open Limit Switch)
    OutletValve.PV (The OutletValve actual state - Opened/InTransition/Closed)
    Prod_GreenBeer_Item (Produced Green Beer Item/Material)
    Prod_GreenBeer_ToLot (Produced Green Beer To inventory Lot/Location)
    ProductionID (Current Production/Work Order to make Beer, from wort to bottled beer - passed from BoilKettle during Draining)
    Scrap (How much material loss due to an equipment downtime condition)
    ShipTo_Tank (Before the Fermenter can drain, it must allocate a Ready/Idle Bright Tank, this indicates the target BrightTank to drain to)
    TemperaturePV (Temperature Process Variable Actual)
    TemperatureSP (Temperature Setpoint Desired)
    UtilizationState ('Demand','Downtime','Maintenance')
    Utilization ('No Orders','Starved Supply','Running (Slow)','Unknown','EStop','Sticking Valve','Pump Overload',
                 'Faulty Wiring','Tripped Breaker','Planned Maintenance','Unplanned Maintenance')
    YeastPV (Yeast Process Variable Actual)
    YeastSP (Yeast Setpoint Desired)
    YeastPump.AuxContact (The YeastPump motors auxiliary contact state - True/False)
    YeastPump.PV (The YeastPump motors actual state - Started/Stopped)

    Methods
    -------
    
    __init__(self, EquipmentName) - Class Constructor
    Run(self) - method to simulate equipment data

    """

    # Class Constructor
    def __init__(self, EquipmentName):

        self.EquipmentName = EquipmentName 
        self.StartCmd = False
        self.StopCmd = False
        self.RestartCmd = False
        self.EStopCmd = False
        self.ResetCmd = False
        self.AbortCmd = False
        self.BrewKettleShipComplete = False
        self.ShipToShipComplete = False
        self.ShipToShipCmd = False         
        self.ShipToAllocated = False
        self.ShipToAutoAllocateCmd = False
        self.IsSearching = False
        self.ShipTo_Tank = -1
        self.ReadyOS = False
        self.TemperaturePV = 0.0
        self.TemperatureSP = 0
        self.TemperatureSafe = 68.0
        self.GreenBeerPV = 0.0
        self.BrewedWortPV = 0.0
        self.BrewedWortSP  = 5000.0
        self.YeastPV = 0.0
        self.YeastSP = 50.0
        self.ScanDelta = 0.89
        self.LevelPV = 0.0
        self.Scrap = 0.0        
        self.newScrap = 0.0
        self.ScanTime = 100
        self.PerformanceTargetPercent = 98
        self.FermentationTime = 300
        self.ProductionID = ""
        self.Next_ProductionID = ""
        self.DownStream_ProductionID = ""
        self.MaterialID = ""
        self.Next_ItemID = ""
        self.DownStream_ItemID = ""
        self.Cons_BrewedWort_FromLot = ""
        self.Cons_BrewedWort_Item = ""
        self.Cons_Yeast_FromLot = ""  
        self.Cons_Yeast_Item = ""      
        self.Prod_GreenBeer_ToLot = ""
        self.Prod_GreenBeer_Item = ""
        self.NewState = NewStateEnum.Ready
        self.NewStatus = NewStatusEnum.Idle
        self.UtilizationState = "Runtime"
        self.Utilization = "Running (Normal)"
        self.YeastNames = ['Ale','Lager','Belgian','Wheat Beer']

        # Create contained assets
        self.HoldTime = Timer("HoldTime")
        self.SettleTime = Timer("SettleTime")
        self.DownTime = Timer("DownTime")
        self.CheckDownTime = Timer("CheckDownTime")
        self.OutletPump = Motor("OutletPump")
        self.YeastPump = Motor("YeastPump")
        self.InletValve = Valve("InletValve")
        self.OutletValve = Valve("OutletValve")
        self.ChillWaterValve = Valve("ChillWaterValve")
        self.TemperatureControl = pidLoop("TemperatureControl", 0.1, 0.25, 1.0, 5.0, 1.0)

        self.SettleTime.PT = randint(10,25)

        # Set timer for 1 minute to check for random downtime event
        self.CheckDownTime.PT = 60

    # Run method to simulate equipment data 
    def Run(self):        

        if self.StartCmd:
            self.StartCmd = False
            if self.NewState == NewStateEnum.Ready:
                # Measures passed from upstream BoilKettle Asset
                self.MaterialID = "{0}{1}".format("Green Beer ", self.Next_ItemID)
                self.Prod_GreenBeer_Item = self.MaterialID
                self.ProductionID = self.Next_ProductionID

                self.DownStream_ItemID = self.Next_ItemID
                self.DownStream_ProductionID = self.ProductionID

                uniquePre = choice(self.YeastNames)

                now = datetime.datetime.now()
                self.Prod_GreenBeer_ToLot = "{0}{1}{2}".format("GB-", self.EquipmentName[-3], now.strftime("%m%d%S%M"))  
                self.Cons_Yeast_Item = "{0}{1}".format(uniquePre," Yeast")                  
                self.Cons_Yeast_FromLot = "{0}{1}{2}".format("YL-A", self.EquipmentName[-3], now.strftime("%d%M%S%m"))

                self.NewState = NewStateEnum.Running

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
                self.GreenBeerPV = 0.0
                self.BrewKettleShipComplete = False
                self.ChillWaterValve.CmdOpen = False
                self.HoldTime.Enabled = False
                self.InletValve.CmdOpen = False
                self.OutletPump.CmdStart = False
                self.OutletValve.CmdOpen = False
                self.TemperaturePV = self.TemperatureSafe
                self.BrewedWortPV = 0.0
                self.BrewedWortSP = 5000.0
                self.YeastPV = 0.0
                self.YeastSP = 50.0
                self.ScanDelta = 0.89
                self.ShipToShipComplete = True                

            case NewStateEnum.Done:                
                self.HoldTime.Enabled = False
                self.ShipToShipComplete = True
                self.ReadyOS = False
                self.HoldTime.RST = True                

                self.SettleTime.Enabled = True
                if (self.SettleTime.DN):

                    self.SettleTime.Enabled = False
                    self.SettleTime.RST = True                                        

                    self.NewState = NewStateEnum.Ready
                    self.NewStatus = NewStatusEnum.Idle

            case NewStateEnum.Paused:                
                self.CheckDownTime.Enabled = False
                self.ChillWaterValve.CmdOpen = False
                self.InletValve.CmdOpen = False
                self.OutletPump.CmdStart = False
                self.OutletValve.CmdOpen = False
                self.HoldTime.Enabled = False

                if (self.BrewedWortPV > 100) and (self.Scrap < self.BrewedWortPV):
                    self.newScrap = self.BrewedWortPV * 0.00001
                    self.Scrap = round(self.Scrap + self.newScrap, 2)

                self.DownTime.Enabled = True
                if (self.DownTime.DN):
                    self.RestartCmd = True
                    self.UtilizationState = "Runtime"
                    self.Utilization = "Running (Normal)"
                    self.DownTime.RST = True

            case NewStateEnum.Ready:
                self.NewStatus = NewStatusEnum.Idle

                if (not self.ReadyOS):
                    # Reset inital values for next production run
                    self.ReadyOS = True
                    self.SettleTime.RST = False
                    self.SettleTime.PT = randint(10,25)
                    self.GreenBeerPV = 0.0
                    self.BrewKettleShipComplete = False
                    self.ChillWaterValve.CmdOpen = False
                    self.HoldTime.RST = True
                    self.InletValve.CmdOpen = False
                    self.OutletPump.CmdStart = False
                    self.OutletValve.CmdOpen = False
                    self.TemperatureSP = 68
                    self.TemperaturePV = self.TemperatureSafe
                    self.BrewedWortPV = 0.0
                    self.BrewedWortSP = 5000.0
                    self.YeastPV = 0.0
                    self.YeastSP = 50.0
                    self.ScanDelta = 0.89
                    self.LevelPV = 0.0
                    self.Scrap = 0.0
                    self.newScrap = 0.0
                    self.ShipToAllocated = False
                    self.ShipToAutoAllocateCmd = False
                    self.ShipToShipCmd = False
                    self.ShipToShipComplete = False                    
                    self.IsSearching = False
                    self.ProductionID = ""
                    self.MaterialID = ""
                    self.ShipTo_Tank = -1
                    self.Cons_Yeast_FromLot = ""  
                    self.Cons_Yeast_Item = ""                  
                    self.Cons_BrewedWort_Item = ""
                    self.Cons_BrewedWort_FromLot = ""
                    self.Prod_GreenBeer_ToLot = ""
                    self.Prod_GreenBeer_Item = ""

                    self.HoldTime.PT = randint(8,14) * 60                     

            case NewStateEnum.Running:

                match self.NewStatus:

                    case NewStatusEnum.Idle:
                        self.ReadyOS = False
                        self.NewStatus = NewStatusEnum.Filling

                    case NewStatusEnum.Filling:
                        # Ramp up the BrewedWort
                        if (self.BrewKettleShipComplete):
                            self.BrewedWortSP = self.BrewedWortPV
                            self.InletValve.CmdOpen = False                            
                        else:
                            self.InletValve.CmdOpen = True
                            self.TemperaturePV = 70.0

                        # Setup yeast levels to dynamically fill based on amount of brewed wort in tank 
                        self.YeastSP = round(self.BrewedWortPV * 0.0125, 2)
                        if (self.BrewedWortPV >= self.BrewedWortSP):
                            if (self.BrewedWortSP < 500.0):
                                self.YeastPV = self.YeastSP

                            if (self.YeastPV < self.YeastSP):
                                self.YeastPump.CmdStart = True
                                self.YeastPV = round(self.YeastPV + ((self.ScanTime/100) * 0.57), 2)
                            else:
                                self.YeastPump.CmdStart = False

                                if (self.HoldTime.PT <= 0):
                                    self.HoldTime.PT = self.FermentationTime

                                self.NewStatus = NewStatusEnum.Holding
                                self.HoldTime.RST = False

                    case NewStatusEnum.Holding:
                        self.HoldTime.Enabled = True

                        if (self.TemperaturePV > self.TemperatureSP):
                            self.ChillWaterValve.CmdOpen = True

                        if (self.TemperaturePV <= self.TemperatureSP):
                            self.ChillWaterValve.CmdOpen = False

                        if (self.ChillWaterValve.OLS):
                            self.TemperaturePV = self.TemperaturePV - abs(self.ScanDelta) * 0.1

                        if (self.ChillWaterValve.CLS):
                            self.TemperaturePV = self.TemperaturePV + abs(self.ScanDelta * 0.01)                        

                        if (self.HoldTime.DN) and (self.ShipToAllocated and self.ShipToShipCmd):
                            self.HoldTime.Enabled = False
                            self.NewStatus = NewStatusEnum.Draining

                    case NewStatusEnum.Draining:
                        # Drain the Beer
                        if (self.BrewedWortPV > 0.0):
                            self.OutletValve.CmdOpen = True
                            self.OutletPump.CmdStart = True
                            self.BrewedWortPV = round(self.BrewedWortPV - ((self.ScanTime/100) * 1.98), 2) 
                            self.GreenBeerPV = round(self.GreenBeerPV + ((self.ScanTime/100) * 1.93), 2)
                        else:
                            self.BrewedWortPV = 0.0
                            self.OutletValve.CmdOpen = False
                            self.OutletPump.CmdStart = False
                            self.ShipToShipComplete = True
                            self.NewState = NewStateEnum.Done

                # Check for a downtime condition while running once every minute
                self.CheckDownTime.RST = False
                self.CheckDownTime.Enabled = True
                if (self.CheckDownTime.DN) and (self.NewStatus != NewStatusEnum.Filling) and (self.NewStatus != NewStatusEnum.Draining):
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

                # Create level from volume - the Fermenter is assumed to be 10' in diameter and 7' tall. 
                # This is a 4,100 GAL tank. Level will be normalized 0-100% 
                self.LevelPV = round(self.BrewedWortPV / 4100.0 * 100.0, 2)

        # Run contained objects
        self.HoldTime.Run()
        self.SettleTime.Run()
        self.DownTime.Run()
        self.CheckDownTime.Run()
        self.OutletPump.Run()
        self.YeastPump.Run()
        self.InletValve.Run()
        self.OutletValve.Run()
        self.ChillWaterValve.Run() 