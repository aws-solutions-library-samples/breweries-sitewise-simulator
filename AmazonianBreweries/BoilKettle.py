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

class BoilKettle:   

    """
    The Boil Kettle is a brewhouse vessel where wort is boiled and reduced for approximately 60 to 90 minutes. During boil, 
    initial hop additions are introduced into the brewing process. After boil is complete the wort is whirlpooled to separate 
    unwanted solids from the desired liquid.

    Operational sequence steps: 
    
    1) The Boil Kettle begins in the Ready/Idle state 
    2) When MashTun is in the Draining status and MashTun OutletPump.AuxContact is true, The BoilKettle will transition to Running/Filling
    3) Once the MashTun Draining is completed, the BoilKettle moves to Running/RampingUp where steam is used to heat up the temperature
    4) Once the Temperature PV (actual temperature) reaches Temperature Setpoint it moves to Running/Holding to soak
    5) Once the HoldTime Setpoint is reached it moves to Running/RampUp2 where steam is used to heat up the temperature further 
    6) Once the HoldTime Setpoint is reached it moves to Running/Draining if the Fermenter is in Ready/Idle, else stays in Holding
    7) After Running/Draining is completed, it moves to Done/Draining, then back to Ready/Idle (Step 1) for next production run   

    Equipment Utilization (Availability component of OEE):

    In parallel to the above Operational sequence steps, every one minute the BoilKettle checks to see if it should go into a "Downtime" state.
    By default the BoilKettle is set to have 98% uptime (self.PerformanceTargetPercent).  If it is determined (randomly) that
    the BoilKettle should go to a Downtime state, the machine is set to Running/Paused and a Utilization State is set to a random value of 
    ('Demand','Downtime','Maintenance') and Utilization is set to a random value of ('No Orders','Starved Supply','Running (Slow)',
    'Unknown','EStop','Sticking Valve','Pump Overload','Faulty Wiring','Tripped Breaker','Planned Maintenance',
    'Unplanned Maintenance') for a randomly selected amount of time (97-600 seconds).  Once the downtime is complete all states go
    back to runtime. 

    Dependencies (Asset material transfers & data handshaking)
    ----------

    Upstream - The BoilKettle (this asset) needs to be in Ready/Idle for MashTun to Drain
    Downstream - The Fermenter must be in Ready/Idle for the BoilKettle to be able to Drain    

    Attributes (exposed to OPC UA Client)
    ----------    

    Cons_Hops_FromLot (Consumed Hops inventory lot/location attained from)
    Cons_Hops_Item (Consumed Hops Item/Material)         
    Cons_Wort_FromLot (Consumed Wort inventory lot/location attained from MashTun)
    Cons_Wort_Item (Consumed Hops Item/Material from MashTun)
    HoldTime.PT (Holdtime Timer Preset Time)
    HoldTime.ET (Holdtime Timer Elapsed Time)
    LevelPV (Level Process Variable in %)
    MaterialID (Current item being produced - Passed from MashTun->BoilKettle during Draining->Filling)                
    NewState (Machine State - "Done", "Ready", "Running", "Paused" (Downtime), "Aborted")
    NewStatus (Machine Status - "Idle", "Filling", "Ramping Up", "Holding", "Draining")
    OutletPump.AuxContact (The OutletPump motors auxiliary contact state - True/False)
    OutletPump.PV (The OutletPump motors actual state - Started/Stopped)
    InletValve.CLS (The InletValve is Closed Limit Switch)
    InletValve.OLS (The InletValve is Open Limit Switch)
    InletValve.PV (The InletValve actual state - Opened/InTransition/Closed)
    OutletValve.CLS (The OutletValve is Closed Limit Switch)
    OutletValve.OLS (The OutletValve is Open Limit Switch)
    OutletValve.PV (The OutletValve actual state - Opened/InTransition/Closed)
    Prod_BrewedWort_Item (Produced Brewed Wort Item/Material)
    Prod_BrewedWort_ToLot (Produced Brewed Wort To inventory Lot/Location)
    ProductionID (Current Production/Work Order to make Beer, from wort to bottled beer - passed from MashTun during Draining)
    Scrap (How much material loss due to an equipment downtime condition)
    SteamValve.CLS (The SteamValve is Closed Limit Switch)
    SteamValve.OLS (The SteamValve is Open Limit Switch)
    SteamValve.PV (The SteamValve actual state - Opened/InTransition/Closed)
    TemperaturePV (Temperature Process Variable Actual)
    TemperatureSP (Temperature Setpoint Desired)
    UtilizationState ('Demand','Downtime','Maintenance')
    Utilization ('No Orders','Starved Supply','Running (Slow)','Unknown','EStop','Sticking Valve','Pump Overload',
                 'Faulty Wiring','Tripped Breaker','Planned Maintenance','Unplanned Maintenance')
    HopsAuger.AuxContact (The HopsAuger motors auxiliary contact state - True/False)
    HopsAuger.PV (The HopsAuger motors actual state - Started/Stopped)
    WortPV (Inflow from MashTun Wort Process Variable Actual)
    HopsPV (Hops Process Variable Actual)
    HopsSP (Hops Setpoint Desired)
    BrewedWortPV (Brewed Wort Process Variable Actual outflow to Fermenter)     

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
        self.ShipComplete = False
        self.AllowMashWort = False
        self.MashShipComplete = False
        self.FermenterReady = False     
        self.ReadyOS = False   
        self.BrewedWortPV = 0.0
        self.HopsPV = 0.0
        self.HopsSP = 0.0
        self.TemperatureSP = 0
        self.TemperaturePV = 0.0
        self.TemperatureSafe = 100.0
        self.WortPV = 0.0
        self.WortSP = 0.0
        self.WortLoss = 0.0
        self.ScanDelta = 0.0
        self.BrewTime = 300
        self.SteamCFM = 0.0
        self.LevelPV = 0.0
        self.Scrap = 0.0
        self.newScrap = 0.0
        self.TemperatureOut = 0.0
        self.TemperatureMassOffset = 0.0
        self.ScanTime = 100
        self.PerformanceTargetPercent = 98
        self.Cons_Wort_Item = ""
        self.Cons_Wort_FromLot = ""
        self.Prod_BrewedWort_ToLot = ""
        self.Prod_BrewedWort_Item = ""
        self.Cons_Hops_FromLot = ""
        self.Cons_Hops_Item = ""
        self.ProductionID = ""
        self.Next_ProductionID = ""
        self.DownStream_ProductionID = ""        
        self.MaterialID = ""
        self.Next_ItemID = ""
        self.DownStream_ItemID = ""
        self.NewState = NewStateEnum.Ready
        self.NewStatus = NewStatusEnum.Idle
        self.UtilizationState = "Runtime"
        self.Utilization = "Running (Normal)"
        self.HopsNames = ['Admiral','Brewers Gold','Calypso','Orion', 'Southern Brewer', 'Viking']

        # Create contained assets
        self.HoldTime = Timer("HoldTime")        
        self.HopsAuger = Motor("HopsAuger")
        self.InletValve = Valve("InletValve") 
        self.OutletPump = Motor("OutletPump")
        self.OutletValve = Valve("OutletValve")
        self.SteamValve = Valve("SteamValve")
        self.CheckDownTime = Timer("CheckDownTime")
        self.SettleTime = Timer("SettleTime")
        self.DownTime = Timer("DownTime")
        self.TemperatureControl = pidLoop("TemperatureControl", 0.1, 0.25, 1.0, 5.0, 1.0)

        self.SettleTime.PT = randint(10,25)

        # Set timer for 1 minute to check for random downtime event
        self.CheckDownTime.PT = 60

    # Run method to simulate equipment data 
    def Run(self):                   

        if self.StartCmd:
            self.StartCmd = False
            if self.NewState == NewStateEnum.Ready:
                # Measures passed from upstream Mash Asset
                self.MaterialID = "{0}{1}".format("Brewed Wort ", self.Next_ItemID)
                self.Prod_BrewedWort_Item = self.MaterialID
                self.ProductionID = self.Next_ProductionID

                self.DownStream_ItemID = self.Next_ItemID
                self.DownStream_ProductionID = self.ProductionID

                uniquePre = choice(self.HopsNames)

                now = datetime.datetime.now()
                self.Prod_BrewedWort_ToLot = "{0}{1}{2}".format("BW-", self.EquipmentName[-3], now.strftime("%m%d%S%M")) 
                self.Cons_Hops_Item = "{0}{1}".format(uniquePre," Hops")                   
                self.Cons_Hops_FromLot = "{0}{1}{2}".format("HL-A", self.EquipmentName[-3], now.strftime("%d%M%S%m"))

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
                self.BrewedWortPV = 0.0
                self.HoldTime.Enabled = False
                self.HopsPV = 0.0
                self.HopsAuger.CmdStart = False
                self.InletValve.CmdOpen = False
                self.OutletPump.CmdStart = False
                self.OutletValve.CmdOpen = False
                self.ShipComplete = False
                self.AllowMashWort = False
                self.SteamValve.CmdOpen = False
                self.TemperaturePV = self.TemperatureSafe
                self.WortPV = 0.0
                self.WortSP = 5000.0

            case NewStateEnum.Done:                
                self.SteamValve.CmdOpen = False
                self.OutletPump.CmdStart = False
                self.OutletValve.CmdOpen = False
                self.HoldTime.Enabled = False
                self.ShipComplete = True
                self.HoldTime.RST = True
                self.ReadyOS = False

                self.SettleTime.Enabled = True
                if (self.SettleTime.DN):

                    self.SettleTime.Enabled = False
                    self.SettleTime.RST = True                                        

                    self.NewState = NewStateEnum.Ready
                    self.NewStatus = NewStatusEnum.Idle

            case NewStateEnum.Paused:                 
                self.HopsAuger.CmdStart = False
                self.InletValve.CmdOpen = False
                self.OutletPump.CmdStart = False
                self.OutletValve.CmdOpen = False
                self.SteamValve.CmdOpen = False
                self.HoldTime.Enabled = False
                self.CheckDownTime.Enabled = False

                if (self.WortPV > 100) and (self.Scrap < self.WortPV):
                    self.newScrap = self.WortPV * 0.00001
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
                    self.TemperatureSP = 100
                    self.TemperaturePV = self.TemperatureSafe
                    self.ScanDelta = 0.81
                    self.HoldTime.RST = True                    
                    self.BrewedWortPV = 0.0
                    self.HopsSP = 75.0
                    self.HopsPV = 0.0
                    self.LevelPV = 0.0
                    self.Scrap = 0.0
                    self.newScrap = 0.0
                    self.Cons_Wort_Item = ""
                    self.Cons_Wort_FromLot = ""
                    self.Prod_BrewedWort_ToLot = ""
                    self.Prod_BrewedWort_Item = ""
                    self.Cons_Hops_FromLot = ""
                    self.Cons_Hops_Item = ""
                    self.ProductionID = ""
                    self.MaterialID = ""
                    self.HopsAuger.CmdStart = False
                    self.InletValve.CmdOpen = False
                    self.OutletPump.CmdStart = False
                    self.OutletValve.CmdOpen = False
                    self.ShipComplete = False
                    self.AllowMashWort = True
                    self.SteamValve.CmdOpen = False                    
                    self.WortPV = 0.0
                    self.WortSP = 5000.0

                    self.HoldTime.PT = randint(6,11) * 60                                       

            case NewStateEnum.Running:

                match self.NewStatus:

                    case NewStatusEnum.Idle:
                        self.ReadyOS = False
                        self.NewStatus = NewStatusEnum.Filling

                    case NewStatusEnum.Filling:
                        # Ramp up the Wort
                        if (self.MashShipComplete):
                            self.WortSP = self.WortPV
                            self.InletValve.CmdOpen = False
                            self.WortLoss = (self.HopsPV * 0.833) / self.WortPV
                            self.AllowMashWort = False
                        else:
                            self.InletValve.CmdOpen = True
                            self.TemperaturePV = 150.0

                        # Setup Hops levels to dynamically fill based on amount of wort in tank 
                        self.HopsSP = round(self.WortPV * 0.02, 2)
                        if (self.MashShipComplete):
                            if (self.HopsPV <= self.HopsSP):
                                self.HopsAuger.CmdStart = True
                                self.HopsPV = round(self.HopsPV + ((self.ScanTime/100) * 0.57), 2)
                                if (self.TemperaturePV > self.TemperatureSafe):
                                    self.TemperaturePV = round(self.TemperaturePV - ((self.ScanTime/100) * 1.7139), 2)

                        if (self.MashShipComplete) and (self.HopsPV >= self.HopsSP):
                            self.HopsAuger.CmdStart = False

                            if (self.HoldTime.PT <= 0):
                                self.HoldTime.PT = self.BrewTime

                            # Initiate next phase
                            self.TemperatureSP = 212
                            self.NewStatus = NewStatusEnum.RampingUp

                    case NewStatusEnum.RampingUp:
                        # Ramp up the Temperature
                        self.SteamValve.CmdOpen = True

                        if (self.TemperaturePV >= self.TemperatureSP):
                            self.SteamValve.CmdOpen = False
                            self.NewStatus = NewStatusEnum.Holding
                            self.HoldTime.RST = False

                    case NewStatusEnum.Holding:
                        self.HoldTime.Enabled = True

                        if (self.TemperaturePV < (self.TemperatureSP - 2.1)):
                            self.SteamValve.CmdOpen = True

                        if (self.TemperaturePV >= self.TemperatureSP):
                            self.SteamValve.CmdOpen = False                        

                        if (self.HoldTime.DN and self.FermenterReady):
                            self.HoldTime.Enabled = False
                            self.NewStatus = NewStatusEnum.Draining 

                    case NewStatusEnum.Draining:
                        # Drain the Wort
                        self.SteamValve.CmdOpen = False

                        if (self.WortPV >= 0.0):
                            self.WortPV = round(self.WortPV - ((self.ScanTime/100) * 2.0), 2)

                            # Show a little loss on transfer
                            self.BrewedWortPV = round(self.BrewedWortPV + ((self.ScanTime/100) * 2.0) - self.WortLoss * 2.0, 2)
                            self.OutletValve.CmdOpen = True
                            self.OutletPump.CmdStart = True
                        else:
                            self.OutletValve.CmdOpen = False
                            self.OutletPump.CmdStart = False
                            self.ShipComplete = True
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

        # Emulate a PI Loop
        if (self.NewState != NewStateEnum.Paused):
            if (self.SteamValve.OLS):
                self.TemperatureControl.Enabled = True
                self.SteamCFM = 500.0 * self.TemperatureOut
            else:
                self.TemperatureControl.Enabled = False
                self.SteamCFM = 0.0

            if (self.SteamValve.CLS) and (self.TemperaturePV >= 90.0):
                self.TemperaturePV = round(self.TemperaturePV - self.ScanDelta * 0.001, 2)

        if (self.TemperatureControl.Enabled):
            self.TemperaturePV = round(self.TemperatureControl.Run(self.TemperatureSP, self.TemperaturePV), 2)

        # Create level from volume - the Brew Kettle is assumed to be 12' in diameter and 7' tall. 
        # This is a 5,900 GAL tank. Level will be normalized 0-100% 
        self.LevelPV = round(self.WortPV / 5900.0 * 100.0, 2)

        self.TemperatureMassOffset = 1.0 - (self.WortPV / 5900.0)

        # Run contained objects
        self.HoldTime.Run()
        self.CheckDownTime.Run()
        self.SettleTime.Run()
        self.DownTime.Run()
        self.HopsAuger.Run()         
        self.InletValve.Run()
        self.OutletValve.Run()  
        self.SteamValve.Run()  
        self.OutletPump.Run()