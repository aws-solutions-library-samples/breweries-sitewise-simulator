#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#----------------------------------------------------------------------------
# Created By  : Nick Santucci, Chris Azer, Tim Wilson
# Created Date: January 18 2023
# version ='1.1.0'
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# ACME Breweries is a program to exercise the capabilities
# of IoT SiteWise (Monitor), IoT Greengrass, IoT TwinMaker, and other IoT 
# based AWS services that constantly runs and produces factory like data.
#
# This program serves as a data simulation and is not recommended for any production 
# environment. Data is exposed via an OPC UA Server for OPC UA Clients 
# (i.e. IoT SiteWise Connector on IoT Greengrass). In addition, values can be
# published directly to IoT SiteWise at a default interval of 5 seconds.
#
# This program serves as a data simulation and is not recommended for any production 
# environment.    
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import time
import datetime
from Timer import Timer
from Roaster import Roaster
from MaltMill import MaltMill
from Mash import Mash
from BoilKettle import BoilKettle 
from Fermenter import Fermenter
from BrightTank import BrightTank
from BottleLine import BottleLine
from GlobalVariables import NewStateEnum, NewStatusEnum
import boto3
import argparse
import threading

#########################################################################
# OPC UA Library provided by - https://github.com/FreeOpcUa/python-opcua
from opcua import Server, ua
#########################################################################



