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
from Valve import Valve
from pidLoop import pidLoop
from GlobalVariables import NewStateEnum, NewStatusEnum, UtilizationList, UtilizationStateList

class BrightTank:    

    """
    A Bright Tank is a dish-bottomed pressure-rated temperature-controlled tank used to hold beer in preparation for packaging. 
    The term “bright” refers to “bright beer,” beer that has been rendered bright (clear) by filtration, centrifugation, fining, 
    and/or maturation.

    Operational sequence steps: 
    
    1) The Bright Tank begins in the Ready/Idle state 
    2) When the Fermenter Allocates a Bright Tank (this asset) it will transition to Running/Draining status and the Bright Tank will transition to Running/Filling
    3) Once the Fermenter Draining is completed, the Boil Kettle moves to Running/Holding
    4) Once the HoldTime Setpoint is reached it moves to Running/Draining if the BottleLine (401-403) is in Ready/Idle, else stays in Holding
    5) After Running/Draining is completed, the Bright Tank moves to Done/Draining, then back to Ready/Idle (Step 1) for next production run   

    Equipment Utilization (Availability component of OEE):

    In parallel to the above Operational sequence steps, every one minute the BrightTank checks to see if it should go into a "Downtime" state.
    By default the BrightTank is set to have 99% uptime (self.PerformanceTargetPercent).  If it is determined (randomly) that
    the BrightTank should go to a Downtime state, the machine is set to Running/Paused and a Utilization State is set to a random value of 
    ('Demand','Downtime','Maintenance') and Utilization is set to a random value of ('No Orders','Starved Supply','Running (Slow)',
    'Unknown','EStop','Sticking Valve','Pump Overload','Faulty Wiring','Tripped Breaker','Planned Maintenance',
    'Unplanned Maintenance') for a randomly selected amount of time (97-600 seconds).  Once the downtime is complete all states go
    back to runtime. 

    Dependencies (Asset material transfers & data handshaking)
    ----------

    Upstream - The Bright Tank (this asset) needs to be in Ready/Idle for Fermenter to Allocate then Drain
    Downstream - The BottleLine (401-403) must be in Ready/Idle for the Bright Tank (301-305) to Allocate and be able to Drain    

    Attributes (exposed to OPC UA Client)
    ----------    

    AllocatedFrom (The Fermenter (100-200) that allocated this Bright Tank)
    ChillWaterValve.CLS (The ChillWaterValve is Closed Limit Switch)
    ChillWaterValve.OLS (The ChillWaterValve is Open Limit Switch)
    ChillWaterValve.PV (The ChillWaterValve actual state - Opened/InTransition/Closed)
    Cons_GreenBeer_FromLot (Consumed Green Beer inventory lot/location attained from)
    Cons_GreenBeer_Item (Consumed Green Beer Item/Material)
    HoldTime.PT (Holdtime Timer Preset Time)
    HoldTime.ET (Holdtime Timer Elapsed Time)
    LevelPV (Level Process Variable in %)
    MaterialID (Current item being produced - Passed from Fermenter (100-200)->BrightTank (301-305) during Draining->Filling)
    NewState (Machine State - "Done", "Ready", "Running", "Paused" (Downtime), "Aborted")
    NewStatus (Machine Status - "Idle", "Allocated", "Filling", "Holding", "Draining")
    BeerPV (Beer Process Variable Actual outflow to Bottle Line 401-403)
    BeerSP (Beer Setpoint Desired)
    InletValve.CLS (The InletValve is Closed Limit Switch)
    InletValve.OLS (The InletValve is Open Limit Switch)
    InletValve.PV (The InletValve actual state - Opened/InTransition/Closed)
    OutletPump.AuxContact (The OutletPump motors auxiliary contact state - True/False)
    OutletPump.PV (The OutletPump motors actual state - Started/Stopped)
    OutletValve.CLS (The OutletValve is Closed Limit Switch)
    OutletValve.OLS (The OutletValve is Open Limit Switch)
    OutletValve.PV (The OutletValve actual state - Opened/InTransition/Closed)
    Prod_Beer_Item (Produced Beer Item/Material)
    Prod_Beer_ToLot (Produced Beer To inventory Lot/Location)
    ProductionID (Current Production/Work Order to make Beer, from wort to bottled beer - passed from Fermenter during Draining)
    TemperaturePV (Temperature Process Variable Actual)
    TemperatureSP (Temperature Setpoint Desired)
    UtilizationState ('Demand','Downtime','Maintenance')
    Utilization ('No Orders','Starved Supply','Running (Slow)','Unknown','EStop','Sticking Valve','Pump Overload',
                 'Faulty Wiring','Tripped Breaker','Planned Maintenance','Unplanned Maintenance')
    BeerShipped (Amount of Beer in LBS that was shipped to the BottlingLine 401-403)
    ShipToTank (Before the Bright Tank can drain, it must allocate a Ready/Idle Bottle Line, this indicates the target BottlingLine to drain to)

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
        self.ShipToShipCmd = False
        self.ShipToAllocated = False
        self.ShipToAutoAllocateCmd = False        
        self.FermenterShipComplete = False
        self.ShipToShipComplete = False        
        self.ReadyOS = False
        self.ShipToTank = -1
        self.AllocatedFrom = -1
        self.BeerSP = 0.0
        self.BeerPV = 0.0
        self.BeerShipped = 0.0
        self.TemperaturePV = 0.0
        self.TemperatureSP = 68
        self.ScanDelta = 1.2
        self.LevelPV = 0.0
        self.BeerShippedFromFermenter = 0.0
        self.PerformanceTargetPercent = 99
        self.ProductionID = ""
        self.Next_ProductionID = ""
        self.DownStream_ProductionID = ""
        self.MaterialID = ""
        self.Next_ItemID = ""
        self.DownStream_ItemID = ""
        self.Prod_Beer_Item = ""
        self.Prod_Beer_ToLot = ""
        self.Cons_GreenBeer_Item = ""
        self.Cons_GreenBeer_FromLot = ""
        self.NewState = NewStateEnum.Ready
        self.NewStatus = NewStatusEnum.Idle
        self.UtilizationState = "Runtime"
        self.Utilization = "Running (Normal)"

        # Create contained assets
        self.HoldTime = Timer("HoldTime")
        self.SettleTime = Timer("SettleTime")
        self.DownTime = Timer("DownTime")
        self.CheckDownTime = Timer("CheckDownTime")
        self.OutletPump = Motor("OutletPump")
        self.InletValve = Valve("InletValve")
        self.OutletValve = Valve("OutletValve")
        self.ChillWaterValve = Valve("ChillWaterValve")
        self.TemperatureControl = pidLoop("TemperatureControl", 0.1, 0.25, 1.0, 5.0, 1.0)

        self.SettleTime.PT = randint(5,10)
        self.HoldTime.PT = randint(5,10) * 60

        # Set timer for 1 minute to check for random downtime event
        self.CheckDownTime.PT = 60

    # Run method to simulate equipment data 
    def Run(self):        

        if self.StartCmd:
            self.StartCmd = False
            if (self.NewState == NewStateEnum.Ready) and (self.NewStatus == NewStatusEnum.Allocated):
                # Measures passed from upstream Fermenter Asset
                self.MaterialID = "{0}{1}".format("Beer ", self.Next_ItemID)
                self.Prod_Beer_Item = self.MaterialID
                self.ProductionID = self.Next_ProductionID

                self.DownStream_ItemID = self.Next_ItemID
                self.DownStream_ProductionID = self.ProductionID

                now = datetime.datetime.now()
                self.Prod_Beer_ToLot = "{0}{1}{2}".format("MB-", self.EquipmentName[-3], now.strftime("%m%d%S%M"))             
                
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
                self.NewStatus = NewStatusEnum.Idle

            if (self.NewStatus == NewStatusEnum.Allocated):
                self.NewStatus = NewStatusEnum.Idle

        if self.AbortCmd:
            self.AbortCmd = False
            if self.NewState == NewStateEnum.Paused:
                self.NewState = NewStateEnum.Aborted

        match self.NewState:

            case NewStateEnum.Aborted:
                self.BeerSP = 5000.0
                self.BeerPV = 0.0
                self.BeerShipped = 0.0
                self.HoldTime.Enabled = False
                self.ShipToShipCmd = False
                self.ShipToAllocated = False
                self.ShipToAutoAllocateCmd = False
                self.InletValve.CmdOpen = False
                self.OutletValve.CmdOpen = False
                self.OutletPump.CmdStart = False                

            case NewStateEnum.Done:                  
                self.InletValve.CmdOpen = False
                self.OutletValve.CmdOpen = False
                self.OutletPump.CmdStart = False                               
                self.ChillWaterValve.CmdOpen = False
                self.HoldTime.Enabled = False                 
                self.BeerShippedFromFermenter = 0.0  
                self.BeerPV = 0.0
                self.ShipToAllocated = False
                self.ShipToShipCmd = False
                self.ShipToShipComplete = False
                self.HoldTime.RST = True
                self.BeerSP = 5000.0 
                self.TemperatureSP = 70
                self.TemperaturePV = 70.0
                self.LevelPV = 0.0                
                self.HoldTime.RST = True
                self.BeerShipped = 0.0
                self.ShipToTank = -1 
                self.AllocatedFrom = -1    
                self.ProductionID = ""
                self.MaterialID = ""
                self.Prod_Beer_Item = ""
                self.Prod_Beer_ToLot = ""
                self.Cons_GreenBeer_Item = ""
                self.Cons_GreenBeer_FromLot = ""                         

                self.SettleTime.RST = False
                self.SettleTime.Enabled = True                
                if (self.SettleTime.DN):

                    self.SettleTime.Enabled = False
                    self.SettleTime.RST = True
                       
                    self.SettleTime.PT = randint(5,10)
                    self.HoldTime.PT = randint(7,13) * 60                    

                    self.NewState = NewStateEnum.Ready                    

            case NewStateEnum.Paused:                
                self.CheckDownTime.Enabled = False                
                self.InletValve.CmdOpen = False
                self.OutletPump.CmdStart = False
                self.OutletValve.CmdOpen = False
                self.HoldTime.Enabled = False                

                self.DownTime.Enabled = True
                if (self.DownTime.DN):
                    self.RestartCmd = True
                    self.UtilizationState = "Runtime"
                    self.Utilization = "Running (Normal)"
                    self.DownTime.RST = True

            case NewStateEnum.Ready:
                self.ScanDelta = 1.2                              

            case NewStateEnum.Running:

                match self.NewStatus:

                    case NewStatusEnum.Allocated:
                        self.ReadyOS = False                        
                        self.NewStatus = NewStatusEnum.Filling

                    case NewStatusEnum.Filling:
                        
                        if (not self.FermenterShipComplete):
                            self.InletValve.CmdOpen = True
                            self.BeerPV = round(self.BeerShippedFromFermenter, 2)
                            self.TemperaturePV = round(68.0 + 99, 2)
                        else:
                            self.BeerPV = round(self.BeerShippedFromFermenter, 2)
                            self.BeerSP = self.BeerPV
                            self.InletValve.CmdOpen = False                            
                            self.HoldTime.RST = False                            
                            self.NewStatus = NewStatusEnum.Holding

                    case NewStatusEnum.Holding:
                        self.HoldTime.Enabled = True

                        if (self.TemperaturePV > self.TemperatureSP):
                            self.ChillWaterValve.CmdOpen = True

                        if (self.TemperaturePV <= self.TemperatureSP):
                            self.ChillWaterValve.CmdOpen = False

                        if (self.ChillWaterValve.OLS):
                            self.TemperaturePV = self.TemperaturePV - abs(self.ScanDelta * 0.05) 

                        if (self.ChillWaterValve.CLS):
                            self.TemperaturePV = self.TemperaturePV + abs(self.ScanDelta * 0.001)                                               

                        if (self.HoldTime.DN) and (self.ShipToAllocated) and (self.ShipToShipCmd):                            
                            self.NewStatus = NewStatusEnum.Draining
                            self.HoldTime.Enabled = False

                    case NewStatusEnum.Draining:
                        # Drain the Beer
                        if (self.BeerPV >= 0.0):
                            self.BeerPV = round(self.BeerPV - self.ScanDelta, 2)
                            self.OutletValve.CmdOpen = True
                            self.OutletPump.CmdStart = True
                            self.BeerShipped = round(self.BeerShipped + self.ScanDelta, 2)                            
                        else:
                            self.OutletValve.CmdOpen = False
                            self.OutletPump.CmdStart = False
                            self.NewState = NewStateEnum.Done
                            self.NewStatus = NewStatusEnum.Idle                            

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

                if (self.ChillWaterValve.OLS) and (self.TemperaturePV >= self.TemperatureSP):
                    self.TemperaturePV = self.TemperaturePV + self.ScanDelta * 0.001

                # Create level from volume - the Storage Tank is assumed to be 10' in diameter and 7' tall. 
                # This is a 4,400 GAL tank. Level will be normalized 0-100% 
                self.LevelPV = round(self.BeerPV / 4400.0 * 100.0, 2)


        # Run contained objects
        self.HoldTime.Run()
        self.SettleTime.Run()
        self.DownTime.Run()
        self.CheckDownTime.Run()
        self.OutletPump.Run()       
        self.InletValve.Run()
        self.OutletValve.Run()
        self.ChillWaterValve.Run() 