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
from GlobalVariables import NewStateEnum, NewStatusEnum, UtilizationList, UtilizationStateList

class BottleLine:

    """
    Packaging of bottled beer typically involves drawing the product from a holding tank (Bright Tank) and filling it into bottles in a filling machine (filler), 
    which are then capped, labeled and packed into cases or cartons.

    Operational sequence steps: 
    
    1) The Bottle Line begins in the Ready/Idle state 
    2) When the Bright Tank 301-305 Allocates a Bottle Line (this asset) it will transition to Running/Draining status and the Bottling Line will transition to Ready/Filling
    3) Once the Bright Tank Draining is completed, the Bottle Line moves to Running/Holding, then quickly to Running/Draining
    4) After Running/Draining is completed, the Bottle Line moves to Done/Draining, then back to Ready/Idle (Step 1) for next production run   

    Equipment OEE:

    In parallel to the above Operational sequence steps, every one minute the Bottle Line checks to see if it should go into a "Downtime" state (which 
    affects the Availability measurement of OEE). By default the Bottle Line is set to have 98% uptime (self.PerformanceTargetPercent).  If it is 
    determined (randomly) that the Bottle Line should go to a Downtime state, the machine is set to Running/Paused and a Utilization State 
    is set to a random value of ('Demand','Downtime','Maintenance') and Utilization is set to a random value of ('No Orders','Starved Supply','Running (Slow)',
    'Unknown','EStop','Sticking Valve','Pump Overload','Faulty Wiring','Tripped Breaker','Planned Maintenance', 'Unplanned Maintenance') for 
    a randomly selected amount of time (97-600 seconds).  Once the downtime is complete all states go back to runtime.  The Attribute/Measurement 
    "BottlePV" serves as the Good Count and the Attribute "Scrap" serves as the Bad Count for the Quality measurement of OEE.   

    Dependencies (Asset material transfers & data handshaking)
    ----------

    Upstream - The Bottle Line (this asset) needs to be in Ready/Idle for Bright Tank (301-305) to Allocate then Drain
    Downstream - None    

    Attributes (exposed to OPC UA Client)
    ----------    

    AllocatedFrom (The Bright Tank (301-305) that allocated this Bottle Line)
    BeerPV (Beer Process Variable Actual received )
    BottlePV (Number of Bottles Filled)
    BottleSP (Number of Desired Bottles to be Filled)
    Cons_Beer_FromLot (Consumed Beer inventory lot/location attained from)
    Cons_Beer_Item (Consumed Beer Item/Material)
    Cons_Bottle_FromLot (Consumed Empty Bottle inventory lot/location attained from)
    Cons_Bottle_Item (Consumed Emtpy Bottle Item/Material)
    Cons_Cap_FromLot (Consumed Caps inventory lot/location attained from)
    Cons_Cap_Item (Consumed Caps Item/Material)
    Cons_Label_FromLot (Consumed Labels inventory lot/location attained from)
    Cons_Label_Item (Consumed Label Item/Material)
    LevelPV (Level Process Variable in %)
    MaterialID (Current item being produced - Passed from Bright Tank (301-305)->BottleLine (401-403) during Draining->Filling)
    Prod_BottledBeer_Item (Produced Bottled Beer Item/Material)
    Prod_BottledBeer_ToLot (Produced Bottled Beer To inventory Lot/Location)
    ProductionID (Current Production/Work Order to make Beer, from wort to bottled beer - passed from Bright Tank during Draining)
    SpeedPV (Line Speed Process Variable Actual)
    SpeedSP (Line Speed Setpoint Desired)
    TemperaturePV (Temperature Process Variable Actual) 
    TemperatureSP (Temperature Setpoint Desired)
    HoldTime.PT (Holdtime Timer Preset Time)
    HoldTime.ET (Holdtime Timer Elapsed Time)
    NewState (Machine State - "Done", "Ready", "Running", "Paused" (Downtime), "Aborted")
    NewStatus (Machine Status - "Idle", "Allocated", "Filling", "Holding", "Draining")      
    UtilizationState ('Demand','Downtime','Maintenance')
    Utilization ('No Orders','Starved Supply','Running (Slow)','Unknown','EStop','Sticking Valve','Pump Overload',
                 'Faulty Wiring','Tripped Breaker','Planned Maintenance','Unplanned Maintenance')        
    Scrap (How much material loss due to an equipment downtime condition)

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
        self.StorageShipComplete = False
        self.LabelJam = False
        self.CapperJam = False
        self.BottleBroken = False
        self.ReadyOS = False
        self.FillingOS = False
        self.SpeedPV = 0.0
        self.SpeedSP = 1000        
        self.BottlePV = 0
        self.BottleSP = 2000
        self.CapPV = 0
        self.LabelPV = 0
        self.ScanDelta = 0.0
        self.Scrap = 0.0
        self.newScrap = 0.0        
        self.BeerPV = 0.0
        self.LevelPV = 0.0
        self.BeerShippedFromStorage = 0.0
        self.TemperaturePV = 0.0
        self.newMax = 0.0
        self.newMin = 0.0
        self.TemperatureSP = 0
        self.BeerShipped = 0
        self.BottleFraction = 0
        self.CapFraction = 0
        self.LabelFraction = 0
        self.BottlesUsed = 0
        self.ScanTime = 100
        self.PerformanceTargetPercent = 98
        self.AllocatedFrom = -1
        self.ProductionID = ""
        self.Next_ProductionID = ""
        self.MaterialID = ""
        self.Next_ItemID = ""
        self.Cons_Beer_Item = ""
        self.Cons_Beer_FromLot = ""
        self.Prod_BottledBeer_Item = ""
        self.Prod_BottledBeer_ToLot = ""
        self.Cons_Bottle_Item = ""
        self.Cons_Bottle_FromLot = ""
        self.Cons_Cap_Item = ""
        self.Cons_Cap_FromLot = ""
        self.Cons_Label_Item = ""
        self.Cons_Label_FromLot = ""

        self.NewState = NewStateEnum.Ready
        self.NewStatus = NewStatusEnum.Idle
        self.UtilizationState = "Runtime"
        self.Utilization = "Running (Normal)"

        # Create contained assets
        self.HoldTime = Timer("HoldTime")
        self.SettleTime = Timer("SettleTime")
        self.CheckDownTime = Timer("CheckDownTime")
        self.DownTime = Timer("DownTime")
        self.ChillWaterValve = Valve("ChillWaterValve")
        self.InletValve = Valve("InletValve")
        self.OutletValve = Valve("OutletValve")
        self.OutletPump = Motor("OutletPump")

        self.SettleTime.PT = randint(10,25)

        # Set timer for 1 minute to check for random downtime event
        self.CheckDownTime.PT = 60

    # Run method to simulate equipment data 
    def Run(self):        

        if self.StartCmd:
            self.StartCmd = False
            if (self.NewState == NewStateEnum.Ready) and (self.NewStatus == NewStatusEnum.Holding):
                
                #                     % in tank       max in tank   oz   oz per bottle
                self.newMax = int((((self.LevelPV / 100) * 4400) * 128) / 12.6)
                self.newMin = int(self.newMax * 0.9)

                self.BottleSP = randint(self.newMin, self.newMax)                
                
                self.NewState = NewStateEnum.Running
                self.NewStatus = NewStatusEnum.Draining

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
                self.SpeedPV = 0.0
                self.HoldTime.Enabled = False
                self.ChillWaterValve.CmdOpen = False
                self.InletValve.CmdOpen = False
                self.OutletValve.CmdOpen = False
                self.OutletPump.CmdStart = False                

            case NewStateEnum.Done:     
                self.SpeedPV = 0.0
                self.HoldTime.Enabled = False
                self.ChillWaterValve.CmdOpen = False
                self.InletValve.CmdOpen = False
                self.OutletValve.CmdOpen = False
                self.OutletPump.CmdStart = False                
                self.ReadyOS = False
                self.AllocatedFrom = -1

                self.SettleTime.Enabled = True
                self.SettleTime.RST = False
                if (self.SettleTime.DN):

                    self.SettleTime.Enabled = False
                    self.SettleTime.RST = True                                        
                    
                    self.NewState = NewStateEnum.Ready
                    self.NewStatus = NewStatusEnum.Idle

            case NewStateEnum.Paused:
                self.CheckDownTime.Enabled = False

                if (self.BottlePV > 100) and (self.Scrap < self.BottlePV):
                    self.newScrap = self.BottlePV * 0.00001
                    self.Scrap = round(self.Scrap + self.newScrap, 2)

                self.DownTime.Enabled = True
                self.DownTime.RST = False
                if (self.DownTime.DN):
                    self.RestartCmd = True
                    self.UtilizationState = "Runtime"
                    self.Utilization = "Running (Normal)"
                    self.DownTime.RST = True

            case NewStateEnum.Ready:

                # Reset inital values for next production run
                if (not self.ReadyOS):
                    self.ReadyOS = True                    
                    self.SettleTime.RST = False
                    self.SettleTime.PT = randint(10,25)
                    self.HoldTime.RST = True
                    self.FillingOS = False                    
                    self.Scrap = 0.0                    
                    self.newScrap = 0.0                    
                    self.TemperatureSP = 70
                    self.InletValve.CmdOpen = False
                    self.OutletValve.CmdOpen = False                    
                    self.LevelPV = 0.0                    
                    self.ScanDelta = 1.2
                    self.ProductionID = ""                    
                    self.MaterialID = ""                    
                    self.Cons_Beer_Item = ""
                    self.Cons_Beer_FromLot = ""
                    self.Prod_BottledBeer_Item = ""
                    self.Prod_BottledBeer_ToLot = ""
                    self.Cons_Bottle_Item = ""
                    self.Cons_Bottle_FromLot = ""
                    self.Cons_Cap_Item = ""
                    self.Cons_Cap_FromLot = ""
                    self.Cons_Label_Item = ""
                    self.Cons_Label_FromLot = ""                    

                    self.HoldTime.PT = randint(5,12)
                
                self.BottlePV = 0
                self.BeerShipped = 0
                self.BottleFraction = 0
                self.CapFraction = 0
                self.LabelFraction = 0
                self.BottlesUsed = 0

                if (self.NewStatus != NewStatusEnum.Filling) and (self.NewStatus != NewStatusEnum.Holding):                    
                    self.BeerPV = 0.0

                if (self.NewStatus == NewStatusEnum.Filling):

                    if (not self.FillingOS):
                        self.FillingOS = True                        
                        # Measures passed from upstream from Storage Tank Asset
                        self.MaterialID = "{0}{1}".format(self.Next_ItemID, " Bottles")
                        self.Prod_BottledBeer_Item = self.MaterialID
                        self.ProductionID = self.Next_ProductionID                

                        now = datetime.datetime.now()
                        self.Prod_BottledBeer_ToLot = "{0}{1}{2}".format("FB-", self.EquipmentName[-3], now.strftime("%m%d%S%M"))

                        self.Cons_Bottle_Item = "Clean Bottle"
                        self.Cons_Bottle_FromLot = "{0}{1}".format("BO-A", str(randint(1,10001)).zfill(5))

                        self.Cons_Cap_Item = "12 oz Cap"
                        self.Cons_Cap_FromLot = "{0}{1}".format("CA-A", str(randint(1,10001)).zfill(5))

                        self.Cons_Label_Item = "Dated Label"
                        self.Cons_Label_FromLot = "{0}{1}".format("LA-A", str(randint(1,10001)).zfill(5))

                        # Update speed setpoint for variety in production speed
                        self.SpeedSP = randint(700,1051)                

                    if (self.StorageShipComplete):                        
                        self.BeerShippedFromStorage = 0.0
                        self.InletValve.CmdOpen = False                        
                        self.FillingOS = False                        
                        self.NewStatus = NewStatusEnum.Holding
                    else:
                        self.InletValve.CmdOpen = True
                        self.BeerPV = round(self.BeerShippedFromStorage, 2)
                        self.TemperaturePV = 68.0

            case NewStateEnum.Running:

                if (self.LabelJam) or (self.CapperJam) or (self.BottleBroken):

                    if (self.LabelJam):
                        self.LabelFraction = self.LabelFraction + 1

                    if (self.CapperJam):
                        self.CapFraction = self.CapFraction + 1

                    if (self.BottleBroken):
                        self.BottlesUsed = self.BottlesUsed + 1

                    self.NewState = NewStateEnum.Paused
                else:
                    self.NewState = NewStateEnum.Running

                match self.NewStatus:

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

                    case NewStatusEnum.Draining:

                        self.ReadyOS = False
                        
                        # Temperature Control
                        if (self.TemperaturePV > self.TemperatureSP):
                            self.ChillWaterValve.CmdOpen = True

                        if (self.TemperaturePV <= self.TemperatureSP):
                            self.ChillWaterValve.CmdOpen = False

                        if (self.ChillWaterValve.OLS):
                            self.TemperaturePV = self.TemperaturePV - abs(self.ScanDelta * 0.05) 

                        if (self.ChillWaterValve.CLS):
                            self.TemperaturePV = self.TemperaturePV + abs(self.ScanDelta * 0.001)

                        # Drain the Beer
                        self.OutletValve.CmdOpen = True

                        if (self.BeerPV >= 0.0) and (self.OutletValve.OLS):
                            self.OutletPump.CmdStart = True

                            self.BottleFraction = round(self.BottleFraction + ((self.SpeedPV/60000) * self.ScanTime), 2)
                            self.BottlePV = int(self.BottleFraction)

                            self.CapFraction = round(self.CapFraction + ((self.SpeedPV/60000) * self.ScanTime), 2)
                            self.CapPV = int(self.CapFraction)

                            self.LabelFraction = round(self.LabelFraction + ((self.SpeedPV/60000) * self.ScanTime), 2)
                            self.LabelPV = int(self.LabelFraction)

                            self.BeerShipped = self.BeerShipped + (((self.SpeedPV/60000 * self.ScanTime) * 0.09375))
                            self.BeerPV = round(self.BeerPV - ((((self.SpeedPV/60000) * self.ScanTime) * 0.09375) + 0.001137), 2)
                        else:
                            self.OutletPump.CmdStart = False

                        if (self.BeerPV <= 0.0):
                            self.BeerPV = 0.0

                        if (self.BottlePV >= self.BottleSP):                            
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

        if (self.BeerShippedFromStorage > 0.0) and (not self.StorageShipComplete):            
            self.NewStatus = NewStatusEnum.Filling
        
        if (self.NewState == NewStateEnum.Ready) and (self.NewStatus == NewStatusEnum.Holding):            
            self.StartCmd = True

        if (self.ChillWaterValve.CmdOpen == False) and (self.TemperaturePV >= self.TemperatureSP):
            self.TemperaturePV = round(self.TemperaturePV + self.ScanDelta * 0.001, 2)

        # Create level from volume - the Bottling Tank is assumed to be 10' in diameter and 7' tall. 
        # This is a 4,400 GAL tank. Level will be normalized 0-100%
        self.LevelPV = round(self.BeerPV / 4400 * 100, 2) 

        # Line Speed Simulation
        if (self.NewState == NewStateEnum.Running):
            if (self.SpeedPV <= self.SpeedSP):
                self.SpeedPV = round(self.SpeedPV + (abs(self.SpeedPV - self.SpeedSP) / 100), 2)
            else:
                if (self.SpeedPV >= 0):
                    self.SpeedPV = self.SpeedPV - self.SpeedPV / 10
                else:
                    self.SpeedPV = 0.0

        if (self.NewState == NewStateEnum.Ready) and (self.NewStatus == NewStatusEnum.Allocated) and (self.AllocatedFrom == -1):            
            self.NewStatus = NewStatusEnum.Idle

        # Run contained objects
        self.HoldTime.Run()
        self.SettleTime.Run()
        self.DownTime.Run()
        self.CheckDownTime.Run()
        self.OutletPump.Run()       
        self.InletValve.Run()
        self.OutletValve.Run()
        self.ChillWaterValve.Run() 