if __name__ == "__main__":     

    """

    Main Program Overview
    ----------

    This Main program file serves to bring the ACME Brewery simulation to life, to integrate everything
    together, to execute the control narrative.

    The major responsibilities include:

    1) Setting up and configuring the OPC UA Server which is a modern communications protocol for 
       industrial automation that is increasingly being adopted for data collection and control by 
       traditional on-premises applications and Industrial IoT and Industry 4.0 applications and platforms
    2) Initializing the virtual brewery assets (Roasters, MaltMill/MashTuns, BoilKettles, Fermenters, BrightTanks, and Bottle Lines) 
       that serve as digital twins to AWS services such as IoT SiteWise and IoT TwinMaker
    3) Executing the logic to simulate asset behavior and controlling material transfer between assets
    4) Sending real time asset values to OPC UA Clients (IoT SiteWise OPC UA Collector running on IoT Greengrass)
    5) Running the program at 100 milliseconds scan rate to emulate PLC control 

    """   

    def publish_properties_to_sitewise(area_name, asset_name, timeInSeconds, properties):
        """
        publish_properties_to_sitewise - Publishes an array of property values from simulatior
                                         to IoT SiteWise. Parameter construct the property alias
                                         in IoT SiteWise

        :param area_name: In alias for property, the area name is required (i.e "Mashing", "Roasting", ...)
        :param asset_name: In alias for property, the asset name is required (i.e "Roaster100", "Roaster200", ...)
        :param timeInSeconds: epoch time in seconds. This is required for the IoT SiteWise TVQ
        :param properties: A nested array of property values. Each record contains an array of parameters needed
                           for the batch_put_asset_property_value API call.
                           - string reference to local variable containing current value
                           - datatype
                           - property name
        """
        # properties == [ [".MaltPV","double","Malt_PV"],...]
        for prop in properties:
            try:
                entries = []
                entries=[
                        {
                            'entryId': '{}{}'.format(prop[2],int(time.time())),
                            'propertyAlias': "/{}/{}/{}/{}/{}".format(enterprise_name,plant_name,area_name,asset_name,prop[2]),
                            'propertyValues': [
                                {
                                    'value': {
                                        prop[1]+'Value': eval(asset_name+prop[0])
                                    },
                                    'timestamp': {
                                        'timeInSeconds': timeInSeconds,
                                        'offsetInNanos': 0
                                    },
                                    'quality': 'GOOD'
                                },
                            ]
                        },
                    ]
                response = client.batch_put_asset_property_value(
                    entries=entries
                )
            except Exception as e:
                print(str(e))
                time.sleep(5)

    def publish_to_sitewise_thread():
        """
        publish_to_sitewise_thread - Thread function to publish values to IoT SiteWise on a continuous loop.

        """
        # IoT SiteWise Publish event tracking
        lastpublishtime = datetime.datetime.now()
        print("Publishing values to SiteWise")
        while True:
            #######################################################################
            # Publish values to IoT SiteWise if enabled and after interval time has elapsed
            #######################################################################
            if((datetime.datetime.now()-lastpublishtime).total_seconds()  >= interval):
                timeInSeconds = int(datetime.datetime.now().timestamp())
                # Roasters
                roaster_properties = [
                    [".MaltPV","double", "Malt_PV"],
                    [".MaltPV", "double", "Malt_PV"],
                    [".MaltSP", "integer", "Malt_SP"],
                    [".TemperaturePV", "double", "Temperature_PV"],
                    [".TemperatureSP", "integer", "Temperature_SP"],
                    [".HoldTime.PT", "integer", "HoldTime_PT"],
                    [".HoldTime.ET", "integer", "HoldTime_ET"],
                    [".NewState", "string", "State"],
                    [".NewStatus", "string", "Status"],
                    [".MaterialID", "string", "MaterialID"],
                    [".ProductionID", "string", "ProductionID"],
                    [".Cons_RawBarley_Item", "string", "Cons_RawBarley_Item"],
                    [".Cons_RawBarley_FromLot", "string", "Cons_RawBarley_FromLot"],
                    [".Prod_RoastedBarley_ToLot", "string", "Prod_RoastedBarley_ToLot"],
                    [".Prod_RoastedBarley_Item", "string", "Prod_RoastedBarley_Item"],
                    [".UtilizationState", "string", "UtilizationState"],
                    [".Utilization", "string", "Utilization"],
                    [".MaltAuger.PV", "string", "MaltAuger_PV"],
                    [".MaltAuger.AuxContact", "boolean", "MaltAuger_AuxContact"],
                    [".Scrap", "double", "Scrap"]
                ]
                publish_properties_to_sitewise("Roasting", "Roaster100", timeInSeconds, roaster_properties)
                publish_properties_to_sitewise("Roasting", "Roaster200", timeInSeconds, roaster_properties)  

                # MaltMills
                maltmill_properties = [
                    [".MaltPV", "double", "Malt_PV"],
                    [".MaltSP", "double", "Malt_SP"],
                    [".MaltAuger.AuxContact", "boolean", "MaltAuger_AuxContact"],
                    [".MaltAuger.PV", "string", "MaltAuger_PV"],
                    [".MaltMill.AuxContact", "boolean", "MaltMill_AuxContact"],
                    [".MaltMill.PV", "string", "MaltMill_PV"],
                    [".NewState", "string", "State"]
                ]
                publish_properties_to_sitewise("Mashing", "MaltMill100", timeInSeconds, maltmill_properties)
                publish_properties_to_sitewise("Mashing", "MaltMill200", timeInSeconds, maltmill_properties)

                # MashTuns
                mashtun_properties = [
                    [".Agitator.AuxContact", "boolean", "Agitator_AuxContact"],
                    [".Agitator.PV", "string", "Agitator_PV"],
                    [".Cons_Malt_FromLot", "string", "Cons_Malt_FromLot"],
                    [".Cons_Malt_Item", "string", "Cons_Malt_Item"],
                    [".HoldTime.PT", "integer", "HoldTime_PT"],
                    [".HoldTime.ET", "integer", "HoldTime_ET"],
                    [".LevelPV", "double", "Level_PV"],
                    [".MaterialID", "string", "MaterialID"],
                    [".NewState", "string", "State"],
                    [".NewStatus", "string", "Status"],
                    [".OutletPump.AuxContact", "boolean", "OutletPump_AuxContact"],
                    [".OutletPump.PV", "string", "OutletPump_PV"],
                    [".OutletValve.CLS", "boolean", "OutletValve_CLS"],
                    [".OutletValve.OLS", "boolean", "OutletValve_OLS"],
                    [".OutletValve.PV", "string", "OutletValve_PV"],
                    [".Prod_Wort_Item", "string", "Prod_Wort_Item"],
                    [".Prod_Wort_ToLot", "string", "Prod_Wort_ToLot"],
                    [".ProductionID", "string", "ProductionID"],
                    [".Scrap", "double", "Scrap"],
                    [".Scrap_ToLot", "string", "Scrap_ToLot"],
                    [".ShipComplete", "boolean", "ShipComplete"],
                    [".SoakTempSP1", "integer", "SoakTempSP1"],
                    [".SoakTempSP2", "integer", "SoakTempSP2"],
                    [".SoakTimeSP1", "integer", "SoakTimeSP1"],
                    [".SoakTimeSP2", "integer", "SoakTimeSP2"],
                    [".SteamValve.CLS", "boolean", "SteamValve_CLS"],
                    [".SteamValve.OLS", "boolean", "SteamValve_OLS"],
                    [".SteamValve.PV", "string", "SteamValve_PV"],
                    [".TemperaturePV", "double", "Temperature_PV"],
                    [".TemperatureSP", "integer", "Temperature_SP"],
                    [".UtilizationState", "string", "UtilizationState"],
                    [".Utilization", "string", "Utilization"],
                    [".WaterPV", "double", "Water_PV"],
                    [".WaterSP", "integer", "Water_SP"],
                    [".WaterValve.CLS", "boolean", "WaterValve_CLS"],
                    [".WaterValve.OLS", "boolean", "WaterValve_OLS"],
                    [".WaterValve.PV", "string", "WaterValve_PV"],
                    [".Wort_Item", "string", "Wort_Item"],
                    [".WortPV", "double", "Wort_PV"]
                ]
                publish_properties_to_sitewise("Mashing", "MashTun100", timeInSeconds, mashtun_properties)
                publish_properties_to_sitewise("Mashing", "MashTun200", timeInSeconds, mashtun_properties)
                
                # BoilKettles
                boilkettle_properties = [
                    [".Cons_Hops_FromLot", "string", "Cons_Hops_FromLot"],                  
                    [".Cons_Hops_Item", "string", "Cons_Hops_Item"],  
                    [".Cons_Wort_FromLot", "string", "Cons_Wort_FromLot"],  
                    [".Cons_Wort_Item", "string", "Cons_Wort_Item"],  
                    [".HoldTime.PT", "integer", "HoldTime_PT"],  
                    [".HoldTime.ET", "integer", "HoldTime_ET"],  
                    [".LevelPV", "double", "Level_PV"],  
                    [".MaterialID", "string", "MaterialID"],  
                    [".NewState", "string", "State"],  
                    [".NewStatus", "string", "Status"],  
                    [".OutletPump.AuxContact", "boolean", "OutletPump_AuxContact"],  
                    [".OutletPump.PV", "string", "OutletPump_PV"],  
                    [".InletValve.CLS", "boolean", "InletValve_CLS"],  
                    [".InletValve.OLS", "boolean", "InletValve_OLS"],  
                    [".InletValve.PV", "string", "InletValve_PV"],  
                    [".OutletValve.CLS", "boolean", "OutletValve_CLS"],  
                    [".OutletValve.OLS", "boolean", "OutletValve_OLS"],  
                    [".OutletValve.PV", "string", "OutletValve_PV"],  
                    [".Prod_BrewedWort_Item", "string", "Prod_BrewedWort_Item"],  
                    [".Prod_BrewedWort_ToLot", "string", "Prod_BrewedWort_ToLot"],  
                    [".ProductionID", "string", "ProductionID"],  
                    [".Scrap", "double", "Scrap"],  
                    [".SteamValve.CLS", "boolean", "SteamValve_CLS"],  
                    [".SteamValve.OLS", "boolean", "SteamValve_OLS"],  
                    [".SteamValve.PV", "string", "SteamValve_PV"],  
                    [".TemperaturePV", "double", "Temperature_PV"],  
                    [".TemperatureSP", "integer", "Temperature_SP"],  
                    [".UtilizationState", "string", "UtilizationState"],  
                    [".Utilization", "string", "Utilization"],  
                    [".HopsAuger.AuxContact", "boolean", "HopsAuger_AuxContact"],  
                    [".HopsAuger.PV", "string", "HopsAuger_PV"],  
                    [".WortPV", "double", "Wort_PV"],  
                    [".HopsPV", "double", "Hops_PV"],  
                    [".HopsSP", "double", "Hops_SP"],  
                    [".BrewedWortPV", "double", "BrewedWort_PV"]
                ]
                publish_properties_to_sitewise("Brewing", "BoilKettle100", timeInSeconds, boilkettle_properties)
                publish_properties_to_sitewise("Brewing", "BoilKettle200", timeInSeconds, boilkettle_properties)      

                    
                # Fermenters
                fermenter_properties = [
                    [".ChillWaterValve.CLS", "boolean", "ChillWaterValve_CLS"],                
                    [".ChillWaterValve.OLS", "boolean", "ChillWaterValve_OLS"],
                    [".ChillWaterValve.PV", "string", "ChillWaterValve_CLS"],
                    [".Cons_BrewedWort_FromLot", "string", "Cons_BrewedWort_FromLot"],
                    [".Cons_BrewedWort_Item", "string", "Cons_BrewedWort_Item"],
                    [".Cons_Yeast_FromLot", "string", "Cons_Yeast_FromLot"],
                    [".Cons_Yeast_Item", "string", "Cons_Yeast_Item"],
                    [".HoldTime.PT", "integer", "HoldTime_PT"],
                    [".HoldTime.ET", "integer", "HoldTime_ET"],
                    [".LevelPV", "double", "Level_PV"],
                    [".MaterialID", "string", "MaterialID"],
                    [".NewState", "string", "State"],
                    [".NewStatus", "string", "Status"],
                    [".InletValve.CLS", "boolean", "InletValve_CLS"],
                    [".InletValve.OLS", "boolean", "InletValve_OLS"],
                    [".InletValve.PV", "string", "InletValve_PV"],
                    [".OutletPump.AuxContact", "boolean", "OutletPump_AuxContact"],
                    [".OutletPump.PV", "string", "OutletPump_PV"],
                    [".OutletValve.CLS", "boolean", "OutletValve_CLS"],
                    [".OutletValve.OLS", "boolean", "OutletValve_OLS"],
                    [".Prod_GreenBeer_Item", "string", "Prod_GreenBeer_Item"],
                    [".Prod_GreenBeer_ToLot", "string", "Prod_GreenBeer_ToLot"],
                    [".ProductionID", "string", "ProductionID"],
                    [".Scrap", "double", "Scrap"],
                    [".ShipTo_Tank", "integer", "ShipTo_Tank"],
                    [".TemperaturePV", "double", "Temperature_PV"],
                    [".TemperatureSP", "integer", "Temperature_SP"],
                    [".UtilizationState", "string", "UtilizationState"],
                    [".Utilization", "string", "Utilization"],
                    [".YeastPV", "double", "Yeast_PV"],
                    [".YeastSP", "double", "Yeast_SP"],
                    [".YeastPump.AuxContact", "boolean", "YeastPump_AuxContact"],
                    [".YeastPump.PV", "string", "YeastPump_PV"],
                    [".GreenBeerPV", "double", "GreenBeer_PV"]
                ]
                publish_properties_to_sitewise("Fermentation", "Fermenter100", timeInSeconds, fermenter_properties)
                publish_properties_to_sitewise("Fermentation", "Fermenter200", timeInSeconds, fermenter_properties)
                

                # Bright Tank 301
                tanks_properties = [
                    [".AllocatedFrom", "integer", "AllocatedFrom"],                
                    [".ChillWaterValve.CLS", "boolean", "ChillWaterValve_CLS"],
                    [".ChillWaterValve.OLS", "boolean", "ChillWaterValve_OLS"],
                    [".ChillWaterValve.PV", "string", "ChillWaterValve_PV"],
                    [".Cons_GreenBeer_FromLot", "string", "Cons_GreenBeer_FromLot"],
                    [".Cons_GreenBeer_Item", "string", "Cons_GreenBeer_Item"],
                    [".HoldTime.PT", "integer", "HoldTime_PT"],
                    [".HoldTime.ET", "integer", "HoldTime_ET"],
                    [".LevelPV", "double", "Level_PV"],
                    [".MaterialID", "string", "MaterialID"],
                    [".NewState", "string", "State"],
                    [".NewStatus", "string", "Status"],
                    [".BeerPV", "double", "Beer_PV"],
                    [".BeerSP", "double", "Beer_SP"],
                    [".InletValve.CLS", "boolean", "InletValve_CLS"],
                    [".InletValve.OLS", "boolean", "InletValve_OLS"],
                    [".InletValve.PV", "string", "InletValve_PV"],
                    [".OutletPump.AuxContact", "boolean", "OutletPump_AuxContact"],
                    [".OutletPump.PV", "string", "OutletPump_PV"],
                    [".OutletValve.CLS", "boolean", "OutletValve_CLS"],
                    [".OutletValve.OLS", "boolean", "OutletValve_OLS"],
                    [".OutletValve.PV", "string", "OutletValve_PV"],
                    [".Prod_Beer_Item", "string", "Prod_Beer_Item"],
                    [".Prod_Beer_ToLot", "string", "Prod_Beer_ToLot"],
                    [".ProductionID", "string", "ProductionID"],
                    [".TemperaturePV", "double", "Temperature_PV"],
                    [".TemperatureSP", "integer", "Temperature_SP"],
                    [".UtilizationState", "string", "UtilizationState"],
                    [".Utilization", "string", "Utilization"],
                    [".BeerShipped", "double", "BeerShipped"],
                    [".ShipToTank", "integer", "ShipTo_Tank"]
                ]
                publish_properties_to_sitewise("BeerStorage", "BrightTank301", timeInSeconds, tanks_properties)
                publish_properties_to_sitewise("BeerStorage", "BrightTank302", timeInSeconds, tanks_properties)
                publish_properties_to_sitewise("BeerStorage", "BrightTank303", timeInSeconds, tanks_properties)
                publish_properties_to_sitewise("BeerStorage", "BrightTank304", timeInSeconds, tanks_properties)
                publish_properties_to_sitewise("BeerStorage", "BrightTank305", timeInSeconds, tanks_properties)        
                

                # BottlingLines
                bottling_properties = [
                    [".AllocatedFrom", "integer", "AllocatedFrom"],
                    [".BeerPV", "double", "Beer_PV"],
                    [".BottlePV", "double", "Bottle_PV"],
                    [".BottleSP", "double", "Bottle_SP"],
                    [".Cons_Beer_FromLot", "string", "Cons_Beer_FromLot"],  
                    [".Cons_Beer_Item", "string", "Cons_Beer_Item"],
                    [".Cons_Bottle_FromLot", "string", "Cons_Bottle_FromLot"],
                    [".Cons_Bottle_Item", "string", "Cons_Bottle_Item"],
                    [".Cons_Cap_FromLot", "string", "Cons_Cap_FromLot"],
                    [".Cons_Cap_Item", "string", "Cons_Cap_Item"],
                    [".Cons_Label_FromLot", "string", "Cons_Label_FromLot"],
                    [".Cons_Label_Item", "string", "Cons_Label_Item"],
                    [".LevelPV", "double", "Level_PV"],
                    [".MaterialID", "string", "MaterialID"],
                    [".Prod_BottledBeer_Item", "string", "Prod_BottledBeer_Item"],
                    [".Prod_BottledBeer_ToLot", "string", "Prod_BottledBeer_ToLot"],
                    [".ProductionID", "string", "ProductionID"],
                    [".TemperaturePV", "double", "Temperature_PV"],
                    [".TemperatureSP", "integer", "Temperature_SP"],
                    [".HoldTime.PT", "integer", "HoldTime_PT"],
                    [".HoldTime.ET", "integer", "HoldTime_ET"],
                    [".NewState", "string", "State"],
                    [".NewStatus", "string", "Status"],
                    [".UtilizationState", "string", "UtilizationState"],
                    [".Utilization", "string", "Utilization"],
                    [".Scrap", "double", "Scrap"],
                    [".SpeedPV", "double", "Speed_PV"],
                    [".SpeedSP", "integer", "Speed_SP"]    
                ]
                publish_properties_to_sitewise("Bottling", "BottleLine401", timeInSeconds, bottling_properties)        
                publish_properties_to_sitewise("Bottling", "BottleLine402", timeInSeconds, bottling_properties)        
                publish_properties_to_sitewise("Bottling", "BottleLine403", timeInSeconds, bottling_properties)        

                # reset interval
                lastpublishtime = datetime.datetime.now()

    # Parse parameters to start the simulation
    parser = argparse.ArgumentParser(description='Simulation Parameters')
    parser.add_argument('--publishtositewise', dest='publishtositewise', default='False', choices=('True','False'), help='Publish to IoT SiteWise (default=False)')
    parser.add_argument('--interval', dest='interval', default=5, type=int, help='Interval in seconds to publish to IoT SiteWise (default=5)')
    parser.add_argument('--region', dest='region', default="us-west-2", type=str, help='AWS Region to publish to (default=us-west-2)')

    args = parser.parse_args()

    publishtositewise = args.publishtositewise == 'True'
    interval = int(args.interval)
    region = args.region
    
    # Initailize IoT SiteWise Client connection
    client = boto3.client('iotsitewise', region_name=region)
    
    # Initailize OPC UA Server
    server = Server()        
    print("Started OPC server")
    ##############################################################################
    ############################## ATTENTION #####################################
    ## This will bind to all IPs, but possible this may need to be specific for your client.
    server.set_endpoint("opc.tcp://0.0.0.0:4841/server/")
    #############################################################################
    #############################################################################
    
    enterprise_name = "AmazonBreweries"
    plant_name = "IrvinePlant"
    opc_server_name = "OPCUA_{}_Server".format(enterprise_name)
    server.set_server_name(opc_server_name)

    # set all possible endpoint policies for clients to connect through
    server.set_security_policy([
                ua.SecurityPolicyType.NoSecurity,
                ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt,
                ua.SecurityPolicyType.Basic256Sha256_Sign])

    addspace = server.register_namespace(opc_server_name)
    
    node = server.get_objects_node()

    # Build Enterprise->Site->Area->Asset Hierarchy
    Enterprise = node.add_object(addspace, enterprise_name)
    Site = Enterprise.add_object(addspace, plant_name)
    # Create Roasting area and add roasting assets
    RoastingArea = Site.add_object(addspace, "Roasting")
    AssetRoaster100 = RoastingArea.add_object(addspace, "Roaster100")
    AssetRoaster200 = RoastingArea.add_object(addspace, "Roaster200")
    # Create Mashing area and add maltmill and mashing assets
    MashingArea = Site.add_object(addspace, "Mashing")
    AssetMaltMill100 = MashingArea.add_object(addspace, "MaltMill100")    
    AssetMaltMill200 = MashingArea.add_object(addspace, "MaltMill200")
    AssetMashTun100 = MashingArea.add_object(addspace, "MashTun100")
    AssetMashTun200 = MashingArea.add_object(addspace, "MashTun200")  
    # Create Brewing area and add brewing assets    
    BrewingArea = Site.add_object(addspace, "Brewing")
    AssetBoilKettle100 = BrewingArea.add_object(addspace, "BoilKettle100")
    AssetBoilKettle200 = BrewingArea.add_object(addspace, "BoilKettle200")
    # Create Fermentation area and add fermenting assets
    FermentationArea = Site.add_object(addspace, "Fermentation")
    AssetFermenter100 = FermentationArea.add_object(addspace, "Fermenter100")
    AssetFermenter200 = FermentationArea.add_object(addspace, "Fermenter200")
    # Create BeerStorage area and add beer storage assets
    BeerStorageArea = Site.add_object(addspace, "BeerStorage")
    AssetBrightTank301 = BeerStorageArea.add_object(addspace, "BrightTank301")
    AssetBrightTank302 = BeerStorageArea.add_object(addspace, "BrightTank302")
    AssetBrightTank303 = BeerStorageArea.add_object(addspace, "BrightTank303")
    AssetBrightTank304 = BeerStorageArea.add_object(addspace, "BrightTank304")
    AssetBrightTank305 = BeerStorageArea.add_object(addspace, "BrightTank305")
    # Create Packaging area and add packaging assets
    BottlingArea = Site.add_object(addspace, "Bottling")
    AssetBottleLine401 = BottlingArea.add_object(addspace, "BottleLine401")
    AssetBottleLine402 = BottlingArea.add_object(addspace, "BottleLine402")
    AssetBottleLine403 = BottlingArea.add_object(addspace, "BottleLine403")    

    # Create OPC Nodes for assets

    # Create new OPC data items for Roaster 100 
    R100_Malt_PV = AssetRoaster100.add_variable(addspace, "Malt_PV", 0, ua.VariantType.Double)
    R100_Malt_SP = AssetRoaster100.add_variable(addspace, "Malt_SP", 0, ua.VariantType.Int64)
    R100_Temperature_PV = AssetRoaster100.add_variable(addspace, "Temperature_PV", 0, ua.VariantType.Double)
    R100_Temperature_SP = AssetRoaster100.add_variable(addspace, "Temperature_SP", 0, ua.VariantType.Int64)
    R100_HoldTime_PT = AssetRoaster100.add_variable(addspace, "HoldTime_PT", 0, ua.VariantType.Int64)
    R100_HoldTime_ET = AssetRoaster100.add_variable(addspace, "HoldTime_ET", 0, ua.VariantType.Int64)
    R100_State = AssetRoaster100.add_variable(addspace, "State", 0, ua.VariantType.String)
    R100_Status = AssetRoaster100.add_variable(addspace, "Status", 0, ua.VariantType.String) 
    R100_MaterialID = AssetRoaster100.add_variable(addspace, "MaterialID", 0, ua.VariantType.String)   
    R100_ProductionID = AssetRoaster100.add_variable(addspace, "ProductionID", 0, ua.VariantType.String) 
    R100_Cons_RawBarley_Item = AssetRoaster100.add_variable(addspace, "Cons_RawBarley_Item", 0, ua.VariantType.String)
    R100_Cons_RawBarley_FromLot = AssetRoaster100.add_variable(addspace, "Cons_RawBarley_FromLot", 0, ua.VariantType.String) 
    R100_Prod_RoastedBarley_ToLot = AssetRoaster100.add_variable(addspace, "Prod_RoastedBarley_ToLot", 0, ua.VariantType.String)
    R100_Prod_RoastedBarley_Item = AssetRoaster100.add_variable(addspace, "Prod_RoastedBarley_Item", 0, ua.VariantType.String) 
    R100_UtilizationState = AssetRoaster100.add_variable(addspace, "UtilizationState", 0, ua.VariantType.String) 
    R100_Utilization = AssetRoaster100.add_variable(addspace, "Utilization", 0, ua.VariantType.String)    
    R100_MaltAuger_PV = AssetRoaster100.add_variable(addspace, "MaltAuger_PV", 0, ua.VariantType.String)
    R100_MaltAuger_AuxContact = AssetRoaster100.add_variable(addspace, "MaltAuger_AuxContact", 0, ua.VariantType.Boolean)
    R100_Scrap = AssetRoaster100.add_variable(addspace, "Scrap", 0, ua.VariantType.Double)

    # Create new OPC data items for Roaster 200 
    R200_Malt_PV = AssetRoaster200.add_variable(addspace, "Malt_PV", 0, ua.VariantType.Double)
    R200_Malt_SP = AssetRoaster200.add_variable(addspace, "Malt_SP", 0, ua.VariantType.Int64)
    R200_Temperature_PV = AssetRoaster200.add_variable(addspace, "Temperature_PV", 0, ua.VariantType.Double)
    R200_Temperature_SP = AssetRoaster200.add_variable(addspace, "Temperature_SP", 0, ua.VariantType.Int64)
    R200_HoldTime_PT = AssetRoaster200.add_variable(addspace, "HoldTime_PT", 0, ua.VariantType.Int64)
    R200_HoldTime_ET = AssetRoaster200.add_variable(addspace, "HoldTime_ET", 0, ua.VariantType.Int64)
    R200_State = AssetRoaster200.add_variable(addspace, "State", 0, ua.VariantType.String)
    R200_Status = AssetRoaster200.add_variable(addspace, "Status", 0, ua.VariantType.String)
    R200_MaterialID = AssetRoaster200.add_variable(addspace, "MaterialID", 0, ua.VariantType.String)  
    R200_ProductionID = AssetRoaster200.add_variable(addspace, "ProductionID", 0, ua.VariantType.String) 
    R200_Cons_RawBarley_Item = AssetRoaster200.add_variable(addspace, "Cons_RawBarley_Item", 0, ua.VariantType.String)  
    R200_Cons_RawBarley_FromLot = AssetRoaster200.add_variable(addspace, "Cons_RawBarley_FromLot", 0, ua.VariantType.String)
    R200_Prod_RoastedBarley_ToLot = AssetRoaster200.add_variable(addspace, "Prod_RoastedBarley_ToLot", 0, ua.VariantType.String)
    R200_Prod_RoastedBarley_Item = AssetRoaster200.add_variable(addspace, "Prod_RoastedBarley_Item", 0, ua.VariantType.String)
    R200_UtilizationState = AssetRoaster200.add_variable(addspace, "UtilizationState", 0, ua.VariantType.String) 
    R200_Utilization = AssetRoaster200.add_variable(addspace, "Utilization", 0, ua.VariantType.String)
    R200_MaltAuger_PV = AssetRoaster200.add_variable(addspace, "MaltAuger_PV", 0, ua.VariantType.String)
    R200_MaltAuger_AuxContact = AssetRoaster200.add_variable(addspace, "MaltAuger_AuxContact", 0, ua.VariantType.Boolean)
    R200_Scrap = AssetRoaster200.add_variable(addspace, "Scrap", 0, ua.VariantType.Double)

    # Create new OPC data items for MaltMill 100
    MM100_Malt_PV = AssetMaltMill100.add_variable(addspace, "Malt_PV", 0, ua.VariantType.Double)
    MM100_Malt_SP = AssetMaltMill100.add_variable(addspace, "Malt_SP", 0, ua.VariantType.Double)
    MM100_MaltAuger_AuxContact = AssetMaltMill100.add_variable(addspace, "MaltAuger_AuxContact", 0, ua.VariantType.Boolean)
    MM100_MaltAuger_PV = AssetMaltMill100.add_variable(addspace, "MaltAuger_PV", 0, ua.VariantType.String)
    MM100_MaltMill_AuxContact = AssetMaltMill100.add_variable(addspace, "MaltMill_AuxContact", 0, ua.VariantType.Boolean)
    MM100_MaltMill_PV = AssetMaltMill100.add_variable(addspace, "MaltMill_PV", 0, ua.VariantType.String)
    MM100_State = AssetMaltMill100.add_variable(addspace, "State", 0, ua.VariantType.String)

     # Create new OPC data items for Mash Tun 100
    M100_Agitator_AuxContact = AssetMashTun100.add_variable(addspace, "Agitator_AuxContact", 0, ua.VariantType.Boolean)
    M100_Agitator_PV = AssetMashTun100.add_variable(addspace, "Agitator_PV", 0, ua.VariantType.String)
    M100_Cons_Malt_FromLot = AssetMashTun100.add_variable(addspace, "Cons_Malt_FromLot", 0, ua.VariantType.String)
    M100_Cons_Malt_Item = AssetMashTun100.add_variable(addspace, "Cons_Malt_Item", 0, ua.VariantType.String)
    M100_HoldTime_PT = AssetMashTun100.add_variable(addspace, "HoldTime_PT", 0, ua.VariantType.Int64)
    M100_HoldTime_ET = AssetMashTun100.add_variable(addspace, "HoldTime_ET", 0, ua.VariantType.Int64)
    M100_Level_PV = AssetMashTun100.add_variable(addspace, "Level_PV", 0, ua.VariantType.Double)
    M100_MaterialID = AssetMashTun100.add_variable(addspace, "MaterialID", 0, ua.VariantType.String)
    M100_State = AssetMashTun100.add_variable(addspace, "State", 0, ua.VariantType.String)
    M100_Status = AssetMashTun100.add_variable(addspace, "Status", 0, ua.VariantType.String)
    M100_OutletPump_AuxContact = AssetMashTun100.add_variable(addspace, "OutletPump_AuxContact", 0, ua.VariantType.Boolean)
    M100_OutletPump_PV = AssetMashTun100.add_variable(addspace, "OutletPump_PV", 0, ua.VariantType.String)
    M100_OutletValve_CLS = AssetMashTun100.add_variable(addspace, "OutletValve_CLS", 0, ua.VariantType.Boolean)
    M100_OutletValve_OLS = AssetMashTun100.add_variable(addspace, "OutletValve_OLS", 0, ua.VariantType.Boolean)
    M100_OutletValve_PV = AssetMashTun100.add_variable(addspace, "OutletValve_PV", 0, ua.VariantType.String)
    M100_Prod_Wort_Item = AssetMashTun100.add_variable(addspace, "Prod_Wort_Item", 0, ua.VariantType.String)
    M100_Prod_Wort_ToLot = AssetMashTun100.add_variable(addspace, "Prod_Wort_ToLot", 0, ua.VariantType.String)
    M100_ProductionID = AssetMashTun100.add_variable(addspace, "ProductionID", 0, ua.VariantType.String)
    M100_Scrap = AssetMashTun100.add_variable(addspace, "Scrap", 0, ua.VariantType.Double)
    M100_Scrap_ToLot = AssetMashTun100.add_variable(addspace, "Scrap_ToLot", 0, ua.VariantType.String)
    M100_ShipComplete = AssetMashTun100.add_variable(addspace, "ShipComplete", 0, ua.VariantType.Boolean)
    M100_SoakTempSP1 = AssetMashTun100.add_variable(addspace, "SoakTempSP1", 0, ua.VariantType.Int64)
    M100_SoakTempSP2 = AssetMashTun100.add_variable(addspace, "SoakTempSP2", 0, ua.VariantType.Int64)
    M100_SoakTimeSP1 = AssetMashTun100.add_variable(addspace, "SoakTimeSP1", 0, ua.VariantType.Int64)
    M100_SoakTimeSP2 = AssetMashTun100.add_variable(addspace, "SoakTimeSP2", 0, ua.VariantType.Int64)
    M100_SteamValve_CLS = AssetMashTun100.add_variable(addspace, "SteamValve_CLS", 0, ua.VariantType.Boolean)
    M100_SteamValve_OLS = AssetMashTun100.add_variable(addspace, "SteamValve_OLS", 0, ua.VariantType.Boolean)
    M100_SteamValve_PV = AssetMashTun100.add_variable(addspace, "SteamValve_PV", 0, ua.VariantType.String)
    M100_Temperature_PV = AssetMashTun100.add_variable(addspace, "Temperature_PV", 0, ua.VariantType.Double)
    M100_Temperature_SP = AssetMashTun100.add_variable(addspace, "Temperature_SP", 0, ua.VariantType.Int64)
    M100_UtilizationState = AssetMashTun100.add_variable(addspace, "UtilizationState", 0, ua.VariantType.String) 
    M100_Utilization = AssetMashTun100.add_variable(addspace, "Utilization", 0, ua.VariantType.String)
    M100_Water_PV = AssetMashTun100.add_variable(addspace, "Water_PV", 0, ua.VariantType.Double)
    M100_Water_SP = AssetMashTun100.add_variable(addspace, "Water_SP", 0, ua.VariantType.Int64)
    M100_WaterValve_CLS = AssetMashTun100.add_variable(addspace, "WaterValve_CLS", 0, ua.VariantType.Boolean)
    M100_WaterValve_OLS = AssetMashTun100.add_variable(addspace, "WaterValve_OLS", 0, ua.VariantType.Boolean)
    M100_WaterValve_PV = AssetMashTun100.add_variable(addspace, "WaterValve_PV", 0, ua.VariantType.String)
    M100_Wort_Item = AssetMashTun100.add_variable(addspace, "Wort_Item", 0, ua.VariantType.String)
    M100_Wort_PV = AssetMashTun100.add_variable(addspace, "Wort_PV", 0, ua.VariantType.Double)

    # Create new OPC data items for MaltMill 200
    MM200_Malt_PV = AssetMaltMill200.add_variable(addspace, "Malt_PV", 0, ua.VariantType.Double)
    MM200_Malt_SP = AssetMaltMill200.add_variable(addspace, "Malt_SP", 0, ua.VariantType.Double)
    MM200_MaltAuger_AuxContact = AssetMaltMill200.add_variable(addspace, "MaltAuger_AuxContact", 0, ua.VariantType.Boolean)
    MM200_MaltAuger_PV = AssetMaltMill200.add_variable(addspace, "MaltAuger_PV", 0, ua.VariantType.String)
    MM200_MaltMill_AuxContact = AssetMaltMill200.add_variable(addspace, "MaltMill_AuxContact", 0, ua.VariantType.Boolean)
    MM200_MaltMill_PV = AssetMaltMill200.add_variable(addspace, "MaltMill_PV", 0, ua.VariantType.String)
    MM200_State = AssetMaltMill200.add_variable(addspace, "State", 0, ua.VariantType.String)

    # Create new OPC data items for Mash Tun 200
    M200_Agitator_AuxContact = AssetMashTun200.add_variable(addspace, "Agitator_AuxContact", 0, ua.VariantType.Boolean)
    M200_Agitator_PV = AssetMashTun200.add_variable(addspace, "Agitator_PV", 0, ua.VariantType.String)
    M200_Cons_Malt_FromLot = AssetMashTun200.add_variable(addspace, "Cons_Malt_FromLot", 0, ua.VariantType.String)
    M200_Cons_Malt_Item = AssetMashTun200.add_variable(addspace, "Cons_Malt_Item", 0, ua.VariantType.String)
    M200_HoldTime_PT = AssetMashTun200.add_variable(addspace, "HoldTime_PT", 0, ua.VariantType.Int64)
    M200_HoldTime_ET = AssetMashTun200.add_variable(addspace, "HoldTime_ET", 0, ua.VariantType.Int64)
    M200_Level_PV = AssetMashTun200.add_variable(addspace, "Level_PV", 0, ua.VariantType.Double)
    M200_MaterialID = AssetMashTun200.add_variable(addspace, "MaterialID", 0, ua.VariantType.String)
    M200_State = AssetMashTun200.add_variable(addspace, "State", 0, ua.VariantType.String)
    M200_Status = AssetMashTun200.add_variable(addspace, "Status", 0, ua.VariantType.String)
    M200_OutletPump_AuxContact = AssetMashTun200.add_variable(addspace, "OutletPump_AuxContact", 0, ua.VariantType.Boolean)
    M200_OutletPump_PV = AssetMashTun200.add_variable(addspace, "OutletPump_PV", 0, ua.VariantType.String)
    M200_OutletValve_CLS = AssetMashTun200.add_variable(addspace, "OutletValve_CLS", 0, ua.VariantType.Boolean)
    M200_OutletValve_OLS = AssetMashTun200.add_variable(addspace, "OutletValve_OLS", 0, ua.VariantType.Boolean)
    M200_OutletValve_PV = AssetMashTun200.add_variable(addspace, "OutletValve_PV", 0, ua.VariantType.String)
    M200_Prod_Wort_Item = AssetMashTun200.add_variable(addspace, "Prod_Wort_Item", 0, ua.VariantType.String)
    M200_Prod_Wort_ToLot = AssetMashTun200.add_variable(addspace, "Prod_Wort_ToLot", 0, ua.VariantType.String)
    M200_ProductionID = AssetMashTun200.add_variable(addspace, "ProductionID", 0, ua.VariantType.String)
    M200_Scrap = AssetMashTun200.add_variable(addspace, "Scrap", 0, ua.VariantType.Double)
    M200_Scrap_ToLot = AssetMashTun200.add_variable(addspace, "Scrap_ToLot", 0, ua.VariantType.String)
    M200_ShipComplete = AssetMashTun200.add_variable(addspace, "ShipComplete", 0, ua.VariantType.Boolean)
    M200_SoakTempSP1 = AssetMashTun200.add_variable(addspace, "SoakTempSP1", 0, ua.VariantType.Int64)
    M200_SoakTempSP2 = AssetMashTun200.add_variable(addspace, "SoakTempSP2", 0, ua.VariantType.Int64)
    M200_SoakTimeSP1 = AssetMashTun200.add_variable(addspace, "SoakTimeSP1", 0, ua.VariantType.Int64)
    M200_SoakTimeSP2 = AssetMashTun200.add_variable(addspace, "SoakTimeSP2", 0, ua.VariantType.Int64)
    M200_SteamValve_CLS = AssetMashTun200.add_variable(addspace, "SteamValve_CLS", 0, ua.VariantType.Boolean)
    M200_SteamValve_OLS = AssetMashTun200.add_variable(addspace, "SteamValve_OLS", 0, ua.VariantType.Boolean)
    M200_SteamValve_PV = AssetMashTun200.add_variable(addspace, "SteamValve_PV", 0, ua.VariantType.String)
    M200_Temperature_PV = AssetMashTun200.add_variable(addspace, "Temperature_PV", 0, ua.VariantType.Double)
    M200_Temperature_SP = AssetMashTun200.add_variable(addspace, "Temperature_SP", 0, ua.VariantType.Int64)
    M200_UtilizationState = AssetMashTun200.add_variable(addspace, "UtilizationState", 0, ua.VariantType.String) 
    M200_Utilization = AssetMashTun200.add_variable(addspace, "Utilization", 0, ua.VariantType.String)
    M200_Water_PV = AssetMashTun200.add_variable(addspace, "Water_PV", 0, ua.VariantType.Double)
    M200_Water_SP = AssetMashTun200.add_variable(addspace, "Water_SP", 0, ua.VariantType.Int64)
    M200_WaterValve_CLS = AssetMashTun200.add_variable(addspace, "WaterValve_CLS", 0, ua.VariantType.Boolean)
    M200_WaterValve_OLS = AssetMashTun200.add_variable(addspace, "WaterValve_OLS", 0, ua.VariantType.Boolean)
    M200_WaterValve_PV = AssetMashTun200.add_variable(addspace, "WaterValve_PV", 0, ua.VariantType.String)
    M200_Wort_Item = AssetMashTun200.add_variable(addspace, "Wort_Item", 0, ua.VariantType.String)
    M200_Wort_PV = AssetMashTun200.add_variable(addspace, "Wort_PV", 0, ua.VariantType.Double)

    # Create new OPC data items for BoilKettle 100       
    BK100_Cons_Hops_FromLot = AssetBoilKettle100.add_variable(addspace, "Cons_Hops_FromLot", 0, ua.VariantType.String)    
    BK100_Cons_Hops_Item = AssetBoilKettle100.add_variable(addspace, "Cons_Hops_Item", 0, ua.VariantType.String)
    BK100_Cons_Wort_FromLot = AssetBoilKettle100.add_variable(addspace, "Cons_Wort_FromLot", 0, ua.VariantType.String)
    BK100_Cons_Wort_Item = AssetBoilKettle100.add_variable(addspace, "Cons_Wort_Item", 0, ua.VariantType.String)
    BK100_HoldTime_PT = AssetBoilKettle100.add_variable(addspace, "HoldTime_PT", 0, ua.VariantType.Int64)
    BK100_HoldTime_ET = AssetBoilKettle100.add_variable(addspace, "HoldTime_ET", 0, ua.VariantType.Int64)
    BK100_Level_PV = AssetBoilKettle100.add_variable(addspace, "Level_PV", 0, ua.VariantType.Double)
    BK100_MaterialID = AssetBoilKettle100.add_variable(addspace, "MaterialID", 0, ua.VariantType.String)
    BK100_State = AssetBoilKettle100.add_variable(addspace, "State", 0, ua.VariantType.String)
    BK100_Status = AssetBoilKettle100.add_variable(addspace, "Status", 0, ua.VariantType.String)
    BK100_OutletPump_AuxContact = AssetBoilKettle100.add_variable(addspace, "OutletPump_AuxContact", 0, ua.VariantType.Boolean)
    BK100_OutletPump_PV = AssetBoilKettle100.add_variable(addspace, "OutletPump_PV", 0, ua.VariantType.String)
    BK100_InletValve_CLS = AssetBoilKettle100.add_variable(addspace, "InletValve_CLS", 0, ua.VariantType.Boolean)
    BK100_InletValve_OLS = AssetBoilKettle100.add_variable(addspace, "InletValve_OLS", 0, ua.VariantType.Boolean)
    BK100_InletValve_PV = AssetBoilKettle100.add_variable(addspace, "InletValve_PV", 0, ua.VariantType.String)
    BK100_OutletValve_CLS = AssetBoilKettle100.add_variable(addspace, "OutletValve_CLS", 0, ua.VariantType.Boolean)
    BK100_OutletValve_OLS = AssetBoilKettle100.add_variable(addspace, "OutletValve_OLS", 0, ua.VariantType.Boolean)
    BK100_OutletValve_PV = AssetBoilKettle100.add_variable(addspace, "OutletValve_PV", 0, ua.VariantType.String)
    BK100_Prod_BrewedWort_Item = AssetBoilKettle100.add_variable(addspace, "Prod_BrewedWort_Item", 0, ua.VariantType.String)
    BK100_Prod_BrewedWort_ToLot = AssetBoilKettle100.add_variable(addspace, "Prod_BrewedWort_ToLot", 0, ua.VariantType.String)
    BK100_ProductionID = AssetBoilKettle100.add_variable(addspace, "ProductionID", 0, ua.VariantType.String)
    BK100_Scrap = AssetBoilKettle100.add_variable(addspace, "Scrap", 0, ua.VariantType.Double)
    BK100_SteamValve_CLS = AssetBoilKettle100.add_variable(addspace, "SteamValve_CLS", 0, ua.VariantType.Boolean)
    BK100_SteamValve_OLS = AssetBoilKettle100.add_variable(addspace, "SteamValve_OLS", 0, ua.VariantType.Boolean)
    BK100_SteamValve_PV = AssetBoilKettle100.add_variable(addspace, "SteamValve_PV", 0, ua.VariantType.String)
    BK100_Temperature_PV = AssetBoilKettle100.add_variable(addspace, "Temperature_PV", 0, ua.VariantType.Double)
    BK100_Temperature_SP = AssetBoilKettle100.add_variable(addspace, "Temperature_SP", 0, ua.VariantType.Int64)
    BK100_UtilizationState = AssetBoilKettle100.add_variable(addspace, "UtilizationState", 0, ua.VariantType.String) 
    BK100_Utilization = AssetBoilKettle100.add_variable(addspace, "Utilization", 0, ua.VariantType.String)
    BK100_HopsAuger_AuxContact = AssetBoilKettle100.add_variable(addspace, "HopsAuger_AuxContact", 0, ua.VariantType.Boolean)
    BK100_HopsAuger_PV = AssetBoilKettle100.add_variable(addspace, "HopsAuger_PV", 0, ua.VariantType.String)
    BK100_Wort_PV = AssetBoilKettle100.add_variable(addspace, "Wort_PV", 0, ua.VariantType.Double)
    BK100_Hops_PV = AssetBoilKettle100.add_variable(addspace, "Hops_PV", 0, ua.VariantType.Double)
    BK100_Hops_SP = AssetBoilKettle100.add_variable(addspace, "Hops_SP", 0, ua.VariantType.Double)
    BK100_BrewedWort_PV = AssetBoilKettle100.add_variable(addspace, "BrewedWort_PV", 0, ua.VariantType.Double)

    # Create new OPC data items for BoilKettle 200    
    BK200_Cons_Hops_FromLot = AssetBoilKettle200.add_variable(addspace, "Cons_Hops_FromLot", 0, ua.VariantType.String)   
    BK200_Cons_Hops_Item = AssetBoilKettle200.add_variable(addspace, "Cons_Hops_Item", 0, ua.VariantType.String) 
    BK200_Cons_Wort_FromLot = AssetBoilKettle200.add_variable(addspace, "Cons_Wort_FromLot", 0, ua.VariantType.String)
    BK200_Cons_Wort_Item = AssetBoilKettle200.add_variable(addspace, "Cons_Wort_Item", 0, ua.VariantType.String)
    BK200_HoldTime_PT = AssetBoilKettle200.add_variable(addspace, "HoldTime_PT", 0, ua.VariantType.Int64)
    BK200_HoldTime_ET = AssetBoilKettle200.add_variable(addspace, "HoldTime_ET", 0, ua.VariantType.Int64)
    BK200_Level_PV = AssetBoilKettle200.add_variable(addspace, "Level_PV", 0, ua.VariantType.Double)
    BK200_MaterialID = AssetBoilKettle200.add_variable(addspace, "MaterialID", 0, ua.VariantType.String)
    BK200_State = AssetBoilKettle200.add_variable(addspace, "State", 0, ua.VariantType.String)
    BK200_Status = AssetBoilKettle200.add_variable(addspace, "Status", 0, ua.VariantType.String)
    BK200_OutletPump_AuxContact = AssetBoilKettle200.add_variable(addspace, "OutletPump_AuxContact", 0, ua.VariantType.Boolean)
    BK200_OutletPump_PV = AssetBoilKettle200.add_variable(addspace, "OutletPump_PV", 0, ua.VariantType.String)
    BK200_InletValve_CLS = AssetBoilKettle200.add_variable(addspace, "InletValve_CLS", 0, ua.VariantType.Boolean)
    BK200_InletValve_OLS = AssetBoilKettle200.add_variable(addspace, "InletValve_OLS", 0, ua.VariantType.Boolean)
    BK200_InletValve_PV = AssetBoilKettle200.add_variable(addspace, "InletValve_PV", 0, ua.VariantType.String)
    BK200_OutletValve_CLS = AssetBoilKettle200.add_variable(addspace, "OutletValve_CLS", 0, ua.VariantType.Boolean)
    BK200_OutletValve_OLS = AssetBoilKettle200.add_variable(addspace, "OutletValve_OLS", 0, ua.VariantType.Boolean)
    BK200_OutletValve_PV = AssetBoilKettle200.add_variable(addspace, "OutletValve_PV", 0, ua.VariantType.String)
    BK200_Prod_BrewedWort_Item = AssetBoilKettle200.add_variable(addspace, "Prod_BrewedWort_Item", 0, ua.VariantType.String)
    BK200_Prod_BrewedWort_ToLot = AssetBoilKettle200.add_variable(addspace, "Prod_BrewedWort_ToLot", 0, ua.VariantType.String)
    BK200_ProductionID = AssetBoilKettle200.add_variable(addspace, "ProductionID", 0, ua.VariantType.String)
    BK200_Scrap = AssetBoilKettle200.add_variable(addspace, "Scrap", 0, ua.VariantType.Double)
    BK200_SteamValve_CLS = AssetBoilKettle200.add_variable(addspace, "SteamValve_CLS", 0, ua.VariantType.Boolean)
    BK200_SteamValve_OLS = AssetBoilKettle200.add_variable(addspace, "SteamValve_OLS", 0, ua.VariantType.Boolean)
    BK200_SteamValve_PV = AssetBoilKettle200.add_variable(addspace, "SteamValve_PV", 0, ua.VariantType.String)
    BK200_Temperature_PV = AssetBoilKettle200.add_variable(addspace, "Temperature_PV", 0, ua.VariantType.Double)
    BK200_Temperature_SP = AssetBoilKettle200.add_variable(addspace, "Temperature_SP", 0, ua.VariantType.Int64)
    BK200_UtilizationState = AssetBoilKettle200.add_variable(addspace, "UtilizationState", 0, ua.VariantType.String) 
    BK200_Utilization = AssetBoilKettle200.add_variable(addspace, "Utilization", 0, ua.VariantType.String)
    BK200_HopsAuger_AuxContact = AssetBoilKettle200.add_variable(addspace, "HopsAuger_AuxContact", 0, ua.VariantType.Boolean)
    BK200_HopsAuger_PV = AssetBoilKettle200.add_variable(addspace, "HopsAuger_PV", 0, ua.VariantType.String)
    BK200_Wort_PV = AssetBoilKettle200.add_variable(addspace, "Wort_PV", 0, ua.VariantType.Double)
    BK200_Hops_PV = AssetBoilKettle200.add_variable(addspace, "Hops_PV", 0, ua.VariantType.Double)
    BK200_Hops_SP = AssetBoilKettle200.add_variable(addspace, "Hops_SP", 0, ua.VariantType.Double)
    BK200_BrewedWort_PV = AssetBoilKettle200.add_variable(addspace, "BrewedWort_PV", 0, ua.VariantType.Double)

    # Create new OPC data items for Fermenter 100 
    F100_ChillWaterValve_CLS = AssetFermenter100.add_variable(addspace, "ChillWaterValve_CLS", 0, ua.VariantType.Boolean)
    F100_ChillWaterValve_OLS = AssetFermenter100.add_variable(addspace, "ChillWaterValve_OLS", 0, ua.VariantType.Boolean)
    F100_ChillWaterValve_PV = AssetFermenter100.add_variable(addspace, "ChillWaterValve_PV", 0, ua.VariantType.String)
    F100_Cons_BrewedWort_FromLot = AssetFermenter100.add_variable(addspace, "Cons_BrewedWort_FromLot", 0, ua.VariantType.String)    
    F100_Cons_BrewedWort_Item = AssetFermenter100.add_variable(addspace, "Cons_BrewedWort_Item", 0, ua.VariantType.String)
    F100_Cons_Yeast_FromLot = AssetFermenter100.add_variable(addspace, "Cons_Yeast_FromLot", 0, ua.VariantType.String)
    F100_Cons_Yeast_Item = AssetFermenter100.add_variable(addspace, "Cons_Yeast_Item", 0, ua.VariantType.String)
    F100_HoldTime_PT = AssetFermenter100.add_variable(addspace, "HoldTime_PT", 0, ua.VariantType.Int64)
    F100_HoldTime_ET = AssetFermenter100.add_variable(addspace, "HoldTime_ET", 0, ua.VariantType.Int64)
    F100_Level_PV = AssetFermenter100.add_variable(addspace, "Level_PV", 0, ua.VariantType.Double)
    F100_MaterialID = AssetFermenter100.add_variable(addspace, "MaterialID", 0, ua.VariantType.String)
    F100_State = AssetFermenter100.add_variable(addspace, "State", 0, ua.VariantType.String)
    F100_Status = AssetFermenter100.add_variable(addspace, "Status", 0, ua.VariantType.String)
    F100_GreenBeer_PV = AssetFermenter100.add_variable(addspace, "GreenBeer_PV", 0, ua.VariantType.Double)
    F100_InletValve_CLS = AssetFermenter100.add_variable(addspace, "InletValve_CLS", 0, ua.VariantType.Boolean)
    F100_InletValve_OLS = AssetFermenter100.add_variable(addspace, "InletValve_OLS", 0, ua.VariantType.Boolean)
    F100_InletValve_PV = AssetFermenter100.add_variable(addspace, "InletValve_PV", 0, ua.VariantType.String)
    F100_OutletPump_AuxContact = AssetFermenter100.add_variable(addspace, "OutletPump_AuxContact", 0, ua.VariantType.Boolean)
    F100_OutletPump_PV = AssetFermenter100.add_variable(addspace, "OutletPump_PV", 0, ua.VariantType.String)
    F100_OutletValve_CLS = AssetFermenter100.add_variable(addspace, "OutletValve_CLS", 0, ua.VariantType.Boolean)
    F100_OutletValve_OLS = AssetFermenter100.add_variable(addspace, "OutletValve_OLS", 0, ua.VariantType.Boolean)
    F100_OutletValve_PV = AssetFermenter100.add_variable(addspace, "OutletValve_PV", 0, ua.VariantType.String)
    F100_Prod_GreenBeer_Item = AssetFermenter100.add_variable(addspace, "Prod_GreenBeer_Item", 0, ua.VariantType.String)
    F100_Prod_GreenBeer_ToLot = AssetFermenter100.add_variable(addspace, "Prod_GreenBeer_ToLot", 0, ua.VariantType.String)
    F100_ProductionID = AssetFermenter100.add_variable(addspace, "ProductionID", 0, ua.VariantType.String)
    F100_Scrap = AssetFermenter100.add_variable(addspace, "Scrap", 0, ua.VariantType.Double)
    F100_ShipTo_Tank = AssetFermenter100.add_variable(addspace, "ShipTo_Tank", 0, ua.VariantType.Int64)
    F100_Temperature_PV = AssetFermenter100.add_variable(addspace, "Temperature_PV", 0, ua.VariantType.Double)
    F100_Temperature_SP = AssetFermenter100.add_variable(addspace, "Temperature_SP", 0, ua.VariantType.Int64)
    F100_UtilizationState = AssetFermenter100.add_variable(addspace, "UtilizationState", 0, ua.VariantType.String) 
    F100_Utilization = AssetFermenter100.add_variable(addspace, "Utilization", 0, ua.VariantType.String)
    F100_Yeast_PV = AssetFermenter100.add_variable(addspace, "Yeast_PV", 0, ua.VariantType.Double)
    F100_Yeast_SP = AssetFermenter100.add_variable(addspace, "Yeast_SP", 0, ua.VariantType.Double)
    F100_YeastPump_AuxContact = AssetFermenter100.add_variable(addspace, "YeastPump_AuxContact", 0, ua.VariantType.Boolean)
    F100_YeastPump_PV = AssetFermenter100.add_variable(addspace, "YeastPump_PV", 0, ua.VariantType.String)

    # Create new OPC data items for Fermenter 200
    F200_ChillWaterValve_CLS = AssetFermenter200.add_variable(addspace, "ChillWaterValve_CLS", 0, ua.VariantType.Boolean)
    F200_ChillWaterValve_OLS = AssetFermenter200.add_variable(addspace, "ChillWaterValve_OLS", 0, ua.VariantType.Boolean)
    F200_ChillWaterValve_PV = AssetFermenter200.add_variable(addspace, "ChillWaterValve_PV", 0, ua.VariantType.String)
    F200_Cons_BrewedWort_FromLot = AssetFermenter200.add_variable(addspace, "Cons_BrewedWort_FromLot", 0, ua.VariantType.String)    
    F200_Cons_BrewedWort_Item = AssetFermenter200.add_variable(addspace, "Cons_BrewedWort_Item", 0, ua.VariantType.String)
    F200_Cons_Yeast_FromLot = AssetFermenter200.add_variable(addspace, "Cons_Yeast_FromLot", 0, ua.VariantType.String)
    F200_Cons_Yeast_Item = AssetFermenter200.add_variable(addspace, "Cons_Yeast_Item", 0, ua.VariantType.String)
    F200_HoldTime_PT = AssetFermenter200.add_variable(addspace, "HoldTime_PT", 0, ua.VariantType.Int64)
    F200_HoldTime_ET = AssetFermenter200.add_variable(addspace, "HoldTime_ET", 0, ua.VariantType.Int64)
    F200_Level_PV = AssetFermenter200.add_variable(addspace, "Level_PV", 0, ua.VariantType.Double)
    F200_MaterialID = AssetFermenter200.add_variable(addspace, "MaterialID", 0, ua.VariantType.String)
    F200_State = AssetFermenter200.add_variable(addspace, "State", 0, ua.VariantType.String)
    F200_Status = AssetFermenter200.add_variable(addspace, "Status", 0, ua.VariantType.String)
    F200_GreenBeer_PV = AssetFermenter200.add_variable(addspace, "GreenBeer_PV", 0, ua.VariantType.Double)
    F200_InletValve_CLS = AssetFermenter200.add_variable(addspace, "InletValve_CLS", 0, ua.VariantType.Boolean)
    F200_InletValve_OLS = AssetFermenter200.add_variable(addspace, "InletValve_OLS", 0, ua.VariantType.Boolean)
    F200_InletValve_PV = AssetFermenter200.add_variable(addspace, "InletValve_PV", 0, ua.VariantType.String)
    F200_OutletPump_AuxContact = AssetFermenter200.add_variable(addspace, "OutletPump_AuxContact", 0, ua.VariantType.Boolean)
    F200_OutletPump_PV = AssetFermenter200.add_variable(addspace, "OutletPump_PV", 0, ua.VariantType.String)
    F200_OutletValve_CLS = AssetFermenter200.add_variable(addspace, "OutletValve_CLS", 0, ua.VariantType.Boolean)
    F200_OutletValve_OLS = AssetFermenter200.add_variable(addspace, "OutletValve_OLS", 0, ua.VariantType.Boolean)
    F200_OutletValve_PV = AssetFermenter200.add_variable(addspace, "OutletValve_PV", 0, ua.VariantType.String)
    F200_Prod_GreenBeer_Item = AssetFermenter200.add_variable(addspace, "Prod_GreenBeer_Item", 0, ua.VariantType.String)
    F200_Prod_GreenBeer_ToLot = AssetFermenter200.add_variable(addspace, "Prod_GreenBeer_ToLot", 0, ua.VariantType.String)
    F200_ProductionID = AssetFermenter200.add_variable(addspace, "ProductionID", 0, ua.VariantType.String)
    F200_Scrap = AssetFermenter200.add_variable(addspace, "Scrap", 0, ua.VariantType.Double)
    F200_ShipTo_Tank = AssetFermenter200.add_variable(addspace, "ShipTo_Tank", 0, ua.VariantType.Int64)
    F200_Temperature_PV = AssetFermenter200.add_variable(addspace, "Temperature_PV", 0, ua.VariantType.Double)
    F200_Temperature_SP = AssetFermenter200.add_variable(addspace, "Temperature_SP", 0, ua.VariantType.Int64)
    F200_UtilizationState = AssetFermenter200.add_variable(addspace, "UtilizationState", 0, ua.VariantType.String) 
    F200_Utilization = AssetFermenter200.add_variable(addspace, "Utilization", 0, ua.VariantType.String)
    F200_Yeast_PV = AssetFermenter200.add_variable(addspace, "Yeast_PV", 0, ua.VariantType.Double)
    F200_Yeast_SP = AssetFermenter200.add_variable(addspace, "Yeast_SP", 0, ua.VariantType.Double)
    F200_YeastPump_AuxContact = AssetFermenter200.add_variable(addspace, "YeastPump_AuxContact", 0, ua.VariantType.Boolean)
    F200_YeastPump_PV = AssetFermenter200.add_variable(addspace, "YeastPump_PV", 0, ua.VariantType.String)

    # Create new OPC data items for Bright Tank 301
    BT301_AllocatedFrom = AssetBrightTank301.add_variable(addspace, "AllocatedFrom", 0, ua.VariantType.Int64)
    BT301_ChillWaterValve_CLS = AssetBrightTank301.add_variable(addspace, "ChillWaterValve_CLS", 0, ua.VariantType.Boolean)
    BT301_ChillWaterValve_OLS = AssetBrightTank301.add_variable(addspace, "ChillWaterValve_OLS", 0, ua.VariantType.Boolean)
    BT301_ChillWaterValve_PV = AssetBrightTank301.add_variable(addspace, "ChillWaterValve_PV", 0, ua.VariantType.String)
    BT301_Cons_GreenBeer_FromLot = AssetBrightTank301.add_variable(addspace, "Cons_GreenBeer_FromLot", 0, ua.VariantType.String)    
    BT301_Cons_GreenBeer_Item = AssetBrightTank301.add_variable(addspace, "Cons_GreenBeer_Item", 0, ua.VariantType.String)
    BT301_HoldTime_PT = AssetBrightTank301.add_variable(addspace, "HoldTime_PT", 0, ua.VariantType.Int64)
    BT301_HoldTime_ET = AssetBrightTank301.add_variable(addspace, "HoldTime_ET", 0, ua.VariantType.Int64)
    BT301_Level_PV = AssetBrightTank301.add_variable(addspace, "Level_PV", 0, ua.VariantType.Double)
    BT301_MaterialID = AssetBrightTank301.add_variable(addspace, "MaterialID", 0, ua.VariantType.String)
    BT301_State = AssetBrightTank301.add_variable(addspace, "State", 0, ua.VariantType.String)
    BT301_Status = AssetBrightTank301.add_variable(addspace, "Status", 0, ua.VariantType.String)
    BT301_Beer_PV = AssetBrightTank301.add_variable(addspace, "Beer_PV", 0, ua.VariantType.Double)
    BT301_Beer_SP = AssetBrightTank301.add_variable(addspace, "Beer_SP", 0, ua.VariantType.Double)
    BT301_InletValve_CLS = AssetBrightTank301.add_variable(addspace, "InletValve_CLS", 0, ua.VariantType.Boolean)
    BT301_InletValve_OLS = AssetBrightTank301.add_variable(addspace, "InletValve_OLS", 0, ua.VariantType.Boolean)
    BT301_InletValve_PV = AssetBrightTank301.add_variable(addspace, "InletValve_PV", 0, ua.VariantType.String)
    BT301_OutletPump_AuxContact = AssetBrightTank301.add_variable(addspace, "OutletPump_AuxContact", 0, ua.VariantType.Boolean)
    BT301_OutletPump_PV = AssetBrightTank301.add_variable(addspace, "OutletPump_PV", 0, ua.VariantType.String)
    BT301_OutletValve_CLS = AssetBrightTank301.add_variable(addspace, "OutletValve_CLS", 0, ua.VariantType.Boolean)
    BT301_OutletValve_OLS = AssetBrightTank301.add_variable(addspace, "OutletValve_OLS", 0, ua.VariantType.Boolean)
    BT301_OutletValve_PV = AssetBrightTank301.add_variable(addspace, "OutletValve_PV", 0, ua.VariantType.String)
    BT301_Prod_Beer_Item = AssetBrightTank301.add_variable(addspace, "Prod_Beer_Item", 0, ua.VariantType.String)
    BT301_Prod_Beer_ToLot = AssetBrightTank301.add_variable(addspace, "Prod_Beer_ToLot", 0, ua.VariantType.String)
    BT301_ProductionID = AssetBrightTank301.add_variable(addspace, "ProductionID", 0, ua.VariantType.String)  
    BT301_Temperature_PV = AssetBrightTank301.add_variable(addspace, "Temperature_PV", 0, ua.VariantType.Double)
    BT301_Temperature_SP = AssetBrightTank301.add_variable(addspace, "Temperature_SP", 0, ua.VariantType.Int64)
    BT301_UtilizationState = AssetBrightTank301.add_variable(addspace, "UtilizationState", 0, ua.VariantType.String) 
    BT301_Utilization = AssetBrightTank301.add_variable(addspace, "Utilization", 0, ua.VariantType.String)  
    BT301_BeerShipped = AssetBrightTank301.add_variable(addspace, "BeerShipped", 0, ua.VariantType.Double)
    BT301_ShipTo_Tank = AssetBrightTank301.add_variable(addspace, "ShipTo_Tank", 0, ua.VariantType.Int64)

    # Create new OPC data items for Bright Tank 302
    BT302_AllocatedFrom = AssetBrightTank302.add_variable(addspace, "AllocatedFrom", 0, ua.VariantType.Int64)
    BT302_ChillWaterValve_CLS = AssetBrightTank302.add_variable(addspace, "ChillWaterValve_CLS", 0, ua.VariantType.Boolean)
    BT302_ChillWaterValve_OLS = AssetBrightTank302.add_variable(addspace, "ChillWaterValve_OLS", 0, ua.VariantType.Boolean)
    BT302_ChillWaterValve_PV = AssetBrightTank302.add_variable(addspace, "ChillWaterValve_PV", 0, ua.VariantType.String)
    BT302_Cons_GreenBeer_FromLot = AssetBrightTank302.add_variable(addspace, "Cons_GreenBeer_FromLot", 0, ua.VariantType.String)    
    BT302_Cons_GreenBeer_Item = AssetBrightTank302.add_variable(addspace, "Cons_GreenBeer_Item", 0, ua.VariantType.String)
    BT302_HoldTime_PT = AssetBrightTank302.add_variable(addspace, "HoldTime_PT", 0, ua.VariantType.Int64)
    BT302_HoldTime_ET = AssetBrightTank302.add_variable(addspace, "HoldTime_ET", 0, ua.VariantType.Int64)
    BT302_Level_PV = AssetBrightTank302.add_variable(addspace, "Level_PV", 0, ua.VariantType.Double)
    BT302_MaterialID = AssetBrightTank302.add_variable(addspace, "MaterialID", 0, ua.VariantType.String)
    BT302_State = AssetBrightTank302.add_variable(addspace, "State", 0, ua.VariantType.String)
    BT302_Status = AssetBrightTank302.add_variable(addspace, "Status", 0, ua.VariantType.String)
    BT302_Beer_PV = AssetBrightTank302.add_variable(addspace, "Beer_PV", 0, ua.VariantType.Double)
    BT302_Beer_SP = AssetBrightTank302.add_variable(addspace, "Beer_SP", 0, ua.VariantType.Double)
    BT302_InletValve_CLS = AssetBrightTank302.add_variable(addspace, "InletValve_CLS", 0, ua.VariantType.Boolean)
    BT302_InletValve_OLS = AssetBrightTank302.add_variable(addspace, "InletValve_OLS", 0, ua.VariantType.Boolean)
    BT302_InletValve_PV = AssetBrightTank302.add_variable(addspace, "InletValve_PV", 0, ua.VariantType.String)
    BT302_OutletPump_AuxContact = AssetBrightTank302.add_variable(addspace, "OutletPump_AuxContact", 0, ua.VariantType.Boolean)
    BT302_OutletPump_PV = AssetBrightTank302.add_variable(addspace, "OutletPump_PV", 0, ua.VariantType.String)
    BT302_OutletValve_CLS = AssetBrightTank302.add_variable(addspace, "OutletValve_CLS", 0, ua.VariantType.Boolean)
    BT302_OutletValve_OLS = AssetBrightTank302.add_variable(addspace, "OutletValve_OLS", 0, ua.VariantType.Boolean)
    BT302_OutletValve_PV = AssetBrightTank302.add_variable(addspace, "OutletValve_PV", 0, ua.VariantType.String)
    BT302_Prod_Beer_Item = AssetBrightTank302.add_variable(addspace, "Prod_Beer_Item", 0, ua.VariantType.String)
    BT302_Prod_Beer_ToLot = AssetBrightTank302.add_variable(addspace, "Prod_Beer_ToLot", 0, ua.VariantType.String)
    BT302_ProductionID = AssetBrightTank302.add_variable(addspace, "ProductionID", 0, ua.VariantType.String)  
    BT302_Temperature_PV = AssetBrightTank302.add_variable(addspace, "Temperature_PV", 0, ua.VariantType.Double)
    BT302_Temperature_SP = AssetBrightTank302.add_variable(addspace, "Temperature_SP", 0, ua.VariantType.Int64)
    BT302_UtilizationState = AssetBrightTank302.add_variable(addspace, "UtilizationState", 0, ua.VariantType.String) 
    BT302_Utilization = AssetBrightTank302.add_variable(addspace, "Utilization", 0, ua.VariantType.String)  
    BT302_BeerShipped = AssetBrightTank302.add_variable(addspace, "BeerShipped", 0, ua.VariantType.Double)
    BT302_ShipTo_Tank = AssetBrightTank302.add_variable(addspace, "ShipTo_Tank", 0, ua.VariantType.Int64)

    # Create new OPC data items for Bright Tank 303
    BT303_AllocatedFrom = AssetBrightTank303.add_variable(addspace, "AllocatedFrom", 0, ua.VariantType.Int64)
    BT303_ChillWaterValve_CLS = AssetBrightTank303.add_variable(addspace, "ChillWaterValve_CLS", 0, ua.VariantType.Boolean)
    BT303_ChillWaterValve_OLS = AssetBrightTank303.add_variable(addspace, "ChillWaterValve_OLS", 0, ua.VariantType.Boolean)
    BT303_ChillWaterValve_PV = AssetBrightTank303.add_variable(addspace, "ChillWaterValve_PV", 0, ua.VariantType.String)
    BT303_Cons_GreenBeer_FromLot = AssetBrightTank303.add_variable(addspace, "Cons_GreenBeer_FromLot", 0, ua.VariantType.String)    
    BT303_Cons_GreenBeer_Item = AssetBrightTank303.add_variable(addspace, "Cons_GreenBeer_Item", 0, ua.VariantType.String)
    BT303_HoldTime_PT = AssetBrightTank303.add_variable(addspace, "HoldTime_PT", 0, ua.VariantType.Int64)
    BT303_HoldTime_ET = AssetBrightTank303.add_variable(addspace, "HoldTime_ET", 0, ua.VariantType.Int64)
    BT303_Level_PV = AssetBrightTank303.add_variable(addspace, "Level_PV", 0, ua.VariantType.Double)
    BT303_MaterialID = AssetBrightTank303.add_variable(addspace, "MaterialID", 0, ua.VariantType.String)
    BT303_State = AssetBrightTank303.add_variable(addspace, "State", 0, ua.VariantType.String)
    BT303_Status = AssetBrightTank303.add_variable(addspace, "Status", 0, ua.VariantType.String)
    BT303_Beer_PV = AssetBrightTank303.add_variable(addspace, "Beer_PV", 0, ua.VariantType.Double)
    BT303_Beer_SP = AssetBrightTank303.add_variable(addspace, "Beer_SP", 0, ua.VariantType.Double)
    BT303_InletValve_CLS = AssetBrightTank303.add_variable(addspace, "InletValve_CLS", 0, ua.VariantType.Boolean)
    BT303_InletValve_OLS = AssetBrightTank303.add_variable(addspace, "InletValve_OLS", 0, ua.VariantType.Boolean)
    BT303_InletValve_PV = AssetBrightTank303.add_variable(addspace, "InletValve_PV", 0, ua.VariantType.String)
    BT303_OutletPump_AuxContact = AssetBrightTank303.add_variable(addspace, "OutletPump_AuxContact", 0, ua.VariantType.Boolean)
    BT303_OutletPump_PV = AssetBrightTank303.add_variable(addspace, "OutletPump_PV", 0, ua.VariantType.String)
    BT303_OutletValve_CLS = AssetBrightTank303.add_variable(addspace, "OutletValve_CLS", 0, ua.VariantType.Boolean)
    BT303_OutletValve_OLS = AssetBrightTank303.add_variable(addspace, "OutletValve_OLS", 0, ua.VariantType.Boolean)
    BT303_OutletValve_PV = AssetBrightTank303.add_variable(addspace, "OutletValve_PV", 0, ua.VariantType.String)
    BT303_Prod_Beer_Item = AssetBrightTank303.add_variable(addspace, "Prod_Beer_Item", 0, ua.VariantType.String)
    BT303_Prod_Beer_ToLot = AssetBrightTank303.add_variable(addspace, "Prod_Beer_ToLot", 0, ua.VariantType.String)
    BT303_ProductionID = AssetBrightTank303.add_variable(addspace, "ProductionID", 0, ua.VariantType.String)  
    BT303_Temperature_PV = AssetBrightTank303.add_variable(addspace, "Temperature_PV", 0, ua.VariantType.Double)
    BT303_Temperature_SP = AssetBrightTank303.add_variable(addspace, "Temperature_SP", 0, ua.VariantType.Int64)
    BT303_UtilizationState = AssetBrightTank303.add_variable(addspace, "UtilizationState", 0, ua.VariantType.String) 
    BT303_Utilization = AssetBrightTank303.add_variable(addspace, "Utilization", 0, ua.VariantType.String)  
    BT303_BeerShipped = AssetBrightTank303.add_variable(addspace, "BeerShipped", 0, ua.VariantType.Double)
    BT303_ShipTo_Tank = AssetBrightTank303.add_variable(addspace, "ShipTo_Tank", 0, ua.VariantType.Int64)

    # Create new OPC data items for Bright Tank 304
    BT304_AllocatedFrom = AssetBrightTank304.add_variable(addspace, "AllocatedFrom", 0, ua.VariantType.Int64)
    BT304_ChillWaterValve_CLS = AssetBrightTank304.add_variable(addspace, "ChillWaterValve_CLS", 0, ua.VariantType.Boolean)
    BT304_ChillWaterValve_OLS = AssetBrightTank304.add_variable(addspace, "ChillWaterValve_OLS", 0, ua.VariantType.Boolean)
    BT304_ChillWaterValve_PV = AssetBrightTank304.add_variable(addspace, "ChillWaterValve_PV", 0, ua.VariantType.String)
    BT304_Cons_GreenBeer_FromLot = AssetBrightTank304.add_variable(addspace, "Cons_GreenBeer_FromLot", 0, ua.VariantType.String)    
    BT304_Cons_GreenBeer_Item = AssetBrightTank304.add_variable(addspace, "Cons_GreenBeer_Item", 0, ua.VariantType.String)
    BT304_HoldTime_PT = AssetBrightTank304.add_variable(addspace, "HoldTime_PT", 0, ua.VariantType.Int64)
    BT304_HoldTime_ET = AssetBrightTank304.add_variable(addspace, "HoldTime_ET", 0, ua.VariantType.Int64)
    BT304_Level_PV = AssetBrightTank304.add_variable(addspace, "Level_PV", 0, ua.VariantType.Double)
    BT304_MaterialID = AssetBrightTank304.add_variable(addspace, "MaterialID", 0, ua.VariantType.String)
    BT304_State = AssetBrightTank304.add_variable(addspace, "State", 0, ua.VariantType.String)
    BT304_Status = AssetBrightTank304.add_variable(addspace, "Status", 0, ua.VariantType.String)
    BT304_Beer_PV = AssetBrightTank304.add_variable(addspace, "Beer_PV", 0, ua.VariantType.Double)
    BT304_Beer_SP = AssetBrightTank304.add_variable(addspace, "Beer_SP", 0, ua.VariantType.Double)
    BT304_InletValve_CLS = AssetBrightTank304.add_variable(addspace, "InletValve_CLS", 0, ua.VariantType.Boolean)
    BT304_InletValve_OLS = AssetBrightTank304.add_variable(addspace, "InletValve_OLS", 0, ua.VariantType.Boolean)
    BT304_InletValve_PV = AssetBrightTank304.add_variable(addspace, "InletValve_PV", 0, ua.VariantType.String)
    BT304_OutletPump_AuxContact = AssetBrightTank304.add_variable(addspace, "OutletPump_AuxContact", 0, ua.VariantType.Boolean)
    BT304_OutletPump_PV = AssetBrightTank304.add_variable(addspace, "OutletPump_PV", 0, ua.VariantType.String)
    BT304_OutletValve_CLS = AssetBrightTank304.add_variable(addspace, "OutletValve_CLS", 0, ua.VariantType.Boolean)
    BT304_OutletValve_OLS = AssetBrightTank304.add_variable(addspace, "OutletValve_OLS", 0, ua.VariantType.Boolean)
    BT304_OutletValve_PV = AssetBrightTank304.add_variable(addspace, "OutletValve_PV", 0, ua.VariantType.String)
    BT304_Prod_Beer_Item = AssetBrightTank304.add_variable(addspace, "Prod_Beer_Item", 0, ua.VariantType.String)
    BT304_Prod_Beer_ToLot = AssetBrightTank304.add_variable(addspace, "Prod_Beer_ToLot", 0, ua.VariantType.String)
    BT304_ProductionID = AssetBrightTank304.add_variable(addspace, "ProductionID", 0, ua.VariantType.String)  
    BT304_Temperature_PV = AssetBrightTank304.add_variable(addspace, "Temperature_PV", 0, ua.VariantType.Double)
    BT304_Temperature_SP = AssetBrightTank304.add_variable(addspace, "Temperature_SP", 0, ua.VariantType.Int64)
    BT304_UtilizationState = AssetBrightTank304.add_variable(addspace, "UtilizationState", 0, ua.VariantType.String) 
    BT304_Utilization = AssetBrightTank304.add_variable(addspace, "Utilization", 0, ua.VariantType.String)  
    BT304_BeerShipped = AssetBrightTank304.add_variable(addspace, "BeerShipped", 0, ua.VariantType.Double)
    BT304_ShipTo_Tank = AssetBrightTank304.add_variable(addspace, "ShipTo_Tank", 0, ua.VariantType.Int64)

    # Create new OPC data items for Bright Tank 305
    BT305_AllocatedFrom = AssetBrightTank305.add_variable(addspace, "AllocatedFrom", 0, ua.VariantType.Int64)
    BT305_ChillWaterValve_CLS = AssetBrightTank305.add_variable(addspace, "ChillWaterValve_CLS", 0, ua.VariantType.Boolean)
    BT305_ChillWaterValve_OLS = AssetBrightTank305.add_variable(addspace, "ChillWaterValve_OLS", 0, ua.VariantType.Boolean)
    BT305_ChillWaterValve_PV = AssetBrightTank305.add_variable(addspace, "ChillWaterValve_PV", 0, ua.VariantType.String)
    BT305_Cons_GreenBeer_FromLot = AssetBrightTank305.add_variable(addspace, "Cons_GreenBeer_FromLot", 0, ua.VariantType.String)    
    BT305_Cons_GreenBeer_Item = AssetBrightTank305.add_variable(addspace, "Cons_GreenBeer_Item", 0, ua.VariantType.String)
    BT305_HoldTime_PT = AssetBrightTank305.add_variable(addspace, "HoldTime_PT", 0, ua.VariantType.Int64)
    BT305_HoldTime_ET = AssetBrightTank305.add_variable(addspace, "HoldTime_ET", 0, ua.VariantType.Int64)
    BT305_Level_PV = AssetBrightTank305.add_variable(addspace, "Level_PV", 0, ua.VariantType.Double)
    BT305_MaterialID = AssetBrightTank305.add_variable(addspace, "MaterialID", 0, ua.VariantType.String)
    BT305_State = AssetBrightTank305.add_variable(addspace, "State", 0, ua.VariantType.String)
    BT305_Status = AssetBrightTank305.add_variable(addspace, "Status", 0, ua.VariantType.String)
    BT305_Beer_PV = AssetBrightTank305.add_variable(addspace, "Beer_PV", 0, ua.VariantType.Double)
    BT305_Beer_SP = AssetBrightTank305.add_variable(addspace, "Beer_SP", 0, ua.VariantType.Double)
    BT305_InletValve_CLS = AssetBrightTank305.add_variable(addspace, "InletValve_CLS", 0, ua.VariantType.Boolean)
    BT305_InletValve_OLS = AssetBrightTank305.add_variable(addspace, "InletValve_OLS", 0, ua.VariantType.Boolean)
    BT305_InletValve_PV = AssetBrightTank305.add_variable(addspace, "InletValve_PV", 0, ua.VariantType.String)
    BT305_OutletPump_AuxContact = AssetBrightTank305.add_variable(addspace, "OutletPump_AuxContact", 0, ua.VariantType.Boolean)
    BT305_OutletPump_PV = AssetBrightTank305.add_variable(addspace, "OutletPump_PV", 0, ua.VariantType.String)
    BT305_OutletValve_CLS = AssetBrightTank305.add_variable(addspace, "OutletValve_CLS", 0, ua.VariantType.Boolean)
    BT305_OutletValve_OLS = AssetBrightTank305.add_variable(addspace, "OutletValve_OLS", 0, ua.VariantType.Boolean)
    BT305_OutletValve_PV = AssetBrightTank305.add_variable(addspace, "OutletValve_PV", 0, ua.VariantType.String)
    BT305_Prod_Beer_Item = AssetBrightTank305.add_variable(addspace, "Prod_Beer_Item", 0, ua.VariantType.String)
    BT305_Prod_Beer_ToLot = AssetBrightTank305.add_variable(addspace, "Prod_Beer_ToLot", 0, ua.VariantType.String)
    BT305_ProductionID = AssetBrightTank305.add_variable(addspace, "ProductionID", 0, ua.VariantType.String)  
    BT305_Temperature_PV = AssetBrightTank305.add_variable(addspace, "Temperature_PV", 0, ua.VariantType.Double)
    BT305_Temperature_SP = AssetBrightTank305.add_variable(addspace, "Temperature_SP", 0, ua.VariantType.Int64)
    BT305_UtilizationState = AssetBrightTank305.add_variable(addspace, "UtilizationState", 0, ua.VariantType.String) 
    BT305_Utilization = AssetBrightTank305.add_variable(addspace, "Utilization", 0, ua.VariantType.String)  
    BT305_BeerShipped = AssetBrightTank305.add_variable(addspace, "BeerShipped", 0, ua.VariantType.Double)
    BT305_ShipTo_Tank = AssetBrightTank305.add_variable(addspace, "ShipTo_Tank", 0, ua.VariantType.Int64)

    # Create new OPC data items for BottlingLine 401 
    BL401_AllocatedFrom = AssetBottleLine401.add_variable(addspace, "AllocatedFrom", 0, ua.VariantType.Int64)
    BL401_Beer_PV = AssetBottleLine401.add_variable(addspace, "Beer_PV", 0, ua.VariantType.Double)
    BL401_Bottle_PV = AssetBottleLine401.add_variable(addspace, "Bottle_PV", 0, ua.VariantType.Int64)
    BL401_Bottle_SP = AssetBottleLine401.add_variable(addspace, "Bottle_SP", 0, ua.VariantType.Int64)
    BL401_Cons_Beer_FromLot = AssetBottleLine401.add_variable(addspace, "Cons_Beer_FromLot", 0, ua.VariantType.String)
    BL401_Cons_Beer_Item = AssetBottleLine401.add_variable(addspace, "Cons_Beer_Item", 0, ua.VariantType.String)
    BL401_Cons_Bottle_FromLot = AssetBottleLine401.add_variable(addspace, "Cons_Bottle_FromLot", 0, ua.VariantType.String)
    BL401_Cons_Bottle_Item = AssetBottleLine401.add_variable(addspace, "Cons_Bottle_Item", 0, ua.VariantType.String)
    BL401_Cons_Cap_FromLot = AssetBottleLine401.add_variable(addspace, "Cons_Cap_FromLot", 0, ua.VariantType.String)
    BL401_Cons_Cap_Item = AssetBottleLine401.add_variable(addspace, "Cons_Cap_Item", 0, ua.VariantType.String)
    BL401_Cons_Label_FromLot = AssetBottleLine401.add_variable(addspace, "Cons_Label_FromLot", 0, ua.VariantType.String)
    BL401_Cons_Label_Item = AssetBottleLine401.add_variable(addspace, "Cons_Label_Item", 0, ua.VariantType.String)
    BL401_Level_PV = AssetBottleLine401.add_variable(addspace, "Level_PV", 0, ua.VariantType.Double)
    BL401_MaterialID = AssetBottleLine401.add_variable(addspace, "MaterialID", 0, ua.VariantType.String)
    BL401_Prod_BottledBeer_Item = AssetBottleLine401.add_variable(addspace, "Prod_BottledBeer_Item", 0, ua.VariantType.String)
    BL401_Prod_BottledBeer_ToLot = AssetBottleLine401.add_variable(addspace, "Prod_BottledBeer_ToLot", 0, ua.VariantType.String)
    BL401_ProductionID = AssetBottleLine401.add_variable(addspace, "ProductionID", 0, ua.VariantType.String)
    BL401_Speed_PV = AssetBottleLine401.add_variable(addspace, "Speed_PV", 0, ua.VariantType.Double)
    BL401_Speed_SP = AssetBottleLine401.add_variable(addspace, "Speed_SP", 0, ua.VariantType.Int64)
    BL401_Temperature_PV = AssetBottleLine401.add_variable(addspace, "Temperature_PV", 0, ua.VariantType.Double)
    BL401_Temperature_SP = AssetBottleLine401.add_variable(addspace, "Temperature_SP", 0, ua.VariantType.Int64)
    BL401_HoldTime_PT = AssetBottleLine401.add_variable(addspace, "HoldTime_PT", 0, ua.VariantType.Int64)
    BL401_HoldTime_ET = AssetBottleLine401.add_variable(addspace, "HoldTime_ET", 0, ua.VariantType.Int64)
    BL401_State = AssetBottleLine401.add_variable(addspace, "State", 0, ua.VariantType.String)
    BL401_Status = AssetBottleLine401.add_variable(addspace, "Status", 0, ua.VariantType.String)        
    BL401_UtilizationState = AssetBottleLine401.add_variable(addspace, "UtilizationState", 0, ua.VariantType.String) 
    BL401_Utilization = AssetBottleLine401.add_variable(addspace, "Utilization", 0, ua.VariantType.String)        
    BL401_Scrap = AssetBottleLine401.add_variable(addspace, "Scrap", 0, ua.VariantType.Double)

    # Create new OPC data items for BottlingLine 402 
    BL402_AllocatedFrom = AssetBottleLine402.add_variable(addspace, "AllocatedFrom", 0, ua.VariantType.Int64)
    BL402_Beer_PV = AssetBottleLine402.add_variable(addspace, "Beer_PV", 0, ua.VariantType.Double)
    BL402_Bottle_PV = AssetBottleLine402.add_variable(addspace, "Bottle_PV", 0, ua.VariantType.Int64)
    BL402_Bottle_SP = AssetBottleLine402.add_variable(addspace, "Bottle_SP", 0, ua.VariantType.Int64)
    BL402_Cons_Beer_FromLot = AssetBottleLine402.add_variable(addspace, "Cons_Beer_FromLot", 0, ua.VariantType.String)
    BL402_Cons_Beer_Item = AssetBottleLine402.add_variable(addspace, "Cons_Beer_Item", 0, ua.VariantType.String)
    BL402_Cons_Bottle_FromLot = AssetBottleLine402.add_variable(addspace, "Cons_Bottle_FromLot", 0, ua.VariantType.String)
    BL402_Cons_Bottle_Item = AssetBottleLine402.add_variable(addspace, "Cons_Bottle_Item", 0, ua.VariantType.String)
    BL402_Cons_Cap_FromLot = AssetBottleLine402.add_variable(addspace, "Cons_Cap_FromLot", 0, ua.VariantType.String)
    BL402_Cons_Cap_Item = AssetBottleLine402.add_variable(addspace, "Cons_Cap_Item", 0, ua.VariantType.String)
    BL402_Cons_Label_FromLot = AssetBottleLine402.add_variable(addspace, "Cons_Label_FromLot", 0, ua.VariantType.String)
    BL402_Cons_Label_Item = AssetBottleLine402.add_variable(addspace, "Cons_Label_Item", 0, ua.VariantType.String)
    BL402_Level_PV = AssetBottleLine402.add_variable(addspace, "Level_PV", 0, ua.VariantType.Double)
    BL402_MaterialID = AssetBottleLine402.add_variable(addspace, "MaterialID", 0, ua.VariantType.String)
    BL402_Prod_BottledBeer_Item = AssetBottleLine402.add_variable(addspace, "Prod_BottledBeer_Item", 0, ua.VariantType.String)
    BL402_Prod_BottledBeer_ToLot = AssetBottleLine402.add_variable(addspace, "Prod_BottledBeer_ToLot", 0, ua.VariantType.String)
    BL402_ProductionID = AssetBottleLine402.add_variable(addspace, "ProductionID", 0, ua.VariantType.String)
    BL402_Speed_PV = AssetBottleLine402.add_variable(addspace, "Speed_PV", 0, ua.VariantType.Double)
    BL402_Speed_SP = AssetBottleLine402.add_variable(addspace, "Speed_SP", 0, ua.VariantType.Int64)
    BL402_Temperature_PV = AssetBottleLine402.add_variable(addspace, "Temperature_PV", 0, ua.VariantType.Double)
    BL402_Temperature_SP = AssetBottleLine402.add_variable(addspace, "Temperature_SP", 0, ua.VariantType.Int64)
    BL402_HoldTime_PT = AssetBottleLine402.add_variable(addspace, "HoldTime_PT", 0, ua.VariantType.Int64)
    BL402_HoldTime_ET = AssetBottleLine402.add_variable(addspace, "HoldTime_ET", 0, ua.VariantType.Int64)
    BL402_State = AssetBottleLine402.add_variable(addspace, "State", 0, ua.VariantType.String)
    BL402_Status = AssetBottleLine402.add_variable(addspace, "Status", 0, ua.VariantType.String)        
    BL402_UtilizationState = AssetBottleLine402.add_variable(addspace, "UtilizationState", 0, ua.VariantType.String) 
    BL402_Utilization = AssetBottleLine402.add_variable(addspace, "Utilization", 0, ua.VariantType.String)        
    BL402_Scrap = AssetBottleLine402.add_variable(addspace, "Scrap", 0, ua.VariantType.Double)

    # Create new OPC data items for BottlingLine 403 
    BL403_AllocatedFrom = AssetBottleLine403.add_variable(addspace, "AllocatedFrom", 0, ua.VariantType.Int64)
    BL403_Beer_PV = AssetBottleLine403.add_variable(addspace, "Beer_PV", 0, ua.VariantType.Double)
    BL403_Bottle_PV = AssetBottleLine403.add_variable(addspace, "Bottle_PV", 0, ua.VariantType.Int64)
    BL403_Bottle_SP = AssetBottleLine403.add_variable(addspace, "Bottle_SP", 0, ua.VariantType.Int64)
    BL403_Cons_Beer_FromLot = AssetBottleLine403.add_variable(addspace, "Cons_Beer_FromLot", 0, ua.VariantType.String)
    BL403_Cons_Beer_Item = AssetBottleLine403.add_variable(addspace, "Cons_Beer_Item", 0, ua.VariantType.String)
    BL403_Cons_Bottle_FromLot = AssetBottleLine403.add_variable(addspace, "Cons_Bottle_FromLot", 0, ua.VariantType.String)
    BL403_Cons_Bottle_Item = AssetBottleLine403.add_variable(addspace, "Cons_Bottle_Item", 0, ua.VariantType.String)
    BL403_Cons_Cap_FromLot = AssetBottleLine403.add_variable(addspace, "Cons_Cap_FromLot", 0, ua.VariantType.String)
    BL403_Cons_Cap_Item = AssetBottleLine403.add_variable(addspace, "Cons_Cap_Item", 0, ua.VariantType.String)
    BL403_Cons_Label_FromLot = AssetBottleLine403.add_variable(addspace, "Cons_Label_FromLot", 0, ua.VariantType.String)
    BL403_Cons_Label_Item = AssetBottleLine403.add_variable(addspace, "Cons_Label_Item", 0, ua.VariantType.String)
    BL403_Level_PV = AssetBottleLine403.add_variable(addspace, "Level_PV", 0, ua.VariantType.Double)
    BL403_MaterialID = AssetBottleLine403.add_variable(addspace, "MaterialID", 0, ua.VariantType.String)
    BL403_Prod_BottledBeer_Item = AssetBottleLine403.add_variable(addspace, "Prod_BottledBeer_Item", 0, ua.VariantType.String)
    BL403_Prod_BottledBeer_ToLot = AssetBottleLine403.add_variable(addspace, "Prod_BottledBeer_ToLot", 0, ua.VariantType.String)
    BL403_ProductionID = AssetBottleLine403.add_variable(addspace, "ProductionID", 0, ua.VariantType.String)
    BL403_Speed_PV = AssetBottleLine403.add_variable(addspace, "Speed_PV", 0, ua.VariantType.Double)
    BL403_Speed_SP = AssetBottleLine403.add_variable(addspace, "Speed_SP", 0, ua.VariantType.Int64)
    BL403_Temperature_PV = AssetBottleLine403.add_variable(addspace, "Temperature_PV", 0, ua.VariantType.Double)
    BL403_Temperature_SP = AssetBottleLine403.add_variable(addspace, "Temperature_SP", 0, ua.VariantType.Int64)
    BL403_HoldTime_PT = AssetBottleLine403.add_variable(addspace, "HoldTime_PT", 0, ua.VariantType.Int64)
    BL403_HoldTime_ET = AssetBottleLine403.add_variable(addspace, "HoldTime_ET", 0, ua.VariantType.Int64)
    BL403_State = AssetBottleLine403.add_variable(addspace, "State", 0, ua.VariantType.String)
    BL403_Status = AssetBottleLine403.add_variable(addspace, "Status", 0, ua.VariantType.String)        
    BL403_UtilizationState = AssetBottleLine403.add_variable(addspace, "UtilizationState", 0, ua.VariantType.String) 
    BL403_Utilization = AssetBottleLine403.add_variable(addspace, "Utilization", 0, ua.VariantType.String)        
    BL403_Scrap = AssetBottleLine403.add_variable(addspace, "Scrap", 0, ua.VariantType.Double)

    # Create instances of virtual physical assets (aka IoT SiteWise/TwinMaker digital twins)
    Roaster100 = Roaster("Roaster100")
    Roaster200 = Roaster("Roaster200")
    MaltMill100 = MaltMill("MaltMill100")
    MaltMill200 = MaltMill("MaltMill200")
    MashTun100 = Mash("MashTun100")
    MashTun200 = Mash("MashTun200")  
    BoilKettle100 = BoilKettle("BoilKettle100")  
    BoilKettle200 = BoilKettle("BoilKettle200")
    Fermenter100 = Fermenter("Fermenter100")
    Fermenter200 = Fermenter("Fermenter200")
    BrightTank301 = BrightTank("BrightTank301")
    BrightTank302 = BrightTank("BrightTank302")
    BrightTank303 = BrightTank("BrightTank303")
    BrightTank304 = BrightTank("BrightTank304")
    BrightTank305 = BrightTank("BrightTank305")
    BottleLine401 = BottleLine("BottleLine401")
    BottleLine402 = BottleLine("BottleLine402")
    BottleLine403 = BottleLine("BottleLine403")    

    # Local variables for asset integration
    assignmentMade = False    

    R100MatTransOS = False
    R200MatTransOS = False    

    FerShipToTime100 = Timer("FerShipToTime100")
    FerShipToTime200 = Timer("FerShipToTime200")

    FerShipToTime100.PT = 15 
    FerShipToTime200.PT = 15    

    # Start the OPC UA Server
    #server.start()    

    try:
        
        if(publishtositewise):
            t = threading.Thread(target=publish_to_sitewise_thread, args=())
            t.daemon = True
            t.start()
        
        while True:

            # Set assets to run            
            FerShipToTime100.Run()
            FerShipToTime200.Run()            

            ####################################################################
            # Start Brewing Train Asset Integration Control 
            ####################################################################

            ############################################################################################################################
            # Fermenter to Storage Control - Fermenter 100 & 200 will search for an available Bright Tank 301-305 and Transfer Material
            ############################################################################################################################            

            ###############################################################
            # Fermenter 100 - Search Bright Tank(s) 301-305 for availabilty 
            ###############################################################

            if (Fermenter100.NewState == NewStateEnum.Running) and (Fermenter100.HoldTime.DN) and (not Fermenter100.ShipToAllocated):
                Fermenter100.ShipToAutoAllocateCmd = True
            
            if (Fermenter100.ShipToAutoAllocateCmd):
                
                FerShipToTime100.Enabled = True
                FerShipToTime100.RST = False
                
                if (BrightTank301.NewState == NewStateEnum.Ready) and (BrightTank301.NewStatus == NewStatusEnum.Idle):
                    BrightTank301.NewStatus = NewStatusEnum.Allocated
                    Fermenter100.ShipToAutoAllocateCmd = False
                    Fermenter100.ShipToAllocated = True
                    Fermenter100.ShipTo_Tank = 301
                    BrightTank301.AllocatedFrom = 100                    
                elif (BrightTank302.NewState == NewStateEnum.Ready) and (BrightTank302.NewStatus == NewStatusEnum.Idle):
                    BrightTank302.NewStatus = NewStatusEnum.Allocated
                    Fermenter100.ShipToAutoAllocateCmd = False
                    Fermenter100.ShipToAllocated = True
                    Fermenter100.ShipTo_Tank = 302
                    BrightTank302.AllocatedFrom = 100                    
                elif (BrightTank303.NewState == NewStateEnum.Ready) and (BrightTank303.NewStatus == NewStatusEnum.Idle):
                    BrightTank303.NewStatus = NewStatusEnum.Allocated
                    Fermenter100.ShipToAutoAllocateCmd = False
                    Fermenter100.ShipToAllocated = True
                    Fermenter100.ShipTo_Tank = 303
                    BrightTank303.AllocatedFrom = 100                    
                elif (BrightTank304.NewState == NewStateEnum.Ready) and (BrightTank304.NewStatus == NewStatusEnum.Idle):
                    BrightTank304.NewStatus = NewStatusEnum.Allocated
                    Fermenter100.ShipToAutoAllocateCmd = False
                    Fermenter100.ShipToAllocated = True
                    Fermenter100.ShipTo_Tank = 304
                    BrightTank304.AllocatedFrom = 100                    
                elif (BrightTank305.NewState == NewStateEnum.Ready) and (BrightTank305.NewStatus == NewStatusEnum.Idle):
                    BrightTank305.NewStatus = NewStatusEnum.Allocated
                    Fermenter100.ShipToAutoAllocateCmd = False
                    Fermenter100.ShipToAllocated = True
                    Fermenter100.ShipTo_Tank = 305
                    BrightTank305.AllocatedFrom = 100                    

            if (Fermenter100.NewState == NewStateEnum.Running) and (Fermenter100.ShipToAllocated):
                
                if (FerShipToTime100.DN):
                    FerShipToTime100.Enabled = False
                    FerShipToTime100.RST = True
                    
                    Fermenter100.ShipToShipCmd = True

            if (Fermenter100.ShipToAllocated) and (Fermenter100.ShipToShipCmd):

                match Fermenter100.ShipTo_Tank:

                    case 301:
                        BrightTank301.StartCmd = True
                        BrightTank301.BeerShippedFromFermenter = Fermenter100.GreenBeerPV
                        BrightTank301.FermenterShipComplete = Fermenter100.ShipToShipComplete or (Fermenter100.NewState == NewStateEnum.Aborted and BrightTank301.NewStatus == NewStatusEnum.Filling)

                        BrightTank301.Next_ProductionID = Fermenter100.DownStream_ProductionID
                        BrightTank301.Next_ItemID = Fermenter100.DownStream_ItemID 
                        BrightTank301.Cons_GreenBeer_Item = Fermenter100.Prod_GreenBeer_Item
                        BrightTank301.Cons_GreenBeer_FromLot = Fermenter100.Prod_GreenBeer_ToLot

                        if (BrightTank301.FermenterShipComplete):
                            Fermenter100.ShipToShipCmd = False                            

                    case 302:
                        BrightTank302.StartCmd = True
                        BrightTank302.BeerShippedFromFermenter = Fermenter100.GreenBeerPV
                        BrightTank302.FermenterShipComplete = Fermenter100.ShipToShipComplete or (Fermenter100.NewState == NewStateEnum.Aborted and BrightTank302.NewStatus == NewStatusEnum.Filling)

                        BrightTank302.Next_ProductionID = Fermenter100.DownStream_ProductionID
                        BrightTank302.Next_ItemID = Fermenter100.DownStream_ItemID 
                        BrightTank302.Cons_GreenBeer_Item = Fermenter100.Prod_GreenBeer_Item
                        BrightTank302.Cons_GreenBeer_FromLot = Fermenter100.Prod_GreenBeer_ToLot

                        if (BrightTank302.FermenterShipComplete):
                            Fermenter100.ShipToShipCmd = False                            

                    case 303:
                        BrightTank303.StartCmd = True
                        BrightTank303.BeerShippedFromFermenter = Fermenter100.GreenBeerPV
                        BrightTank303.FermenterShipComplete = Fermenter100.ShipToShipComplete or (Fermenter100.NewState == NewStateEnum.Aborted and BrightTank303.NewStatus == NewStatusEnum.Filling)

                        BrightTank303.Next_ProductionID = Fermenter100.DownStream_ProductionID
                        BrightTank303.Next_ItemID = Fermenter100.DownStream_ItemID 
                        BrightTank303.Cons_GreenBeer_Item = Fermenter100.Prod_GreenBeer_Item
                        BrightTank303.Cons_GreenBeer_FromLot = Fermenter100.Prod_GreenBeer_ToLot

                        if (BrightTank303.FermenterShipComplete):
                            Fermenter100.ShipToShipCmd = False                            

                    case 304:
                        BrightTank304.StartCmd = True
                        BrightTank304.BeerShippedFromFermenter = Fermenter100.GreenBeerPV
                        BrightTank304.FermenterShipComplete = Fermenter100.ShipToShipComplete or (Fermenter100.NewState == NewStateEnum.Aborted and BrightTank304.NewStatus == NewStatusEnum.Filling)

                        BrightTank304.Next_ProductionID = Fermenter100.DownStream_ProductionID
                        BrightTank304.Next_ItemID = Fermenter100.DownStream_ItemID 
                        BrightTank304.Cons_GreenBeer_Item = Fermenter100.Prod_GreenBeer_Item
                        BrightTank304.Cons_GreenBeer_FromLot = Fermenter100.Prod_GreenBeer_ToLot

                        if (BrightTank304.FermenterShipComplete):
                            Fermenter100.ShipToShipCmd = False                            

                    case 305:
                        BrightTank305.StartCmd = True
                        BrightTank305.BeerShippedFromFermenter = Fermenter100.GreenBeerPV
                        BrightTank305.FermenterShipComplete = Fermenter100.ShipToShipComplete or (Fermenter100.NewState == NewStateEnum.Aborted and BrightTank305.NewStatus == NewStatusEnum.Filling)

                        BrightTank305.Next_ProductionID = Fermenter100.DownStream_ProductionID
                        BrightTank305.Next_ItemID = Fermenter100.DownStream_ItemID 
                        BrightTank305.Cons_GreenBeer_Item = Fermenter100.Prod_GreenBeer_Item
                        BrightTank305.Cons_GreenBeer_FromLot = Fermenter100.Prod_GreenBeer_ToLot

                        if (BrightTank305.FermenterShipComplete):
                            Fermenter100.ShipToShipCmd = False                            

            ###############################################################
            # Fermenter 200 - Search Bright Tank(s) 401-405 for availabilty 
            ###############################################################

            if (Fermenter200.NewState == NewStateEnum.Running) and (Fermenter200.HoldTime.DN) and (not Fermenter200.ShipToAllocated):
                Fermenter200.ShipToAutoAllocateCmd = True

            if (Fermenter200.ShipToAutoAllocateCmd):
                
                FerShipToTime200.Enabled = True
                FerShipToTime200.RST = False

                if (BrightTank301.NewState == NewStateEnum.Ready) and (BrightTank301.NewStatus == NewStatusEnum.Idle):
                    BrightTank301.NewStatus = NewStatusEnum.Allocated
                    Fermenter200.ShipToAutoAllocateCmd = False
                    Fermenter200.ShipToAllocated = True
                    Fermenter200.ShipTo_Tank = 301
                    BrightTank301.AllocatedFrom = 200                    
                elif (BrightTank302.NewState == NewStateEnum.Ready) and (BrightTank302.NewStatus == NewStatusEnum.Idle):
                    BrightTank302.NewStatus = NewStatusEnum.Allocated
                    Fermenter200.ShipToAutoAllocateCmd = False
                    Fermenter200.ShipToAllocated = True
                    Fermenter200.ShipTo_Tank = 302
                    BrightTank302.AllocatedFrom = 200                    
                elif (BrightTank303.NewState == NewStateEnum.Ready) and (BrightTank303.NewStatus == NewStatusEnum.Idle):
                    BrightTank303.NewStatus = NewStatusEnum.Allocated
                    Fermenter200.ShipToAutoAllocateCmd = False
                    Fermenter200.ShipToAllocated = True
                    Fermenter200.ShipTo_Tank = 303
                    BrightTank303.AllocatedFrom = 200                    
                elif (BrightTank304.NewState == NewStateEnum.Ready) and (BrightTank304.NewStatus == NewStatusEnum.Idle):
                    BrightTank304.NewStatus = NewStatusEnum.Allocated
                    Fermenter200.ShipToAutoAllocateCmd = False
                    Fermenter200.ShipToAllocated = True
                    Fermenter200.ShipTo_Tank = 304
                    BrightTank304.AllocatedFrom = 200                    
                elif (BrightTank305.NewState == NewStateEnum.Ready) and (BrightTank305.NewStatus == NewStatusEnum.Idle):
                    BrightTank305.NewStatus = NewStatusEnum.Allocated
                    Fermenter200.ShipToAutoAllocateCmd = False
                    Fermenter200.ShipToAllocated = True
                    Fermenter200.ShipTo_Tank = 305
                    BrightTank305.AllocatedFrom = 200             

            if (Fermenter200.NewState == NewStateEnum.Running) and (Fermenter200.ShipToAllocated):
                
                if (FerShipToTime200.DN):
                    FerShipToTime200.Enabled = False
                    FerShipToTime200.RST = True
                    
                    Fermenter200.ShipToShipCmd = True

            if (Fermenter200.ShipToAllocated) and (Fermenter200.ShipToShipCmd):

                match Fermenter200.ShipTo_Tank:

                    case 301:
                        BrightTank301.StartCmd = True
                        BrightTank301.BeerShippedFromFermenter = Fermenter200.GreenBeerPV
                        BrightTank301.FermenterShipComplete = Fermenter200.ShipToShipComplete or (Fermenter200.NewState == NewStateEnum.Aborted and BrightTank301.NewStatus == NewStatusEnum.Filling)

                        BrightTank301.Next_ProductionID = Fermenter200.DownStream_ProductionID
                        BrightTank301.Next_ItemID = Fermenter200.DownStream_ItemID 
                        BrightTank301.Cons_GreenBeer_Item = Fermenter200.Prod_GreenBeer_Item
                        BrightTank301.Cons_GreenBeer_FromLot = Fermenter200.Prod_GreenBeer_ToLot

                        if (BrightTank301.FermenterShipComplete):
                            Fermenter200.ShipToShipCmd = False                            

                    case 302:
                        BrightTank302.StartCmd = True
                        BrightTank302.BeerShippedFromFermenter = Fermenter200.GreenBeerPV
                        BrightTank302.FermenterShipComplete = Fermenter200.ShipToShipComplete or (Fermenter200.NewState == NewStateEnum.Aborted and BrightTank302.NewStatus == NewStatusEnum.Filling)

                        BrightTank302.Next_ProductionID = Fermenter200.DownStream_ProductionID
                        BrightTank302.Next_ItemID = Fermenter200.DownStream_ItemID 
                        BrightTank302.Cons_GreenBeer_Item = Fermenter200.Prod_GreenBeer_Item
                        BrightTank302.Cons_GreenBeer_FromLot = Fermenter200.Prod_GreenBeer_ToLot

                        if (BrightTank302.FermenterShipComplete):
                            Fermenter200.ShipToShipCmd = False                            

                    case 303:
                        BrightTank303.StartCmd = True
                        BrightTank303.BeerShippedFromFermenter = Fermenter200.GreenBeerPV
                        BrightTank303.FermenterShipComplete = Fermenter200.ShipToShipComplete or (Fermenter200.NewState == NewStateEnum.Aborted and BrightTank303.NewStatus == NewStatusEnum.Filling)

                        BrightTank303.Next_ProductionID = Fermenter200.DownStream_ProductionID
                        BrightTank303.Next_ItemID = Fermenter200.DownStream_ItemID 
                        BrightTank303.Cons_GreenBeer_Item = Fermenter200.Prod_GreenBeer_Item
                        BrightTank303.Cons_GreenBeer_FromLot = Fermenter200.Prod_GreenBeer_ToLot

                        if (BrightTank303.FermenterShipComplete):
                            Fermenter200.ShipToShipCmd = False                            

                    case 304:
                        BrightTank304.StartCmd = True
                        BrightTank304.BeerShippedFromFermenter = Fermenter200.GreenBeerPV
                        BrightTank304.FermenterShipComplete = Fermenter200.ShipToShipComplete or (Fermenter200.NewState == NewStateEnum.Aborted and BrightTank304.NewStatus == NewStatusEnum.Filling)

                        BrightTank304.Next_ProductionID = Fermenter200.DownStream_ProductionID
                        BrightTank304.Next_ItemID = Fermenter200.DownStream_ItemID 
                        BrightTank304.Cons_GreenBeer_Item = Fermenter200.Prod_GreenBeer_Item
                        BrightTank304.Cons_GreenBeer_FromLot = Fermenter200.Prod_GreenBeer_ToLot

                        if (BrightTank304.FermenterShipComplete):
                            Fermenter200.ShipToShipCmd = False                            

                    case 305:
                        BrightTank305.StartCmd = True
                        BrightTank305.BeerShippedFromFermenter = Fermenter200.GreenBeerPV
                        BrightTank305.FermenterShipComplete = Fermenter200.ShipToShipComplete or (Fermenter200.NewState == NewStateEnum.Aborted and BrightTank305.NewStatus == NewStatusEnum.Filling)

                        BrightTank305.Next_ProductionID = Fermenter200.DownStream_ProductionID
                        BrightTank305.Next_ItemID = Fermenter200.DownStream_ItemID 
                        BrightTank305.Cons_GreenBeer_Item = Fermenter200.Prod_GreenBeer_Item
                        BrightTank305.Cons_GreenBeer_FromLot = Fermenter200.Prod_GreenBeer_ToLot

                        if (BrightTank305.FermenterShipComplete):
                            Fermenter200.ShipToShipCmd = False                            

            ########################################################################################################################################
            # Bright Tanks to Bottling Lines Control - Bright Tanks 301-305 will search for an available BottlingLines 401/402 and Transfer Material
            ########################################################################################################################################

            if (BrightTank301.NewState == NewStateEnum.Running) and (BrightTank301.HoldTime.DN) and (not BrightTank301.ShipToAllocated):                
                BrightTank301.ShipToAutoAllocateCmd = True                    

            if (BrightTank302.NewState == NewStateEnum.Running) and (BrightTank302.HoldTime.DN) and (not BrightTank302.ShipToAllocated):                
                BrightTank302.ShipToAutoAllocateCmd = True                    

            if (BrightTank303.NewState == NewStateEnum.Running) and (BrightTank303.HoldTime.DN) and (not BrightTank303.ShipToAllocated):                
                BrightTank303.ShipToAutoAllocateCmd = True                    

            if (BrightTank304.NewState == NewStateEnum.Running) and (BrightTank304.HoldTime.DN) and (not BrightTank304.ShipToAllocated):                
                BrightTank304.ShipToAutoAllocateCmd = True                    

            if (BrightTank305.NewState == NewStateEnum.Running) and (BrightTank305.HoldTime.DN) and (not BrightTank305.ShipToAllocated):                
                BrightTank305.ShipToAutoAllocateCmd = True                             

            assignmentMade = False             

            if (BrightTank301.ShipToAutoAllocateCmd):                

                if (BottleLine401.NewState == NewStateEnum.Ready) and (BottleLine401.NewStatus == NewStatusEnum.Idle):
                    BottleLine401.NewStatus = NewStatusEnum.Allocated
                    BrightTank301.ShipToTank = 401
                    BrightTank301.ShipToAllocated = True
                    BrightTank301.ShipToAutoAllocateCmd = False                    
                    BottleLine401.AllocatedFrom = 301                                        
                    assignmentMade = True
                elif (BottleLine402.NewState == NewStateEnum.Ready) and (BottleLine402.NewStatus == NewStatusEnum.Idle):
                    BottleLine402.NewStatus = NewStatusEnum.Allocated
                    BrightTank301.ShipToTank = 402
                    BrightTank301.ShipToAllocated = True
                    BrightTank301.ShipToAutoAllocateCmd = False                    
                    BottleLine402.AllocatedFrom = 301                                        
                    assignmentMade = True
                elif (BottleLine403.NewState == NewStateEnum.Ready) and (BottleLine403.NewStatus == NewStatusEnum.Idle):
                    BottleLine403.NewStatus = NewStatusEnum.Allocated
                    BrightTank301.ShipToTank = 403
                    BrightTank301.ShipToAllocated = True
                    BrightTank301.ShipToAutoAllocateCmd = False                    
                    BottleLine403.AllocatedFrom = 301                                        
                    assignmentMade = True
                else:
                    BrightTank301.ShipToAllocated = False
                    BrightTank301.ShipToTank = -1

            if (BrightTank302.ShipToAutoAllocateCmd):                

                if (BottleLine401.NewState == NewStateEnum.Ready) and (BottleLine401.NewStatus == NewStatusEnum.Idle):
                    BottleLine401.NewStatus = NewStatusEnum.Allocated
                    BrightTank302.ShipToTank = 401
                    BrightTank302.ShipToAllocated = True
                    BrightTank302.ShipToAutoAllocateCmd = False                    
                    BottleLine401.AllocatedFrom = 302                                        
                    assignmentMade = True
                elif (BottleLine402.NewState == NewStateEnum.Ready) and (BottleLine402.NewStatus == NewStatusEnum.Idle):
                    BottleLine402.NewStatus = NewStatusEnum.Allocated
                    BrightTank302.ShipToTank = 402
                    BrightTank302.ShipToAllocated = True
                    BrightTank302.ShipToAutoAllocateCmd = False                    
                    BottleLine402.AllocatedFrom = 302                                        
                    assignmentMade = True
                elif (BottleLine403.NewState == NewStateEnum.Ready) and (BottleLine403.NewStatus == NewStatusEnum.Idle):
                    BottleLine403.NewStatus = NewStatusEnum.Allocated
                    BrightTank302.ShipToTank = 403
                    BrightTank302.ShipToAllocated = True
                    BrightTank302.ShipToAutoAllocateCmd = False                    
                    BottleLine403.AllocatedFrom = 302                                        
                    assignmentMade = True
                else:
                    BrightTank302.ShipToAllocated = False
                    BrightTank302.ShipToTank = -1

            if (BrightTank303.ShipToAutoAllocateCmd):                

                if (BottleLine401.NewState == NewStateEnum.Ready) and (BottleLine401.NewStatus == NewStatusEnum.Idle):
                    BottleLine401.NewStatus = NewStatusEnum.Allocated
                    BrightTank303.ShipToTank = 401
                    BrightTank303.ShipToAllocated = True
                    BrightTank303.ShipToAutoAllocateCmd = False                    
                    BottleLine401.AllocatedFrom = 303                                        
                    assignmentMade = True
                elif (BottleLine402.NewState == NewStateEnum.Ready) and (BottleLine402.NewStatus == NewStatusEnum.Idle):
                    BottleLine402.NewStatus = NewStatusEnum.Allocated
                    BrightTank303.ShipToTank = 402
                    BrightTank303.ShipToAllocated = True
                    BrightTank303.ShipToAutoAllocateCmd = False                    
                    BottleLine402.AllocatedFrom = 303                                        
                    assignmentMade = True
                elif (BottleLine403.NewState == NewStateEnum.Ready) and (BottleLine403.NewStatus == NewStatusEnum.Idle):
                    BottleLine403.NewStatus = NewStatusEnum.Allocated
                    BrightTank303.ShipToTank = 403
                    BrightTank303.ShipToAllocated = True
                    BrightTank303.ShipToAutoAllocateCmd = False                    
                    BottleLine403.AllocatedFrom = 303                                        
                    assignmentMade = True
                else:
                    BrightTank303.ShipToAllocated = False
                    BrightTank303.ShipToTank = -1

            if (BrightTank304.ShipToAutoAllocateCmd):                

                if (BottleLine401.NewState == NewStateEnum.Ready) and (BottleLine401.NewStatus == NewStatusEnum.Idle):
                    BottleLine401.NewStatus = NewStatusEnum.Allocated
                    BrightTank304.ShipToTank = 401
                    BrightTank304.ShipToAllocated = True
                    BrightTank304.ShipToAutoAllocateCmd = False                    
                    BottleLine401.AllocatedFrom = 304                                        
                    assignmentMade = True
                elif (BottleLine402.NewState == NewStateEnum.Ready) and (BottleLine402.NewStatus == NewStatusEnum.Idle):
                    BottleLine402.NewStatus = NewStatusEnum.Allocated
                    BrightTank304.ShipToTank = 402
                    BrightTank304.ShipToAllocated = True
                    BrightTank304.ShipToAutoAllocateCmd = False                    
                    BottleLine402.AllocatedFrom = 304                                        
                    assignmentMade = True
                elif (BottleLine403.NewState == NewStateEnum.Ready) and (BottleLine403.NewStatus == NewStatusEnum.Idle):
                    BottleLine403.NewStatus = NewStatusEnum.Allocated
                    BrightTank304.ShipToTank = 403
                    BrightTank304.ShipToAllocated = True
                    BrightTank304.ShipToAutoAllocateCmd = False                    
                    BottleLine403.AllocatedFrom = 304                                        
                    assignmentMade = True
                else:
                    BrightTank304.ShipToAllocated = False
                    BrightTank304.ShipToTank = -1

            if (BrightTank305.ShipToAutoAllocateCmd):                

                if (BottleLine401.NewState == NewStateEnum.Ready) and (BottleLine401.NewStatus == NewStatusEnum.Idle):
                    BottleLine401.NewStatus = NewStatusEnum.Allocated
                    BrightTank305.ShipToTank = 401
                    BrightTank305.ShipToAllocated = True
                    BrightTank305.ShipToAutoAllocateCmd = False                    
                    BottleLine401.AllocatedFrom = 305                                        
                    assignmentMade = True
                elif (BottleLine402.NewState == NewStateEnum.Ready) and (BottleLine402.NewStatus == NewStatusEnum.Idle):
                    BottleLine402.NewStatus = NewStatusEnum.Allocated
                    BrightTank305.ShipToTank = 402
                    BrightTank305.ShipToAllocated = True
                    BrightTank305.ShipToAutoAllocateCmd = False                    
                    BottleLine402.AllocatedFrom = 305                                        
                    assignmentMade = True
                elif (BottleLine403.NewState == NewStateEnum.Ready) and (BottleLine403.NewStatus == NewStatusEnum.Idle):
                    BottleLine403.NewStatus = NewStatusEnum.Allocated
                    BrightTank305.ShipToTank = 403
                    BrightTank305.ShipToAllocated = True
                    BrightTank305.ShipToAutoAllocateCmd = False                    
                    BottleLine403.AllocatedFrom = 305                                        
                    assignmentMade = True
                else:
                    BrightTank305.ShipToAllocated = False
                    BrightTank305.ShipToTank = -1

            if (BrightTank301.NewState == NewStateEnum.Running) and (BrightTank301.ShipToAllocated):                      
                BrightTank301.ShipToShipCmd = True

            if (BrightTank302.NewState == NewStateEnum.Running) and (BrightTank302.ShipToAllocated):                                    
                BrightTank302.ShipToShipCmd = True

            if (BrightTank303.NewState == NewStateEnum.Running) and (BrightTank303.ShipToAllocated):                    
                BrightTank303.ShipToShipCmd = True

            if (BrightTank304.NewState == NewStateEnum.Running) and (BrightTank304.ShipToAllocated):                    
                BrightTank304.ShipToShipCmd = True

            if (BrightTank305.NewState == NewStateEnum.Running) and (BrightTank305.ShipToAllocated):                    
                BrightTank305.ShipToShipCmd = True

            if (BrightTank301.ShipToShipCmd):

                match BrightTank301.ShipToTank:

                    case 401:
                        BottleLine401.BeerShippedFromStorage = BrightTank301.BeerShipped
                        BottleLine401.StorageShipComplete = BrightTank301.ShipToShipComplete or (BrightTank301.NewState == NewStateEnum.Aborted and BottleLine401.NewStatus == NewStatusEnum.Filling)

                        BottleLine401.Next_ProductionID = BrightTank301.DownStream_ProductionID
                        BottleLine401.Next_ItemID = BrightTank301.DownStream_ItemID 
                        BottleLine401.Cons_Beer_Item = BrightTank301.Prod_Beer_Item
                        BottleLine401.Cons_Beer_FromLot = BrightTank301.Prod_Beer_ToLot

                        if (BrightTank301.NewState == NewStateEnum.Done) or (BrightTank301.NewState == NewStateEnum.Aborted):
                            BrightTank301.ShipToShipCmd = False
                            BottleLine401.StorageShipComplete = True                           

                    case 402:
                        BottleLine402.BeerShippedFromStorage = BrightTank301.BeerShipped
                        BottleLine402.StorageShipComplete = BrightTank301.ShipToShipComplete or (BrightTank301.NewState == NewStateEnum.Aborted and BottleLine402.NewStatus == NewStatusEnum.Filling)

                        BottleLine402.Next_ProductionID = BrightTank301.DownStream_ProductionID
                        BottleLine402.Next_ItemID = BrightTank301.DownStream_ItemID 
                        BottleLine402.Cons_Beer_Item = BrightTank301.Prod_Beer_Item
                        BottleLine402.Cons_Beer_FromLot = BrightTank301.Prod_Beer_ToLot

                        if (BrightTank301.NewState == NewStateEnum.Done) or (BrightTank301.NewState == NewStateEnum.Aborted):
                            BrightTank301.ShipToShipCmd = False
                            BottleLine402.StorageShipComplete = True 

                    case 403:
                        BottleLine403.BeerShippedFromStorage = BrightTank301.BeerShipped
                        BottleLine403.StorageShipComplete = BrightTank301.ShipToShipComplete or (BrightTank301.NewState == NewStateEnum.Aborted and BottleLine403.NewStatus == NewStatusEnum.Filling)

                        BottleLine403.Next_ProductionID = BrightTank301.DownStream_ProductionID
                        BottleLine403.Next_ItemID = BrightTank301.DownStream_ItemID 
                        BottleLine403.Cons_Beer_Item = BrightTank301.Prod_Beer_Item
                        BottleLine403.Cons_Beer_FromLot = BrightTank301.Prod_Beer_ToLot

                        if (BrightTank301.NewState == NewStateEnum.Done) or (BrightTank301.NewState == NewStateEnum.Aborted):
                            BrightTank301.ShipToShipCmd = False
                            BottleLine403.StorageShipComplete = True

            if (BrightTank302.ShipToShipCmd):

                match BrightTank302.ShipToTank:

                    case 401:
                        BottleLine401.BeerShippedFromStorage = BrightTank302.BeerShipped
                        BottleLine401.StorageShipComplete = BrightTank302.ShipToShipComplete or (BrightTank302.NewState == NewStateEnum.Aborted and BottleLine401.NewStatus == NewStatusEnum.Filling)

                        BottleLine401.Next_ProductionID = BrightTank302.DownStream_ProductionID
                        BottleLine401.Next_ItemID = BrightTank302.DownStream_ItemID 
                        BottleLine401.Cons_Beer_Item = BrightTank302.Prod_Beer_Item
                        BottleLine401.Cons_Beer_FromLot = BrightTank302.Prod_Beer_ToLot

                        if (BrightTank302.NewState == NewStateEnum.Done) or (BrightTank302.NewState == NewStateEnum.Aborted):
                            BrightTank302.ShipToShipCmd = False
                            BottleLine401.StorageShipComplete = True                            

                    case 402:
                        BottleLine402.BeerShippedFromStorage = BrightTank302.BeerShipped
                        BottleLine402.StorageShipComplete = BrightTank302.ShipToShipComplete or (BrightTank302.NewState == NewStateEnum.Aborted and BottleLine402.NewStatus == NewStatusEnum.Filling)

                        BottleLine402.Next_ProductionID = BrightTank302.DownStream_ProductionID
                        BottleLine402.Next_ItemID = BrightTank302.DownStream_ItemID 
                        BottleLine402.Cons_Beer_Item = BrightTank302.Prod_Beer_Item
                        BottleLine402.Cons_Beer_FromLot = BrightTank302.Prod_Beer_ToLot

                        if (BrightTank302.NewState == NewStateEnum.Done) or (BrightTank302.NewState == NewStateEnum.Aborted):
                            BrightTank302.ShipToShipCmd = False
                            BottleLine402.StorageShipComplete = True    

                    case 403:
                        BottleLine403.BeerShippedFromStorage = BrightTank302.BeerShipped
                        BottleLine403.StorageShipComplete = BrightTank302.ShipToShipComplete or (BrightTank302.NewState == NewStateEnum.Aborted and BottleLine403.NewStatus == NewStatusEnum.Filling)

                        BottleLine403.Next_ProductionID = BrightTank302.DownStream_ProductionID
                        BottleLine403.Next_ItemID = BrightTank302.DownStream_ItemID 
                        BottleLine403.Cons_Beer_Item = BrightTank302.Prod_Beer_Item
                        BottleLine403.Cons_Beer_FromLot = BrightTank302.Prod_Beer_ToLot

                        if (BrightTank302.NewState == NewStateEnum.Done) or (BrightTank302.NewState == NewStateEnum.Aborted):
                            BrightTank302.ShipToShipCmd = False
                            BottleLine403.StorageShipComplete = True

            if (BrightTank303.ShipToShipCmd):

                match BrightTank303.ShipToTank:

                    case 401:
                        BottleLine401.BeerShippedFromStorage = BrightTank303.BeerShipped
                        BottleLine401.StorageShipComplete = BrightTank303.ShipToShipComplete or (BrightTank303.NewState == NewStateEnum.Aborted and BottleLine401.NewStatus == NewStatusEnum.Filling)

                        BottleLine401.Next_ProductionID = BrightTank303.DownStream_ProductionID
                        BottleLine401.Next_ItemID = BrightTank303.DownStream_ItemID 
                        BottleLine401.Cons_Beer_Item = BrightTank303.Prod_Beer_Item
                        BottleLine401.Cons_Beer_FromLot = BrightTank303.Prod_Beer_ToLot

                        if (BrightTank303.NewState == NewStateEnum.Done) or (BrightTank303.NewState == NewStateEnum.Aborted):
                            BrightTank303.ShipToShipCmd = False
                            BottleLine401.StorageShipComplete = True                            

                    case 402:
                        BottleLine402.BeerShippedFromStorage = BrightTank303.BeerShipped
                        BottleLine402.StorageShipComplete = BrightTank303.ShipToShipComplete or (BrightTank303.NewState == NewStateEnum.Aborted and BottleLine402.NewStatus == NewStatusEnum.Filling)

                        BottleLine402.Next_ProductionID = BrightTank303.DownStream_ProductionID
                        BottleLine402.Next_ItemID = BrightTank303.DownStream_ItemID 
                        BottleLine402.Cons_Beer_Item = BrightTank303.Prod_Beer_Item
                        BottleLine402.Cons_Beer_FromLot = BrightTank303.Prod_Beer_ToLot

                        if (BrightTank303.NewState == NewStateEnum.Done) or (BrightTank303.NewState == NewStateEnum.Aborted):
                            BrightTank303.ShipToShipCmd = False
                            BottleLine402.StorageShipComplete = True  

                    case 403:
                        BottleLine403.BeerShippedFromStorage = BrightTank303.BeerShipped
                        BottleLine403.StorageShipComplete = BrightTank303.ShipToShipComplete or (BrightTank303.NewState == NewStateEnum.Aborted and BottleLine403.NewStatus == NewStatusEnum.Filling)

                        BottleLine403.Next_ProductionID = BrightTank303.DownStream_ProductionID
                        BottleLine403.Next_ItemID = BrightTank303.DownStream_ItemID 
                        BottleLine403.Cons_Beer_Item = BrightTank303.Prod_Beer_Item
                        BottleLine403.Cons_Beer_FromLot = BrightTank303.Prod_Beer_ToLot

                        if (BrightTank303.NewState == NewStateEnum.Done) or (BrightTank303.NewState == NewStateEnum.Aborted):
                            BrightTank303.ShipToShipCmd = False
                            BottleLine403.StorageShipComplete = True

            if (BrightTank304.ShipToShipCmd):

                match BrightTank304.ShipToTank:

                    case 401:
                        BottleLine401.BeerShippedFromStorage = BrightTank304.BeerShipped
                        BottleLine401.StorageShipComplete = BrightTank304.ShipToShipComplete or (BrightTank304.NewState == NewStateEnum.Aborted and BottleLine401.NewStatus == NewStatusEnum.Filling)

                        BottleLine401.Next_ProductionID = BrightTank304.DownStream_ProductionID
                        BottleLine401.Next_ItemID = BrightTank304.DownStream_ItemID 
                        BottleLine401.Cons_Beer_Item = BrightTank304.Prod_Beer_Item
                        BottleLine401.Cons_Beer_FromLot = BrightTank304.Prod_Beer_ToLot

                        if (BrightTank304.NewState == NewStateEnum.Done) or (BrightTank304.NewState == NewStateEnum.Aborted):
                            BrightTank304.ShipToShipCmd = False
                            BottleLine401.StorageShipComplete = True                            

                    case 402:
                        BottleLine402.BeerShippedFromStorage = BrightTank304.BeerShipped
                        BottleLine402.StorageShipComplete = BrightTank304.ShipToShipComplete or (BrightTank304.NewState == NewStateEnum.Aborted and BottleLine402.NewStatus == NewStatusEnum.Filling)

                        BottleLine402.Next_ProductionID = BrightTank304.DownStream_ProductionID
                        BottleLine402.Next_ItemID = BrightTank304.DownStream_ItemID 
                        BottleLine402.Cons_Beer_Item = BrightTank304.Prod_Beer_Item
                        BottleLine402.Cons_Beer_FromLot = BrightTank304.Prod_Beer_ToLot

                        if (BrightTank304.NewState == NewStateEnum.Done) or (BrightTank304.NewState == NewStateEnum.Aborted):
                            BrightTank304.ShipToShipCmd = False
                            BottleLine402.StorageShipComplete = True     

                    case 403:
                        BottleLine403.BeerShippedFromStorage = BrightTank304.BeerShipped
                        BottleLine403.StorageShipComplete = BrightTank304.ShipToShipComplete or (BrightTank304.NewState == NewStateEnum.Aborted and BottleLine403.NewStatus == NewStatusEnum.Filling)

                        BottleLine403.Next_ProductionID = BrightTank304.DownStream_ProductionID
                        BottleLine403.Next_ItemID = BrightTank304.DownStream_ItemID 
                        BottleLine403.Cons_Beer_Item = BrightTank304.Prod_Beer_Item
                        BottleLine403.Cons_Beer_FromLot = BrightTank304.Prod_Beer_ToLot

                        if (BrightTank304.NewState == NewStateEnum.Done) or (BrightTank304.NewState == NewStateEnum.Aborted):
                            BrightTank304.ShipToShipCmd = False
                            BottleLine403.StorageShipComplete = True

            if (BrightTank305.ShipToShipCmd):

                match BrightTank305.ShipToTank:

                    case 401:
                        BottleLine401.BeerShippedFromStorage = BrightTank305.BeerShipped
                        BottleLine401.StorageShipComplete = BrightTank305.ShipToShipComplete or (BrightTank305.NewState == NewStateEnum.Aborted and BottleLine401.NewStatus == NewStatusEnum.Filling)

                        BottleLine401.Next_ProductionID = BrightTank305.DownStream_ProductionID
                        BottleLine401.Next_ItemID = BrightTank305.DownStream_ItemID 
                        BottleLine401.Cons_Beer_Item = BrightTank305.Prod_Beer_Item
                        BottleLine401.Cons_Beer_FromLot = BrightTank305.Prod_Beer_ToLot

                        if (BrightTank305.NewState == NewStateEnum.Done) or (BrightTank305.NewState == NewStateEnum.Aborted):
                            BrightTank305.ShipToShipCmd = False
                            BottleLine401.StorageShipComplete = True                            

                    case 402:
                        BottleLine402.BeerShippedFromStorage = BrightTank305.BeerShipped
                        BottleLine402.StorageShipComplete = BrightTank305.ShipToShipComplete or (BrightTank305.NewState == NewStateEnum.Aborted and BottleLine402.NewStatus == NewStatusEnum.Filling)

                        BottleLine402.Next_ProductionID = BrightTank305.DownStream_ProductionID
                        BottleLine402.Next_ItemID = BrightTank305.DownStream_ItemID 
                        BottleLine402.Cons_Beer_Item = BrightTank305.Prod_Beer_Item
                        BottleLine402.Cons_Beer_FromLot = BrightTank305.Prod_Beer_ToLot

                        if (BrightTank305.NewState == NewStateEnum.Done) or (BrightTank305.NewState == NewStateEnum.Aborted):
                            BrightTank305.ShipToShipCmd = False
                            BottleLine402.StorageShipComplete = True

                    case 403:
                        BottleLine403.BeerShippedFromStorage = BrightTank305.BeerShipped
                        BottleLine403.StorageShipComplete = BrightTank305.ShipToShipComplete or (BrightTank305.NewState == NewStateEnum.Aborted and BottleLine403.NewStatus == NewStatusEnum.Filling)

                        BottleLine403.Next_ProductionID = BrightTank305.DownStream_ProductionID
                        BottleLine403.Next_ItemID = BrightTank305.DownStream_ItemID 
                        BottleLine403.Cons_Beer_Item = BrightTank305.Prod_Beer_Item
                        BottleLine403.Cons_Beer_FromLot = BrightTank305.Prod_Beer_ToLot

                        if (BrightTank305.NewState == NewStateEnum.Done) or (BrightTank305.NewState == NewStateEnum.Aborted):
                            BrightTank305.ShipToShipCmd = False
                            BottleLine403.StorageShipComplete = True

            #Update Roasters            
            Roaster100.Run()     
            Roaster200.Run()

            #######################################################
            # Brew Train 100 - Roaster->Mash->BoilKettle->Fermenter
            #######################################################

            # Transfer Roaster100 Produced Item/ToLot to MashTun100 Consume Item/From Lot
            if (Roaster100.NewStatus == NewStatusEnum.Filling):
                if (not R100MatTransOS):
                    R100MatTransOS = True
                    R100NewProdDict = {"SelectedProduct":Roaster100.SelectedProduct,
                                        "RoastedBarley_ToLot":Roaster100.Prod_RoastedBarley_ToLot,
                                        "RoastedBarley_Item":Roaster100.Prod_RoastedBarley_Item}

                    if (len(MashTun100.ConsList) <= 20):
                        MashTun100.ConsList.append(R100NewProdDict)
            else:
                R100MatTransOS = False

            MashTun100.NewState = MaltMill100.NewState
            MashTun100.Utilization = MaltMill100.Utilization
            MashTun100.UtilizationState = MaltMill100.UtilizationState
            MaltMill100.MaltSP = round(MashTun100.WaterSP * 0.2951328, 2)
            MaltMill100.MashTunComplete = MashTun100.MashComplete
            MashTun100.MaltMillComplete = MaltMill100.MaltMillComplete

            # Send ProductionID and MaterialID Information to Downstream Assets Mash100->BoilKettle100
            if (MashTun100.NewState == NewStateEnum.Running):
                BoilKettle100.Next_ProductionID = MashTun100.ProductionID
                BoilKettle100.Next_ItemID = MashTun100.Wort_Item

            # Send Produced Information to Downstream Assets Mash100->BoilKettle100 for Consumption
            if (MashTun100.NewStatus == NewStatusEnum.Draining):
                BoilKettle100.Cons_Wort_Item = MashTun100.Prod_Wort_Item
                BoilKettle100.Cons_Wort_FromLot = MashTun100.Prod_Wort_ToLot

            if (BoilKettle100.NewState == NewStateEnum.Ready):
                MashTun100.BrewKettleReady = True
            else:
                MashTun100.BrewKettleReady = False

            #Update MaltMill100 and MashTun100
            MashTun100.Run()
            MaltMill100.Run()             

            BoilKettle100.StartCmd = MashTun100.OutletPump.AuxContact            
            BoilKettle100.MashShipComplete = MashTun100.ShipComplete or (MashTun100.NewState == NewStateEnum.Aborted and BoilKettle100.NewStatus == NewStatusEnum.Filling) 

            if (MashTun100.NewStatus == NewStatusEnum.Draining) and (MashTun100.NewState == NewStateEnum.Running):
                BoilKettle100.WortPV = MashTun100.WortPV

            # Send ProductionID and MaterialID Information to Downstream Assets BoilKettle100->Fermenter100
            if (BoilKettle100.NewState == NewStateEnum.Running):
                Fermenter100.Next_ProductionID = BoilKettle100.DownStream_ProductionID
                Fermenter100.Next_ItemID = BoilKettle100.DownStream_ItemID

            # Send Produced Information to Downstream Assets BoilKettle100->Fermenter100 for Consumption
            if (BoilKettle100.NewStatus == NewStatusEnum.Draining):
                Fermenter100.Cons_BrewedWort_Item = BoilKettle100.Prod_BrewedWort_Item
                Fermenter100.Cons_BrewedWort_FromLot = BoilKettle100.Prod_BrewedWort_ToLot

            if (Fermenter100.NewState == NewStateEnum.Ready):
                BoilKettle100.FermenterReady = True
            else:
                BoilKettle100.FermenterReady = False                

            if (BoilKettle100.NewStatus == NewStatusEnum.Filling) and (MashTun100.NewStatus != NewStatusEnum.Draining):
                BoilKettle100.MashShipComplete = True

            # Update BoilKettle100
            BoilKettle100.Run()                 
            
            Fermenter100.StartCmd = BoilKettle100.OutletPump.AuxContact
            Fermenter100.BrewKettleShipComplete = BoilKettle100.ShipComplete or (BoilKettle100.NewState == NewStateEnum.Aborted and Fermenter100.NewStatus == NewStatusEnum.Filling)
    
            if (BoilKettle100.NewStatus == NewStatusEnum.Draining) and (BoilKettle100.NewState == NewStateEnum.Running):
                Fermenter100.BrewedWortPV = BoilKettle100.BrewedWortPV
              
            # Update Fermenter100   
            Fermenter100.Run()             

            #######################################################
            # Brew Train 200 - Roaster->Mash->BoilKettle->Fermenter
            #######################################################

            # Transfer Roaster200 Produced Item/ToLot to MashTun200 Consume Item/From Lot
            if (Roaster200.NewStatus == NewStatusEnum.Filling):
                if (not R200MatTransOS):
                    R200MatTransOS = True
                    R200NewProdDict = {"SelectedProduct":Roaster200.SelectedProduct,
                                        "RoastedBarley_ToLot":Roaster200.Prod_RoastedBarley_ToLot,
                                        "RoastedBarley_Item":Roaster200.Prod_RoastedBarley_Item}

                    if (len(MashTun200.ConsList) <= 20):
                        MashTun200.ConsList.append(R200NewProdDict)
            else:
                R200MatTransOS = False

            MashTun200.NewState = MaltMill200.NewState
            MashTun200.Utilization = MaltMill200.Utilization
            MashTun200.UtilizationState = MaltMill200.UtilizationState
            MaltMill200.MaltSP = round(MashTun200.WaterSP * 0.2951328, 2)
            MaltMill200.MashTunComplete = MashTun200.MashComplete
            MashTun200.MaltMillComplete = MaltMill200.MaltMillComplete

            # Send ProductionID and MaterialID Information to Downstream Assets Mash200->BoilKettle200 
            if (MashTun200.NewState == NewStateEnum.Running):
                BoilKettle200.Next_ProductionID = MashTun200.ProductionID
                BoilKettle200.Next_ItemID = MashTun200.Wort_Item

            # Send Produced Information to Downstream Assets Mash200->BoilKettle200 for Consumption
            if (MashTun200.NewStatus == NewStatusEnum.Draining):
                BoilKettle200.Cons_Wort_Item = MashTun200.Prod_Wort_Item
                BoilKettle200.Cons_Wort_FromLot = MashTun200.Prod_Wort_ToLot

            if (BoilKettle200.NewState == NewStateEnum.Ready):
                MashTun200.BrewKettleReady = True
            else:
                MashTun200.BrewKettleReady = False

            #Update MaltMill200 and MashTun200           
            MashTun200.Run()
            MaltMill200.Run()                  

            BoilKettle200.StartCmd = MashTun200.OutletPump.AuxContact
            BoilKettle200.MashShipComplete = MashTun200.ShipComplete or (MashTun200.NewState == NewStateEnum.Aborted and BoilKettle200.NewStatus == NewStatusEnum.Filling) 

            if (MashTun200.NewStatus == NewStatusEnum.Draining) and (MashTun200.NewState == NewStateEnum.Running):
                BoilKettle200.WortPV = MashTun200.WortPV 

            # Send ProductionID and MaterialID Information to Downstream Assets BoilKettle200->Fermenter200
            if (BoilKettle200.NewState == NewStateEnum.Running):
                Fermenter200.Next_ProductionID = BoilKettle200.DownStream_ProductionID
                Fermenter200.Next_ItemID = BoilKettle200.DownStream_ItemID

            # Send Produced Information to Downstream Assets BoilKettle200->Fermenter200 for Consumption
            if (BoilKettle200.NewStatus == NewStatusEnum.Draining):
                Fermenter200.Cons_BrewedWort_Item = BoilKettle200.Prod_BrewedWort_Item
                Fermenter200.Cons_BrewedWort_FromLot = BoilKettle200.Prod_BrewedWort_ToLot

            if (Fermenter200.NewState == NewStateEnum.Ready):
                BoilKettle200.FermenterReady = True
            else:
                BoilKettle200.FermenterReady = False 

            if (BoilKettle200.NewStatus == NewStatusEnum.Filling) and (MashTun200.NewStatus != NewStatusEnum.Draining):
                BoilKettle200.MashShipComplete = True     

            # Update BoilKettle200
            BoilKettle200.Run()

            Fermenter200.StartCmd = BoilKettle200.OutletPump.AuxContact
            Fermenter200.BrewKettleShipComplete = BoilKettle200.ShipComplete or (BoilKettle200.NewState == NewStateEnum.Aborted and Fermenter200.NewStatus == NewStatusEnum.Filling)
    
            if (BoilKettle200.NewStatus == NewStatusEnum.Draining) and (BoilKettle200.NewState == NewStateEnum.Running):
                Fermenter200.BrewedWortPV = BoilKettle200.BrewedWortPV

            # Update Fermenter200   
            Fermenter200.Run()

            # Update Bright Tanks
            BrightTank301.Run()
            BrightTank302.Run()
            BrightTank303.Run()
            BrightTank304.Run()
            BrightTank305.Run()

            #Update Bottling Lines
            BottleLine401.Run()
            BottleLine402.Run()
            BottleLine403.Run()
            
            #######################################################################
            # Map asset runtime values to OPC Data Items for OPC Client Consumption
            #######################################################################

            # Roaster100
            R100_Malt_PV.set_value(Roaster100.MaltPV)
            R100_Malt_SP.set_value(Roaster100.MaltSP) 
            R100_Temperature_PV.set_value(Roaster100.TemperaturePV) 
            R100_Temperature_SP.set_value(Roaster100.TemperatureSP)
            R100_HoldTime_PT.set_value(Roaster100.HoldTime.PT)  
            R100_HoldTime_ET.set_value(Roaster100.HoldTime.ET) 
            R100_State.set_value(Roaster100.NewState)
            R100_Status.set_value(Roaster100.NewStatus)  
            R100_MaterialID.set_value(Roaster100.MaterialID)    
            R100_ProductionID.set_value(Roaster100.ProductionID)
            R100_Cons_RawBarley_Item.set_value(Roaster100.Cons_RawBarley_Item)
            R100_Cons_RawBarley_FromLot.set_value(Roaster100.Cons_RawBarley_FromLot)
            R100_Prod_RoastedBarley_ToLot.set_value(Roaster100.Prod_RoastedBarley_ToLot)
            R100_Prod_RoastedBarley_Item.set_value(Roaster100.Prod_RoastedBarley_Item)
            R100_UtilizationState.set_value(Roaster100.UtilizationState)
            R100_Utilization.set_value(Roaster100.Utilization)
            R100_MaltAuger_PV.set_value(Roaster100.MaltAuger.PV)
            R100_MaltAuger_AuxContact.set_value(Roaster100.MaltAuger.AuxContact)
            R100_Scrap.set_value(Roaster100.Scrap)

            # Roaster200
            R200_Malt_PV.set_value(Roaster200.MaltPV)
            R200_Malt_SP.set_value(Roaster200.MaltSP) 
            R200_Temperature_PV.set_value(Roaster200.TemperaturePV) 
            R200_Temperature_SP.set_value(Roaster200.TemperatureSP)
            R200_HoldTime_PT.set_value(Roaster200.HoldTime.PT)  
            R200_HoldTime_ET.set_value(Roaster200.HoldTime.ET) 
            R200_State.set_value(Roaster200.NewState)
            R200_Status.set_value(Roaster200.NewStatus)  
            R200_MaterialID.set_value(Roaster200.MaterialID)       
            R200_ProductionID.set_value(Roaster200.ProductionID)    
            R200_Cons_RawBarley_Item.set_value(Roaster200.Cons_RawBarley_Item)  
            R200_Cons_RawBarley_FromLot.set_value(Roaster200.Cons_RawBarley_FromLot) 
            R200_Prod_RoastedBarley_ToLot.set_value(Roaster200.Prod_RoastedBarley_ToLot) 
            R200_Prod_RoastedBarley_Item.set_value(Roaster200.Prod_RoastedBarley_Item) 
            R200_UtilizationState.set_value(Roaster200.UtilizationState)
            R200_Utilization.set_value(Roaster200.Utilization)   
            R200_MaltAuger_PV.set_value(Roaster200.MaltAuger.PV)  
            R200_MaltAuger_AuxContact.set_value(Roaster100.MaltAuger.AuxContact)   
            R200_Scrap.set_value(Roaster200.Scrap)     

            # MaltMill100   
            MM100_Malt_PV.set_value(MaltMill100.MaltPV)
            MM100_Malt_SP.set_value(MaltMill100.MaltSP)
            MM100_MaltAuger_AuxContact.set_value(MaltMill100.MaltAuger.AuxContact)
            MM100_MaltAuger_PV.set_value(MaltMill100.MaltAuger.PV)
            MM100_MaltMill_AuxContact.set_value(MaltMill100.MaltMill.AuxContact)
            MM100_MaltMill_PV.set_value(MaltMill100.MaltMill.PV)
            MM100_State.set_value(MaltMill100.NewState)

            # Mash100             
            M100_Agitator_AuxContact.set_value(MashTun100.Agitator.AuxContact)
            M100_Agitator_PV.set_value(MashTun100.Agitator.PV)
            M100_Cons_Malt_FromLot.set_value(MashTun100.Cons_Malt_FromLot)
            M100_Cons_Malt_Item.set_value(MashTun100.Cons_Malt_Item)
            M100_HoldTime_PT.set_value(MashTun100.HoldTime.PT)
            M100_HoldTime_ET.set_value(MashTun100.HoldTime.ET)
            M100_Level_PV.set_value(MashTun100.LevelPV)
            M100_MaterialID.set_value(MashTun100.MaterialID)
            M100_State.set_value(MashTun100.NewState)
            M100_Status.set_value(MashTun100.NewStatus)
            M100_OutletPump_AuxContact.set_value(MashTun100.OutletPump.AuxContact)
            M100_OutletPump_PV.set_value(MashTun100.OutletPump.PV)
            M100_OutletValve_CLS.set_value(MashTun100.OutletValve.CLS)
            M100_OutletValve_OLS.set_value(MashTun100.OutletValve.OLS)
            M100_OutletValve_PV.set_value(MashTun100.OutletValve.PV)
            M100_Prod_Wort_Item.set_value(MashTun100.Prod_Wort_Item)
            M100_Prod_Wort_ToLot.set_value(MashTun100.Prod_Wort_ToLot)
            M100_ProductionID.set_value(MashTun100.ProductionID)
            M100_Scrap.set_value(MashTun100.Scrap)
            M100_Scrap_ToLot.set_value(MashTun100.Scrap_ToLot)
            M100_ShipComplete.set_value(MashTun100.ShipComplete)
            M100_SoakTempSP1.set_value(MashTun100.SoakTempSP1)
            M100_SoakTempSP2.set_value(MashTun100.SoakTempSP2)
            M100_SoakTimeSP1.set_value(MashTun100.SoakTimeSP1)
            M100_SoakTimeSP2.set_value(MashTun100.SoakTimeSP2)
            M100_SteamValve_CLS.set_value(MashTun100.SteamValve.CLS)
            M100_SteamValve_OLS.set_value(MashTun100.SteamValve.OLS)
            M100_SteamValve_PV.set_value(MashTun100.SteamValve.PV)
            M100_Temperature_PV.set_value(MashTun100.TemperaturePV)
            M100_Temperature_SP.set_value(MashTun100.TemperatureSP)
            M100_UtilizationState.set_value(MashTun100.UtilizationState)
            M100_Utilization.set_value(MashTun100.Utilization)
            M100_Water_PV.set_value(MashTun100.WaterPV)
            M100_Water_SP.set_value(MashTun100.WaterSP)
            M100_WaterValve_CLS.set_value(MashTun100.WaterValve.CLS)
            M100_WaterValve_OLS.set_value(MashTun100.WaterValve.OLS)
            M100_WaterValve_PV.set_value(MashTun100.WaterValve.PV)
            M100_Wort_Item.set_value(MashTun100.Wort_Item)
            M100_Wort_PV.set_value(MashTun100.WortPV)

            # MaltMill200   
            MM200_Malt_PV.set_value(MaltMill200.MaltPV)
            MM200_Malt_SP.set_value(MaltMill200.MaltSP)
            MM200_MaltAuger_AuxContact.set_value(MaltMill200.MaltAuger.AuxContact)
            MM200_MaltAuger_PV.set_value(MaltMill200.MaltAuger.PV)
            MM200_MaltMill_AuxContact.set_value(MaltMill200.MaltMill.AuxContact)
            MM200_MaltMill_PV.set_value(MaltMill200.MaltMill.PV)
            MM200_State.set_value(MaltMill200.NewState)     

            # Mash200             
            M200_Agitator_AuxContact.set_value(MashTun200.Agitator.AuxContact)
            M200_Agitator_PV.set_value(MashTun200.Agitator.PV)
            M200_Cons_Malt_FromLot.set_value(MashTun200.Cons_Malt_FromLot)
            M200_Cons_Malt_Item.set_value(MashTun200.Cons_Malt_Item)
            M200_HoldTime_PT.set_value(MashTun200.HoldTime.PT)
            M200_HoldTime_ET.set_value(MashTun200.HoldTime.ET)
            M200_Level_PV.set_value(MashTun200.LevelPV)
            M200_MaterialID.set_value(MashTun200.MaterialID)
            M200_State.set_value(MashTun200.NewState)
            M200_Status.set_value(MashTun200.NewStatus)
            M200_OutletPump_AuxContact.set_value(MashTun200.OutletPump.AuxContact)
            M200_OutletPump_PV.set_value(MashTun200.OutletPump.PV)
            M200_OutletValve_CLS.set_value(MashTun200.OutletValve.CLS)
            M200_OutletValve_OLS.set_value(MashTun200.OutletValve.OLS)
            M200_OutletValve_PV.set_value(MashTun200.OutletValve.PV)
            M200_Prod_Wort_Item.set_value(MashTun200.Prod_Wort_Item)
            M200_Prod_Wort_ToLot.set_value(MashTun200.Prod_Wort_ToLot)
            M200_ProductionID.set_value(MashTun200.ProductionID)
            M200_Scrap.set_value(MashTun200.Scrap)
            M200_Scrap_ToLot.set_value(MashTun200.Scrap_ToLot)
            M200_ShipComplete.set_value(MashTun200.ShipComplete)
            M200_SoakTempSP1.set_value(MashTun200.SoakTempSP1)
            M200_SoakTempSP2.set_value(MashTun200.SoakTempSP2)
            M200_SoakTimeSP1.set_value(MashTun200.SoakTimeSP1)
            M200_SoakTimeSP2.set_value(MashTun200.SoakTimeSP2)
            M200_SteamValve_CLS.set_value(MashTun200.SteamValve.CLS)
            M200_SteamValve_OLS.set_value(MashTun200.SteamValve.OLS)
            M200_SteamValve_PV.set_value(MashTun200.SteamValve.PV)
            M200_Temperature_PV.set_value(MashTun200.TemperaturePV)
            M200_Temperature_SP.set_value(MashTun200.TemperatureSP)
            M200_UtilizationState.set_value(MashTun200.UtilizationState)
            M200_Utilization.set_value(MashTun200.Utilization)
            M200_Water_PV.set_value(MashTun200.WaterPV)
            M200_Water_SP.set_value(MashTun200.WaterSP)
            M200_WaterValve_CLS.set_value(MashTun200.WaterValve.CLS)
            M200_WaterValve_OLS.set_value(MashTun200.WaterValve.OLS)
            M200_WaterValve_PV.set_value(MashTun200.WaterValve.PV)
            M200_Wort_Item.set_value(MashTun200.Wort_Item)
            M200_Wort_PV.set_value(MashTun200.WortPV)     
            
            # BoilKettle100            
            BK100_Cons_Hops_FromLot.set_value(BoilKettle100.Cons_Hops_FromLot) 
            BK100_Cons_Hops_Item.set_value(BoilKettle100.Cons_Hops_Item)           
            BK100_Cons_Wort_FromLot.set_value(BoilKettle100.Cons_Wort_FromLot)
            BK100_Cons_Wort_Item.set_value(BoilKettle100.Cons_Wort_Item)
            BK100_HoldTime_PT.set_value(BoilKettle100.HoldTime.PT)
            BK100_HoldTime_ET.set_value(BoilKettle100.HoldTime.ET)
            BK100_Level_PV.set_value(BoilKettle100.LevelPV)
            BK100_MaterialID.set_value(BoilKettle100.MaterialID)
            BK100_State.set_value(BoilKettle100.NewState)
            BK100_Status.set_value(BoilKettle100.NewStatus)
            BK100_OutletPump_AuxContact.set_value(BoilKettle100.OutletPump.AuxContact)
            BK100_OutletPump_PV.set_value(BoilKettle100.OutletPump.PV)
            BK100_InletValve_CLS.set_value(BoilKettle100.InletValve.CLS)
            BK100_InletValve_OLS.set_value(BoilKettle100.InletValve.OLS)
            BK100_InletValve_PV.set_value(BoilKettle100.InletValve.PV)
            BK100_OutletValve_CLS.set_value(BoilKettle100.OutletValve.CLS)
            BK100_OutletValve_OLS.set_value(BoilKettle100.OutletValve.OLS)
            BK100_OutletValve_PV.set_value(BoilKettle100.OutletValve.PV)
            BK100_Prod_BrewedWort_Item.set_value(BoilKettle100.Prod_BrewedWort_Item)
            BK100_Prod_BrewedWort_ToLot.set_value(BoilKettle100.Prod_BrewedWort_ToLot)
            BK100_ProductionID.set_value(BoilKettle100.ProductionID)
            BK100_Scrap.set_value(BoilKettle100.Scrap)
            BK100_SteamValve_CLS.set_value(BoilKettle100.SteamValve.CLS)
            BK100_SteamValve_OLS.set_value(BoilKettle100.SteamValve.OLS)
            BK100_SteamValve_PV.set_value(BoilKettle100.SteamValve.PV)
            BK100_Temperature_PV.set_value(BoilKettle100.TemperaturePV)
            BK100_Temperature_SP.set_value(BoilKettle100.TemperatureSP)
            BK100_UtilizationState.set_value(BoilKettle100.UtilizationState)
            BK100_Utilization.set_value(BoilKettle100.Utilization)
            BK100_HopsAuger_AuxContact.set_value(BoilKettle100.HopsAuger.AuxContact)
            BK100_HopsAuger_PV.set_value(BoilKettle100.HopsAuger.PV)
            BK100_Wort_PV.set_value(BoilKettle100.WortPV)
            BK100_Hops_PV.set_value(BoilKettle100.HopsPV)
            BK100_Hops_SP.set_value(BoilKettle100.HopsSP)
            BK100_BrewedWort_PV.set_value(BoilKettle100.BrewedWortPV)  

            # BoilKettle200            
            BK200_Cons_Hops_FromLot.set_value(BoilKettle200.Cons_Hops_FromLot) 
            BK200_Cons_Hops_Item.set_value(BoilKettle200.Cons_Hops_Item)           
            BK200_Cons_Wort_FromLot.set_value(BoilKettle200.Cons_Wort_FromLot)
            BK200_Cons_Wort_Item.set_value(BoilKettle200.Cons_Wort_Item)
            BK200_HoldTime_PT.set_value(BoilKettle200.HoldTime.PT)
            BK200_HoldTime_ET.set_value(BoilKettle200.HoldTime.ET)
            BK200_Level_PV.set_value(BoilKettle200.LevelPV)
            BK200_MaterialID.set_value(BoilKettle200.MaterialID)
            BK200_State.set_value(BoilKettle200.NewState)
            BK200_Status.set_value(BoilKettle200.NewStatus)
            BK200_OutletPump_AuxContact.set_value(BoilKettle200.OutletPump.AuxContact)
            BK200_OutletPump_PV.set_value(BoilKettle200.OutletPump.PV)
            BK200_InletValve_CLS.set_value(BoilKettle200.InletValve.CLS)
            BK200_InletValve_OLS.set_value(BoilKettle200.InletValve.OLS)
            BK200_InletValve_PV.set_value(BoilKettle200.InletValve.PV)
            BK200_OutletValve_CLS.set_value(BoilKettle200.OutletValve.CLS)
            BK200_OutletValve_OLS.set_value(BoilKettle200.OutletValve.OLS)
            BK200_OutletValve_PV.set_value(BoilKettle200.OutletValve.PV)
            BK200_Prod_BrewedWort_Item.set_value(BoilKettle200.Prod_BrewedWort_Item)
            BK200_Prod_BrewedWort_ToLot.set_value(BoilKettle200.Prod_BrewedWort_ToLot)
            BK200_ProductionID.set_value(BoilKettle200.ProductionID)
            BK200_Scrap.set_value(BoilKettle200.Scrap)
            BK200_SteamValve_CLS.set_value(BoilKettle200.SteamValve.CLS)
            BK200_SteamValve_OLS.set_value(BoilKettle200.SteamValve.OLS)
            BK200_SteamValve_PV.set_value(BoilKettle200.SteamValve.PV)
            BK200_Temperature_PV.set_value(BoilKettle200.TemperaturePV)
            BK200_Temperature_SP.set_value(BoilKettle200.TemperatureSP)
            BK200_UtilizationState.set_value(BoilKettle200.UtilizationState)
            BK200_Utilization.set_value(BoilKettle200.Utilization)
            BK200_HopsAuger_AuxContact.set_value(BoilKettle200.HopsAuger.AuxContact)
            BK200_HopsAuger_PV.set_value(BoilKettle200.HopsAuger.PV)
            BK200_Wort_PV.set_value(BoilKettle200.WortPV)
            BK200_Hops_PV.set_value(BoilKettle200.HopsPV)
            BK200_Hops_SP.set_value(BoilKettle200.HopsSP)
            BK200_BrewedWort_PV.set_value(BoilKettle200.BrewedWortPV)

            # Fermenter100
            F100_ChillWaterValve_CLS.set_value(Fermenter100.ChillWaterValve.CLS)
            F100_ChillWaterValve_OLS.set_value(Fermenter100.ChillWaterValve.OLS)
            F100_ChillWaterValve_PV.set_value(Fermenter100.ChillWaterValve.PV)
            F100_Cons_BrewedWort_FromLot.set_value(Fermenter100.Cons_BrewedWort_FromLot)  
            F100_Cons_BrewedWort_Item.set_value(Fermenter100.Cons_BrewedWort_Item)
            F100_Cons_Yeast_FromLot.set_value(Fermenter100.Cons_Yeast_FromLot)
            F100_Cons_Yeast_Item.set_value(Fermenter100.Cons_Yeast_Item)
            F100_HoldTime_PT.set_value(Fermenter100.HoldTime.PT)
            F100_HoldTime_ET.set_value(Fermenter100.HoldTime.ET)
            F100_Level_PV.set_value(Fermenter100.LevelPV)
            F100_MaterialID.set_value(Fermenter100.MaterialID)
            F100_State.set_value(Fermenter100.NewState)
            F100_Status.set_value(Fermenter100.NewStatus)
            F100_GreenBeer_PV.set_value(Fermenter100.GreenBeerPV)
            F100_InletValve_CLS.set_value(Fermenter100.InletValve.CLS)
            F100_InletValve_OLS.set_value(Fermenter100.InletValve.OLS)
            F100_InletValve_PV.set_value(Fermenter100.InletValve.PV)
            F100_OutletPump_AuxContact.set_value(Fermenter100.OutletPump.AuxContact)
            F100_OutletPump_PV.set_value(Fermenter100.OutletPump.PV)
            F100_OutletValve_CLS.set_value(Fermenter100.OutletValve.CLS)
            F100_OutletValve_OLS.set_value(Fermenter100.OutletValve.OLS)
            F100_OutletValve_PV.set_value(Fermenter100.OutletValve.PV)
            F100_Prod_GreenBeer_Item.set_value(Fermenter100.Prod_GreenBeer_Item)
            F100_Prod_GreenBeer_ToLot.set_value(Fermenter100.Prod_GreenBeer_ToLot)
            F100_ProductionID.set_value(Fermenter100.ProductionID)
            F100_Scrap.set_value(Fermenter100.Scrap)
            F100_ShipTo_Tank.set_value(Fermenter100.ShipTo_Tank)
            F100_Temperature_PV.set_value(Fermenter100.TemperaturePV)
            F100_Temperature_SP.set_value(Fermenter100.TemperatureSP)
            F100_UtilizationState .set_value(Fermenter100.UtilizationState) 
            F100_Utilization.set_value(Fermenter100.Utilization)
            F100_Yeast_PV.set_value(Fermenter100.YeastPV)
            F100_Yeast_SP.set_value(Fermenter100.YeastSP)
            F100_YeastPump_AuxContact.set_value(Fermenter100.YeastPump.AuxContact)
            F100_YeastPump_PV.set_value(Fermenter100.YeastPump.PV)

            # Fermenter200
            F200_ChillWaterValve_CLS.set_value(Fermenter200.ChillWaterValve.CLS)
            F200_ChillWaterValve_OLS.set_value(Fermenter200.ChillWaterValve.OLS)
            F200_ChillWaterValve_PV.set_value(Fermenter200.ChillWaterValve.PV)
            F200_Cons_BrewedWort_FromLot.set_value(Fermenter200.Cons_BrewedWort_FromLot)  
            F200_Cons_BrewedWort_Item.set_value(Fermenter200.Cons_BrewedWort_Item)
            F200_Cons_Yeast_FromLot.set_value(Fermenter200.Cons_Yeast_FromLot)
            F200_Cons_Yeast_Item.set_value(Fermenter200.Cons_Yeast_Item)
            F200_HoldTime_PT.set_value(Fermenter200.HoldTime.PT)
            F200_HoldTime_ET.set_value(Fermenter200.HoldTime.ET)
            F200_Level_PV.set_value(Fermenter200.LevelPV)
            F200_MaterialID.set_value(Fermenter200.MaterialID)
            F200_State.set_value(Fermenter200.NewState)
            F200_Status.set_value(Fermenter200.NewStatus)
            F200_GreenBeer_PV.set_value(Fermenter200.GreenBeerPV)
            F200_InletValve_CLS.set_value(Fermenter200.InletValve.CLS)
            F200_InletValve_OLS.set_value(Fermenter200.InletValve.OLS)
            F200_InletValve_PV.set_value(Fermenter200.InletValve.PV)
            F200_OutletPump_AuxContact.set_value(Fermenter200.OutletPump.AuxContact)
            F200_OutletPump_PV.set_value(Fermenter200.OutletPump.PV)
            F200_OutletValve_CLS.set_value(Fermenter200.OutletValve.CLS)
            F200_OutletValve_OLS.set_value(Fermenter200.OutletValve.OLS)
            F200_OutletValve_PV.set_value(Fermenter200.OutletValve.PV)
            F200_Prod_GreenBeer_Item.set_value(Fermenter200.Prod_GreenBeer_Item)
            F200_Prod_GreenBeer_ToLot.set_value(Fermenter200.Prod_GreenBeer_ToLot)
            F200_ProductionID.set_value(Fermenter200.ProductionID)
            F200_Scrap.set_value(Fermenter200.Scrap)
            F200_ShipTo_Tank.set_value(Fermenter200.ShipTo_Tank)
            F200_Temperature_PV.set_value(Fermenter200.TemperaturePV)
            F200_Temperature_SP.set_value(Fermenter200.TemperatureSP)
            F200_UtilizationState .set_value(Fermenter200.UtilizationState) 
            F200_Utilization.set_value(Fermenter200.Utilization)
            F200_Yeast_PV.set_value(Fermenter200.YeastPV)
            F200_Yeast_SP.set_value(Fermenter200.YeastSP)
            F200_YeastPump_AuxContact.set_value(Fermenter200.YeastPump.AuxContact)
            F200_YeastPump_PV.set_value(Fermenter200.YeastPump.PV)

            # Bright Tank 301
            BT301_AllocatedFrom.set_value(BrightTank301.AllocatedFrom)
            BT301_ChillWaterValve_CLS.set_value(BrightTank301.ChillWaterValve.CLS)
            BT301_ChillWaterValve_OLS.set_value(BrightTank301.ChillWaterValve.OLS)
            BT301_ChillWaterValve_PV.set_value(BrightTank301.ChillWaterValve.PV)
            BT301_Cons_GreenBeer_FromLot.set_value(BrightTank301.Cons_GreenBeer_FromLot)
            BT301_Cons_GreenBeer_Item.set_value(BrightTank301.Cons_GreenBeer_Item)
            BT301_HoldTime_PT.set_value(BrightTank301.HoldTime.PT)
            BT301_HoldTime_ET.set_value(BrightTank301.HoldTime.ET)
            BT301_Level_PV.set_value(BrightTank301.LevelPV)
            BT301_MaterialID.set_value(BrightTank301.MaterialID)
            BT301_State.set_value(BrightTank301.NewState)
            BT301_Status.set_value(BrightTank301.NewStatus)
            BT301_Beer_PV.set_value(BrightTank301.BeerPV)
            BT301_Beer_SP.set_value(BrightTank301.BeerSP)
            BT301_InletValve_CLS.set_value(BrightTank301.InletValve.CLS)
            BT301_InletValve_OLS.set_value(BrightTank301.InletValve.OLS)
            BT301_InletValve_PV.set_value(BrightTank301.InletValve.PV)
            BT301_OutletPump_AuxContact.set_value(BrightTank301.OutletPump.AuxContact)
            BT301_OutletPump_PV.set_value(BrightTank301.OutletPump.PV)
            BT301_OutletValve_CLS.set_value(BrightTank301.OutletValve.CLS)
            BT301_OutletValve_OLS.set_value(BrightTank301.OutletValve.OLS)
            BT301_OutletValve_PV.set_value(BrightTank301.OutletValve.PV)
            BT301_Prod_Beer_Item.set_value(BrightTank301.Prod_Beer_Item)
            BT301_Prod_Beer_ToLot.set_value(BrightTank301.Prod_Beer_ToLot)
            BT301_ProductionID.set_value(BrightTank301.ProductionID)  
            BT301_Temperature_PV.set_value(BrightTank301.TemperaturePV)
            BT301_Temperature_SP.set_value(BrightTank301.TemperatureSP)
            BT301_UtilizationState.set_value(BrightTank301.UtilizationState) 
            BT301_Utilization.set_value(BrightTank301.Utilization)  
            BT301_BeerShipped.set_value(BrightTank301.BeerShipped)
            BT301_ShipTo_Tank.set_value(BrightTank301.ShipToTank)

            # Bright Tank 302
            BT302_AllocatedFrom.set_value(BrightTank302.AllocatedFrom)
            BT302_ChillWaterValve_CLS.set_value(BrightTank302.ChillWaterValve.CLS)
            BT302_ChillWaterValve_OLS.set_value(BrightTank302.ChillWaterValve.OLS)
            BT302_ChillWaterValve_PV.set_value(BrightTank302.ChillWaterValve.PV)
            BT302_Cons_GreenBeer_FromLot.set_value(BrightTank302.Cons_GreenBeer_FromLot)
            BT302_Cons_GreenBeer_Item.set_value(BrightTank302.Cons_GreenBeer_Item)
            BT302_HoldTime_PT.set_value(BrightTank302.HoldTime.PT)
            BT302_HoldTime_ET.set_value(BrightTank302.HoldTime.ET)
            BT302_Level_PV.set_value(BrightTank302.LevelPV)
            BT302_MaterialID.set_value(BrightTank302.MaterialID)
            BT302_State.set_value(BrightTank302.NewState)
            BT302_Status.set_value(BrightTank302.NewStatus)
            BT302_Beer_PV.set_value(BrightTank302.BeerPV)
            BT302_Beer_SP.set_value(BrightTank302.BeerSP)
            BT302_InletValve_CLS.set_value(BrightTank302.InletValve.CLS)
            BT302_InletValve_OLS.set_value(BrightTank302.InletValve.OLS)
            BT302_InletValve_PV.set_value(BrightTank302.InletValve.PV)
            BT302_OutletPump_AuxContact.set_value(BrightTank302.OutletPump.AuxContact)
            BT302_OutletPump_PV.set_value(BrightTank302.OutletPump.PV)
            BT302_OutletValve_CLS.set_value(BrightTank302.OutletValve.CLS)
            BT302_OutletValve_OLS.set_value(BrightTank302.OutletValve.OLS)
            BT302_OutletValve_PV.set_value(BrightTank302.OutletValve.PV)
            BT302_Prod_Beer_Item.set_value(BrightTank302.Prod_Beer_Item)
            BT302_Prod_Beer_ToLot.set_value(BrightTank302.Prod_Beer_ToLot)
            BT302_ProductionID.set_value(BrightTank302.ProductionID)  
            BT302_Temperature_PV.set_value(BrightTank302.TemperaturePV)
            BT302_Temperature_SP.set_value(BrightTank302.TemperatureSP)
            BT302_UtilizationState.set_value(BrightTank302.UtilizationState) 
            BT302_Utilization.set_value(BrightTank302.Utilization)  
            BT302_BeerShipped.set_value(BrightTank302.BeerShipped)
            BT302_ShipTo_Tank.set_value(BrightTank302.ShipToTank)

            # Bright Tank 003
            BT303_AllocatedFrom.set_value(BrightTank303.AllocatedFrom)
            BT303_ChillWaterValve_CLS.set_value(BrightTank303.ChillWaterValve.CLS)
            BT303_ChillWaterValve_OLS.set_value(BrightTank303.ChillWaterValve.OLS)
            BT303_ChillWaterValve_PV.set_value(BrightTank303.ChillWaterValve.PV)
            BT303_Cons_GreenBeer_FromLot.set_value(BrightTank303.Cons_GreenBeer_FromLot)
            BT303_Cons_GreenBeer_Item.set_value(BrightTank303.Cons_GreenBeer_Item)
            BT303_HoldTime_PT.set_value(BrightTank303.HoldTime.PT)
            BT303_HoldTime_ET.set_value(BrightTank303.HoldTime.ET)
            BT303_Level_PV.set_value(BrightTank303.LevelPV)
            BT303_MaterialID.set_value(BrightTank303.MaterialID)
            BT303_State.set_value(BrightTank303.NewState)
            BT303_Status.set_value(BrightTank303.NewStatus)
            BT303_Beer_PV.set_value(BrightTank303.BeerPV)
            BT303_Beer_SP.set_value(BrightTank303.BeerSP)
            BT303_InletValve_CLS.set_value(BrightTank303.InletValve.CLS)
            BT303_InletValve_OLS.set_value(BrightTank303.InletValve.OLS)
            BT303_InletValve_PV.set_value(BrightTank303.InletValve.PV)
            BT303_OutletPump_AuxContact.set_value(BrightTank303.OutletPump.AuxContact)
            BT303_OutletPump_PV.set_value(BrightTank303.OutletPump.PV)
            BT303_OutletValve_CLS.set_value(BrightTank303.OutletValve.CLS)
            BT303_OutletValve_OLS.set_value(BrightTank303.OutletValve.OLS)
            BT303_OutletValve_PV.set_value(BrightTank303.OutletValve.PV)
            BT303_Prod_Beer_Item.set_value(BrightTank303.Prod_Beer_Item)
            BT303_Prod_Beer_ToLot.set_value(BrightTank303.Prod_Beer_ToLot)
            BT303_ProductionID.set_value(BrightTank303.ProductionID)  
            BT303_Temperature_PV.set_value(BrightTank303.TemperaturePV)
            BT303_Temperature_SP.set_value(BrightTank303.TemperatureSP)
            BT303_UtilizationState.set_value(BrightTank303.UtilizationState) 
            BT303_Utilization.set_value(BrightTank303.Utilization)  
            BT303_BeerShipped.set_value(BrightTank303.BeerShipped)
            BT303_ShipTo_Tank.set_value(BrightTank303.ShipToTank)

            # Bright Tank 004
            BT304_AllocatedFrom.set_value(BrightTank304.AllocatedFrom)
            BT304_ChillWaterValve_CLS.set_value(BrightTank304.ChillWaterValve.CLS)
            BT304_ChillWaterValve_OLS.set_value(BrightTank304.ChillWaterValve.OLS)
            BT304_ChillWaterValve_PV.set_value(BrightTank304.ChillWaterValve.PV)
            BT304_Cons_GreenBeer_FromLot.set_value(BrightTank304.Cons_GreenBeer_FromLot)
            BT304_Cons_GreenBeer_Item.set_value(BrightTank304.Cons_GreenBeer_Item)
            BT304_HoldTime_PT.set_value(BrightTank304.HoldTime.PT)
            BT304_HoldTime_ET.set_value(BrightTank304.HoldTime.ET)
            BT304_Level_PV.set_value(BrightTank304.LevelPV)
            BT304_MaterialID.set_value(BrightTank304.MaterialID)
            BT304_State.set_value(BrightTank304.NewState)
            BT304_Status.set_value(BrightTank304.NewStatus)
            BT304_Beer_PV.set_value(BrightTank304.BeerPV)
            BT304_Beer_SP.set_value(BrightTank304.BeerSP)
            BT304_InletValve_CLS.set_value(BrightTank304.InletValve.CLS)
            BT304_InletValve_OLS.set_value(BrightTank304.InletValve.OLS)
            BT304_InletValve_PV.set_value(BrightTank304.InletValve.PV)
            BT304_OutletPump_AuxContact.set_value(BrightTank304.OutletPump.AuxContact)
            BT304_OutletPump_PV.set_value(BrightTank304.OutletPump.PV)
            BT304_OutletValve_CLS.set_value(BrightTank304.OutletValve.CLS)
            BT304_OutletValve_OLS.set_value(BrightTank304.OutletValve.OLS)
            BT304_OutletValve_PV.set_value(BrightTank304.OutletValve.PV)
            BT304_Prod_Beer_Item.set_value(BrightTank304.Prod_Beer_Item)
            BT304_Prod_Beer_ToLot.set_value(BrightTank304.Prod_Beer_ToLot)
            BT304_ProductionID.set_value(BrightTank304.ProductionID)  
            BT304_Temperature_PV.set_value(BrightTank304.TemperaturePV)
            BT304_Temperature_SP.set_value(BrightTank304.TemperatureSP)
            BT304_UtilizationState.set_value(BrightTank304.UtilizationState) 
            BT304_Utilization.set_value(BrightTank304.Utilization)  
            BT304_BeerShipped.set_value(BrightTank304.BeerShipped)
            BT304_ShipTo_Tank.set_value(BrightTank304.ShipToTank)

            # Bright Tank 005
            BT305_AllocatedFrom.set_value(BrightTank305.AllocatedFrom)
            BT305_ChillWaterValve_CLS.set_value(BrightTank305.ChillWaterValve.CLS)
            BT305_ChillWaterValve_OLS.set_value(BrightTank305.ChillWaterValve.OLS)
            BT305_ChillWaterValve_PV.set_value(BrightTank305.ChillWaterValve.PV)
            BT305_Cons_GreenBeer_FromLot.set_value(BrightTank305.Cons_GreenBeer_FromLot)
            BT305_Cons_GreenBeer_Item.set_value(BrightTank305.Cons_GreenBeer_Item)
            BT305_HoldTime_PT.set_value(BrightTank305.HoldTime.PT)
            BT305_HoldTime_ET.set_value(BrightTank305.HoldTime.ET)
            BT305_Level_PV.set_value(BrightTank305.LevelPV)
            BT305_MaterialID.set_value(BrightTank305.MaterialID)
            BT305_State.set_value(BrightTank305.NewState)
            BT305_Status.set_value(BrightTank305.NewStatus)
            BT305_Beer_PV.set_value(BrightTank305.BeerPV)
            BT305_Beer_SP.set_value(BrightTank305.BeerSP)
            BT305_InletValve_CLS.set_value(BrightTank305.InletValve.CLS)
            BT305_InletValve_OLS.set_value(BrightTank305.InletValve.OLS)
            BT305_InletValve_PV.set_value(BrightTank305.InletValve.PV)
            BT305_OutletPump_AuxContact.set_value(BrightTank305.OutletPump.AuxContact)
            BT305_OutletPump_PV.set_value(BrightTank305.OutletPump.PV)
            BT305_OutletValve_CLS.set_value(BrightTank305.OutletValve.CLS)
            BT305_OutletValve_OLS.set_value(BrightTank305.OutletValve.OLS)
            BT305_OutletValve_PV.set_value(BrightTank305.OutletValve.PV)
            BT305_Prod_Beer_Item.set_value(BrightTank305.Prod_Beer_Item)
            BT305_Prod_Beer_ToLot.set_value(BrightTank305.Prod_Beer_ToLot)
            BT305_ProductionID.set_value(BrightTank305.ProductionID)  
            BT305_Temperature_PV.set_value(BrightTank305.TemperaturePV)
            BT305_Temperature_SP.set_value(BrightTank305.TemperatureSP)
            BT305_UtilizationState.set_value(BrightTank305.UtilizationState) 
            BT305_Utilization.set_value(BrightTank305.Utilization)  
            BT305_BeerShipped.set_value(BrightTank305.BeerShipped)
            BT305_ShipTo_Tank.set_value(BrightTank305.ShipToTank)

            # BottlingLine 401 
            BL401_AllocatedFrom.set_value(BottleLine401.AllocatedFrom)
            BL401_Beer_PV.set_value(BottleLine401.BeerPV)
            BL401_Bottle_PV.set_value(BottleLine401.BottlePV)
            BL401_Bottle_SP.set_value(BottleLine401.BottleSP)
            BL401_Cons_Beer_FromLot.set_value(BottleLine401.Cons_Beer_FromLot)
            BL401_Cons_Beer_Item.set_value(BottleLine401.Cons_Beer_Item)
            BL401_Cons_Bottle_FromLot.set_value(BottleLine401.Cons_Bottle_FromLot)
            BL401_Cons_Bottle_Item.set_value(BottleLine401.Cons_Bottle_Item)
            BL401_Cons_Cap_FromLot.set_value(BottleLine401.Cons_Cap_FromLot)
            BL401_Cons_Cap_Item.set_value(BottleLine401.Cons_Cap_Item)
            BL401_Cons_Label_FromLot.set_value(BottleLine401.Cons_Label_FromLot)
            BL401_Cons_Label_Item.set_value(BottleLine401.Cons_Label_Item)
            BL401_Level_PV.set_value(BottleLine401.LevelPV)
            BL401_MaterialID.set_value(BottleLine401.MaterialID)
            BL401_Prod_BottledBeer_Item.set_value(BottleLine401.Prod_BottledBeer_Item)
            BL401_Prod_BottledBeer_ToLot.set_value(BottleLine401.Prod_BottledBeer_ToLot)
            BL401_ProductionID.set_value(BottleLine401.ProductionID)
            BL401_Speed_PV.set_value(BottleLine401.SpeedPV)
            BL401_Speed_SP.set_value(BottleLine401.SpeedSP)
            BL401_Temperature_PV.set_value(BottleLine401.TemperaturePV)
            BL401_Temperature_SP.set_value(BottleLine401.TemperatureSP)
            BL401_HoldTime_PT.set_value(BottleLine401.HoldTime.PT)
            BL401_HoldTime_ET.set_value(BottleLine401.HoldTime.ET)
            BL401_State.set_value(BottleLine401.NewState)
            BL401_Status.set_value(BottleLine401.NewStatus)        
            BL401_UtilizationState.set_value(BottleLine401.UtilizationState) 
            BL401_Utilization.set_value(BottleLine401.Utilization)        
            BL401_Scrap.set_value(BottleLine401.Scrap)

            # BottlingLine 402 
            BL402_AllocatedFrom.set_value(BottleLine402.AllocatedFrom)
            BL402_Beer_PV.set_value(BottleLine402.BeerPV)
            BL402_Bottle_SP.set_value(BottleLine402.BottleSP)
            BL402_Bottle_PV.set_value(BottleLine402.BottlePV)
            BL402_Cons_Beer_FromLot.set_value(BottleLine402.Cons_Beer_FromLot)
            BL402_Cons_Beer_Item.set_value(BottleLine402.Cons_Beer_Item)
            BL402_Cons_Bottle_FromLot.set_value(BottleLine402.Cons_Bottle_FromLot)
            BL402_Cons_Bottle_Item.set_value(BottleLine402.Cons_Bottle_Item)
            BL402_Cons_Cap_FromLot.set_value(BottleLine402.Cons_Cap_FromLot)
            BL402_Cons_Cap_Item.set_value(BottleLine402.Cons_Cap_Item)
            BL402_Cons_Label_FromLot.set_value(BottleLine402.Cons_Label_FromLot)
            BL402_Cons_Label_Item.set_value(BottleLine402.Cons_Label_Item)
            BL402_Level_PV.set_value(BottleLine402.LevelPV)
            BL402_MaterialID.set_value(BottleLine402.MaterialID)
            BL402_Prod_BottledBeer_Item.set_value(BottleLine402.Prod_BottledBeer_Item)
            BL402_Prod_BottledBeer_ToLot.set_value(BottleLine402.Prod_BottledBeer_ToLot)
            BL402_ProductionID.set_value(BottleLine402.ProductionID)
            BL402_Speed_PV.set_value(BottleLine402.SpeedPV)
            BL402_Speed_SP.set_value(BottleLine402.SpeedSP)
            BL402_Temperature_PV.set_value(BottleLine402.TemperaturePV)
            BL402_Temperature_SP.set_value(BottleLine402.TemperatureSP)
            BL402_HoldTime_PT.set_value(BottleLine402.HoldTime.PT)
            BL402_HoldTime_ET.set_value(BottleLine402.HoldTime.ET)
            BL402_State.set_value(BottleLine402.NewState)
            BL402_Status.set_value(BottleLine402.NewStatus)        
            BL402_UtilizationState.set_value(BottleLine402.UtilizationState) 
            BL402_Utilization.set_value(BottleLine402.Utilization)        
            BL402_Scrap.set_value(BottleLine402.Scrap)

            # BottlingLine 403 
            BL403_AllocatedFrom.set_value(BottleLine403.AllocatedFrom)
            BL403_Beer_PV.set_value(BottleLine403.BeerPV)
            BL403_Bottle_SP.set_value(BottleLine403.BottleSP)
            BL403_Bottle_PV.set_value(BottleLine403.BottlePV)
            BL403_Cons_Beer_FromLot.set_value(BottleLine403.Cons_Beer_FromLot)
            BL403_Cons_Beer_Item.set_value(BottleLine403.Cons_Beer_Item)
            BL403_Cons_Bottle_FromLot.set_value(BottleLine403.Cons_Bottle_FromLot)
            BL403_Cons_Bottle_Item.set_value(BottleLine403.Cons_Bottle_Item)
            BL403_Cons_Cap_FromLot.set_value(BottleLine403.Cons_Cap_FromLot)
            BL403_Cons_Cap_Item.set_value(BottleLine403.Cons_Cap_Item)
            BL403_Cons_Label_FromLot.set_value(BottleLine403.Cons_Label_FromLot)
            BL403_Cons_Label_Item.set_value(BottleLine403.Cons_Label_Item)
            BL403_Level_PV.set_value(BottleLine403.LevelPV)
            BL403_MaterialID.set_value(BottleLine403.MaterialID)
            BL403_Prod_BottledBeer_Item.set_value(BottleLine403.Prod_BottledBeer_Item)
            BL403_Prod_BottledBeer_ToLot.set_value(BottleLine403.Prod_BottledBeer_ToLot)
            BL403_ProductionID.set_value(BottleLine403.ProductionID)
            BL403_Speed_PV.set_value(BottleLine403.SpeedPV)
            BL403_Speed_SP.set_value(BottleLine403.SpeedSP)
            BL403_Temperature_PV.set_value(BottleLine403.TemperaturePV)
            BL403_Temperature_SP.set_value(BottleLine403.TemperatureSP)
            BL403_HoldTime_PT.set_value(BottleLine403.HoldTime.PT)
            BL403_HoldTime_ET.set_value(BottleLine403.HoldTime.ET)
            BL403_State.set_value(BottleLine403.NewState)
            BL403_Status.set_value(BottleLine403.NewStatus)        
            BL403_UtilizationState.set_value(BottleLine403.UtilizationState) 
            BL403_Utilization.set_value(BottleLine403.Utilization)        
            BL403_Scrap.set_value(BottleLine403.Scrap)            

            # Set Scan rate
            time.sleep(.1)   

    finally:
        #close connection, remove subcsriptions, etc
        server.stop()
        