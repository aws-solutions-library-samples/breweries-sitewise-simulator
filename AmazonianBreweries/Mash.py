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
from random import randint, choice
from Motor import Motor
from Timer import Timer
from pidLoop import pidLoop
from Valve import Valve
from GlobalVariables import NewStateEnum, NewStatusEnum, UtilizationList, UtilizationStateList

class Mash:

    """
    The Mash Tun is a brewhouse vessel used for mixing the ground malt (grist) with temperature-controlled water. 
    This is called “mashing” and the porridge-like result is called the “mash.” The mash is held at a predetermined 
    temperature and time (e.g., at 65°C for 1 h) until the malt starches convert to sugars, and the dissolved malt 
    sugars (wort) are rinsed into the kettle where hops are added. The mash tun is a single vessel where the mashing 
    and wort runoff take place in the same vessel.

    Operational sequence steps: 
    
    1) The MashTun begins in the Ready/Idle state 
    2) Automatically transitions to Running(from MaltMill Asset going to Running)/Filling where water is added to the MashTun vessel
    3) Once the Water fill setpoint is reached it moves to Running/RampingUp where steam is used to heat up the temperature
    4) Once the Temperature PV (actual temperature) reaches Temperature Setpoint it moves to Running/Holding1 to soak and agitate
    5) Once the HoldTime Setpoint is reached it moves to Running/RampUp2 where steam is used to heat up the temperature further 
    6) Once the Temperature PV (actual temperature) reaches Temperature Setpoint it moves to Running/Holding2 to soak and agitate
    7) Once the HoldTime Setpoint is reached it moves to Running/Draining if the BoilKettle is in Ready/Idle, else stays in Holding2 
    8) After Draining is completed, it moves to Done/Draining, then back to Ready/Idle (Step 1) for next production run   

    Equipment Utilization (Availability component of OEE):

    Is dependent on the MalMill asset, please see MaltMill.py for more details. 

    Dependencies (Asset material transfers & data handshaking)
    ----------

    Upstream - Soft dependency on the Roaster (100/200), if no production(s) from the Roaster exists, it will randomly generate a consumption 
               item and from lot, otherwise it will randomly pull from an existing list of consumption items from the Roaster (100/200)
    Downstream - The BoilKettle must be in Ready/Idle for the MashTun to be able to Drain, else it will Hold.    

    Attributes (exposed to OPC UA Client)
    ----------    

    MaltPV (Malt Process Variable Actual)
    MaltSP (Malt Setpoint Desired)        
    NewState (Machine State - "Done", "Ready", "Running", "Paused" (Downtime), "Aborted")
    Agitator.AuxContact (The Agitator motors auxiliary contact state - True/False)
    Agitator.PV (The Agitator motors actual state - Started/Stopped)
    Cons_Malt_FromLot (Consumed Roasted Barley/Malt inventory lot/location attained from Roaster)
    Cons_Malt_Item (Consumed Roasted Barley/Malt Item/Material from Roaster)
    HoldTime.PT (Holdtime Timer Preset Time)
    HoldTime.ET (Holdtime Timer Elapsed Time)
    LevelPV (Level Process Variable in %)
    MaterialID (Current item being produced - if the Roaster asset has supplied Produced items then the MashTun will consume from it,
                otherwise it randomly selects 'Red','Pale','Dark','Green' Malt per production cycle)
    NewState (MaltMill asset provides new state)
    NewStatus (Machine Status - "Idle", "Filling", "Ramping Up1", "Holding1", "Ramping Up2", "Holding2", "Draining")
    OutletPump.AuxContact (The OutletPump motors auxiliary contact state - True/False)
    OutletPump.PV (The OutletPump motors actual state - Started/Stopped)
    OutletValve.CLS (The OutletValve is Closed Limit Switch)
    OutletValve.OLS (The OutletValve is Open Limit Switch)
    OutletValve.PV (The OutletValve actual state - Opened/InTransition/Closed)
    Prod_Wort_Item (Produced Wort Item/Material)
    Prod_Wort_ToLot (Produced Wort To inventory Lot/Location)
    ProductionID (Current Production/Work Order to make Beer, from wort to bottled beer - randomly created per production cycle)
    Scrap (How much material loss due to an equipment downtime condition)
    Scrap_ToLot (Scrapped Roasted Barley/Malt inventory lot/location)
    ShipComplete (Boolean flag to indicate when the Wort has been fully drained from the MashTun vessel)
    SoakTempSP1 (Temperature_SP setpoint for the RampUp1 Operation)
    SoakTempSP2 (Temperature_SP setpoint for the RampUp2 Operation)
    SoakTimeSP1 (HoldTime.PT setpoint for the Holding1 Operation)
    SoakTimeSP2 (HoldTime.PT setpoint for the Holding2 Operation)
    SteamValve.CLS (The SteamValve is Closed Limit Switch)
    SteamValve.OLS (The SteamValve is Open Limit Switch)
    SteamValve.PV (The SteamValve actual state - Opened/InTransition/Closed)
    TemperaturePV (Temperature Process Variable Actual)
    TemperatureSP (Temperature Setpoint Desired)
    UtilizationState ('Demand','Downtime','Maintenance')
    Utilization ('No Orders','Starved Supply','Running (Slow)','Unknown','EStop','Sticking Valve','Pump Overload',
                 'Faulty Wiring','Tripped Breaker','Planned Maintenance','Unplanned Maintenance')
    WaterPV (Water Process Variable Actual)
    WaterSP (Water Setpoint Desired)
    WaterValve.CLS (The WaterValve is Closed Limit Switch)
    WaterValve.OLS (The WaterValve is Open Limit Switch)
    WaterValve.PV (The WaterValve actual state - Opened/InTransition/Closed)
    Wort_Item (Wort Item/Material cureently being Produced)
    WortPV (Wort Process Variable Actual outflow to Boil Kettle)

    Methods
    -------
    
    __init__(self, EquipmentName) - Class Constructor
    Run(self) - method to simulate equipment data

    """

    # Class Constructor
    def __init__(self, EquipmentName):
        self.EquipmentName = EquipmentName 
        self.NewState = NewStateEnum.Done
        self.NewStatus = NewStatusEnum.Idle
        self.UtilizationState = "Runtime"
        self.Utilization = "Running (Normal)"        
        self.ShipComplete = False
        self.MaltMillComplete = False        
        self.BrewKettleReady = False
        self.ReadyOS = False        
        self.MashComplete = False
        self.ScanTime = 100
        self.WaterSP = 0
        self.WaterPV = 0.0
        self.WortPV = 0.0
        self.SoakTempSP1 = 0
        self.SoakTempSP2 = 0
        self.SoakTimeSP1 = 0
        self.SoakTimeSP2 = 0
        self.TemperatureSP = 0
        self.TemperaturePV = 0.0
        self.LevelPV = 0.0
        self.Scrap = 0.0        
        self.newScrap = 0.0
        self.ProductionID = ""
        self.MaterialID = ""
        self.Wort_Item = ""
        self.Cons_Malt_Item = ""
        self.Cons_Malt_FromLot = ""
        self.Prod_Wort_ToLot = ""
        self.Prod_Wort_Item = ""
        self.Scrap_ToLot = ""
        self.ConsList = []
        self.ProductNames = ['Red','Pale','Dark','Green']

        # Create contained assets
        self.HoldTime = Timer("HoldTime")        
        self.TemperatureControl = pidLoop("TemperatureControl", 0.1, 0.25, 1.0, 5.0, 1.0)
        self.WaterValve = Valve("WaterValve")
        self.SteamValve = Valve("SteamValve")
        self.OutletValve = Valve("OutletValve")
        self.Agitator = Motor("Agitator")
        self.OutletPump = Motor("OutletPump")        

    # Run method to simulate equipment data 
    def Run(self):        

        match self.NewState:

            case NewStateEnum.Aborted:
                self.Agitator.CmdStart = False
                self.SteamValve.CmdOpen = False
                self.OutletPump.CmdStart = False
                self.OutletValve.CmdOpen = False
                self.ShipComplete = True
                self.WaterPV = 0.0
                self.TemperatureSP = 120
                self.WortPV = 0.0
                self.HoldTime.Enabled = False

            case NewStateEnum.Done:
                self.Agitator.CmdStart = False
                self.SteamValve.CmdOpen = False
                self.OutletPump.CmdStart = False
                self.OutletValve.CmdOpen = False
                self.HoldTime.Enabled = False                

            case NewStateEnum.Paused:
                self.Agitator.CmdStart = False
                self.OutletPump.CmdStart = False
                self.OutletValve.CmdOpen = False
                self.SteamValve.CmdOpen = False
                self.WaterValve.CmdOpen = False
                self.HoldTime.Enabled = False                

                if (self.WaterPV > 100) and (self.Scrap < self.WaterPV):
                    self.newScrap = self.WaterPV * 0.00001
                    self.Scrap = round(self.Scrap + self.newScrap, 2)                 

            case NewStateEnum.Ready:
                self.NewStatus = NewStatusEnum.Idle

                if (not self.ReadyOS):
                    # Reset inital values for next production run
                    self.ReadyOS = True
                    self.WaterSP = 0
                    self.Scrap = 0.0
                    self.newScrap = 0.0
                    self.SoakTempSP1 = 0
                    self.SoakTempSP2 = 0
                    self.SoakTimeSP1 = 0
                    self.SoakTimeSP2 = 0
                    self.TemperatureSP = 90
                    self.TemperaturePV = 90.0
                    self.WortPV = 0.0
                    self.LevelPV = 0.0
                    self.ProductionID = ""
                    self.MaterialID = ""
                    self.Wort_Item = ""
                    self.Cons_Malt_Item = ""
                    self.Cons_Malt_FromLot = ""
                    self.Prod_Wort_ToLot = ""
                    self.Prod_Wort_Item = ""
                    self.Scrap_ToLot = ""                    
                    self.HoldTime.RST = True
                    self.MaltMillComplete = False
                    self.MashComplete = False
                    self.ShipComplete = False                    
                    
                    # Randomize measurements for next Production Run
                    self.WaterSP = randint(2500,3500)  
                    self.SoakTempSP1 = randint(120,141)
                    self.SoakTempSP2 = randint(150,201) 
                    self.SoakTimeSP1 = randint(5,12) * 60    
                    self.SoakTimeSP2 = randint(7,14) * 60 

                    self.HoldTime.PT = self.SoakTimeSP1  

                    if (len(self.ConsList) > 0):
                        roasterProdDict = choice(self.ConsList)
                        uniquePre = roasterProdDict["SelectedProduct"]
                        self.Cons_Malt_Item = "{0}".format(roasterProdDict["RoastedBarley_Item"])
                        self.Cons_Malt_FromLot = "{0}".format(roasterProdDict["RoastedBarley_ToLot"])
                        self.ConsList.remove(roasterProdDict)
                    else:
                        uniquePre = choice(self.ProductNames)
                        self.Cons_Malt_Item = "{0}{1}".format(uniquePre," Malt")
                        self.Cons_Malt_FromLot = "{0}{1}".format("RBB-", str(randint(1,10000)).zfill(5))                               

                    #uniquePre = choice(self.ProductNames)                  
                    fullMatID = "{0}{1}".format(uniquePre," Ale")
                    self.Wort_Item = fullMatID
                    self.MaterialID = "{0}{1}".format("Wort ", fullMatID)
                    self.Prod_Wort_Item = self.MaterialID                                                            

                    now = datetime.datetime.now()
                    self.ProductionID = "{0}{1}{2}".format("PR-A", self.EquipmentName[-3], now.strftime("%m%d%S%M"))

                    lotNo = "{0}{1}{2}".format("GW-", self.EquipmentName[-3], now.strftime("%d%M%S%m"))
                    self.Prod_Wort_ToLot = lotNo
                    self.Scrap_ToLot = lotNo
                        
            case NewStateEnum.Running:

                match self.NewStatus:

                    case NewStatusEnum.Idle:
                        # Automatically set it to the first phase, Filling
                        self.ReadyOS = False
                        self.NewStatus = NewStatusEnum.Filling

                    case NewStatusEnum.Filling:
                        # Ramp up the Water
                        if (self.WaterPV <= self.WaterSP):
                            self.WaterValve.CmdOpen = True

                            if self.WaterValve.OLS:
                                self.WaterPV = round(self.WaterPV + ((self.ScanTime/100) * 3.367), 2)
                                self.TemperaturePV = 90.0
                        else:
                            self.WaterValve.CmdOpen = False

                            # Complete the phase
                            if (self.WaterValve.CLS and self.MaltMillComplete):
                                # Configure Setpoint for next phase
                                self.TemperatureSP = self.SoakTempSP1

                                # Initiate next phase
                                self.NewStatus = NewStatusEnum.RampingUp1

                    case NewStatusEnum.RampingUp1:
                        # Ramp up the temperature
                        self.Agitator.CmdStart = True 
                        self.SteamValve.CmdOpen = True

                        if (self.TemperaturePV >= self.TemperatureSP):
                            self.Agitator.CmdStart = False
                            self.SteamValve.CmdOpen = False

                            # Initiate next phase
                            self.NewStatus = NewStatusEnum.Holding1
                            self.HoldTime.RST = False

                    case NewStatusEnum.Holding1:
                         self.HoldTime.Enabled = True

                         if(self.HoldTime.DN):
                             self.HoldTime.Enabled = False
                             self.HoldTime.RST = True
                             self.HoldTime.PT = self.SoakTimeSP2

                             # Initiate next phase
                             self.NewStatus = NewStatusEnum.RampingUp2
                             self.TemperatureSP = self.SoakTempSP2

                    case NewStatusEnum.RampingUp2:
                        # Ramp up the temperature
                        self.Agitator.CmdStart = True
                        self.SteamValve.CmdOpen = True

                        if (self.TemperaturePV >= self.TemperatureSP):
                            self.Agitator.CmdStart = False
                            self.SteamValve.CmdOpen = False

                            # Initiate next phase
                            self.NewStatus = NewStatusEnum.Holding2
                            self.HoldTime.RST = False

                    case NewStatusEnum.Holding2:
                        self.HoldTime.Enabled = True                        

                        if (self.HoldTime.DN and self.BrewKettleReady):
                            self.HoldTime.Enabled = False
                            self.NewStatus = NewStatusEnum.Draining

                    case NewStatusEnum.Draining:
                        self.OutletValve.CmdOpen = True
                        self.OutletPump.CmdStart = True

                        if (self.WaterPV >= 0.0):
                            if (self.WaterPV >= 1000.0):
                                self.WaterPV = round(self.WaterPV - ((self.ScanTime/100) * 1.91), 2)
                                # Going to lose some moisture to the Mash
                                self.WortPV = round(self.WortPV + ((self.ScanTime/100) * 1.90), 2)

                            if(self.WaterPV <= 1000.0):
                                self.WaterValve.CmdOpen = True
                                self.WaterPV = round(self.WaterPV - ((self.ScanTime/100) * 1.31), 2)
                                # Going to lose some moisture to the Mash
                                self.WortPV = round(self.WortPV + ((self.ScanTime/100) * 1.30), 2)
                            if ((self.WaterValve.CmdOpen) and (self.TemperaturePV > 120.0)):
                                self.TemperaturePV = round(self.TemperaturePV - (0.93 * 0.9), 2)
                        else:
                            self.OutletValve.CmdOpen = False
                            self.OutletPump.CmdStart = False
                            self.ShipComplete = True 
                            self.WaterValve.CmdOpen = False

                            # Because of the interaction between Malt and Mash, this entity only sets a bit for completion
                            self.MashComplete = True                

        if (self.NewState != NewStateEnum.Paused) and (self.SteamValve.CmdOpen) and (self.WaterValve.CmdOpen == False) and (self.TemperaturePV >= 90.0):
            self.TemperaturePV = round(self.TemperaturePV - 0.93 * 0.001, 2)

        # Anytime the steam valve is open, increase heat accordingly and adjust Steam CFM
        if (self.SteamValve.OLS):
            self.TemperatureControl.Enabled = True
        else:
            self.TemperatureControl.Enabled = False

        if (self.TemperatureControl.Enabled):
            self.TemperaturePV = round(self.TemperatureControl.Run(self.TemperatureSP, self.TemperaturePV), 2)

        # Create level from volume - the Mash Tun is assumed to be 12' in diameter and 7' tall. 
        # This is a 5,900 GAL tank. Level will be normalized 0-100% as: Level = Water.PV / 5900 * 100 
        self.LevelPV = round(self.WaterPV / 5900 * 100.0, 2)

        self.TemperatureControl.MassOffset = 1.0 - (self.WaterPV / 5900.0)
        self.TemperatureControl.PVincreaseMultiplier = 0.25   

        # Run contained objects
        self.HoldTime.Run()        
        self.WaterValve.Run()
        self.SteamValve.Run()
        self.OutletValve.Run()
        self.Agitator.Run()
        self.OutletPump.Run()  