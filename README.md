# Amazonian Breweries OPC UA Server Getting Started

## Summary

Amazonian Breweries is a Python based program to exercise the capabilities of IoT SiteWise (Monitor), IoT Greengrass, IoT TwinMaker, and other IoT based AWS services that constantly runs and produces factory like data exposed via an OPC UA Server (a cross-platform, open-source, IEC62541 standard for data exchange from sensors to cloud applications developed by the OPC Foundation) for consumption by an OPC UA Client (like the IoT SiteWise OPC UA Collector). 

## Prerequisites

1. [Python3](https://www.python.org/downloads/)
   - Verify your python3 path and version (<b>needs to be 3.10.0+</b>). 
     ```
     python3 --version

     ```
2. Install the OPC UA Server Python Library

    - With pip:
      ```
      pip install opcua

      ```

    - Ubuntu:
      ```
      apt install python-opcua        # Library
      apt install python-opcua-tools  # Command-line tools

      ```

    - Dependencies:
      ```
      cryptography, dateutil, lxml and pytz.

      ```

3. Create a server environment (Linux, Windows, or macOS) to host the Amazonian Breweries OPC UA Server Python program. 

4. Copy Amazonian Breweries program folder to the server host (see Step 3 above), then open the AmazonianBreweries\awsBrewOPCUAServer.py file, go to line 70, and update the IP address to your servers IP address.  

5. Start the Amazonian Breweries program - python3.exe "directory where program folder was copied to"/AmazonianBreweries/awsBrewOPCUAServer.py 

6. Create an Edge Device (Ubuntu 20.04 or 18.04, Red Hat Enterprise Linux (RHEL) 8, or Amazon Linux 2) to host AWS IoT SiteWise Edge  gateway.  

7. Create and deploy the AWS IoT SiteWise Edge gateway to the Edge Device (see step 5 above), please use this URL for reference - https://docs.aws.amazon.com/iot-sitewise/latest/userguide/configure-gateway-ggv2.html. The Data processing pack is not required.

8. Now you will need to create Models in the IoT SiteWise console, please see this URL for reference - https://docs.aws.amazon.com/iot-sitewise/latest/userguide/industrial-asset-models.html. The Amazonian Breweries project leverages the ISA-95 Equipment Model to define the plant hierarchy (Enterprise->Site->Area->Production Unit). To match up with the Amazonian Breweries OPC UA Server Plant Hierachy and Assets, here are the Asset Models and Measurements you will need to create in IoT SiteWise:

    - Enterprise [Enterprise Model](./images/Enterprise_Model.jpg)
    - Site [Site Model](./images/Site_Model.jpg)
    - Area [Area Model](./images/Area_Model.jpg)
    - Roaster [Roaster Model](./images/Roaster_Model.jpg)
      - Roaster Measurements [Roaster Measurements](./images/Roaster_Model_Measurements.jpg)
    - MaltMill [Roaster Model](./images/MaltMill_Model.jpg)
      - MaltMill Measurements [MaltMill Measurements](./images/MaltMill_Model_Measurements.jpg)
    - MashTun [MashTun Model](./images/MashTun_Model.jpg)
      - MashTun Measurements Part 1 [MaltMill Measurements Part 1](./images/MashTun_Model_Measurements_Part_1.jpg)
      - MashTun Measurements Part 2 [MaltMill Measurements Part 2](./images/MashTun_Model_Measurements_Part_2.jpg)
    - BoilKettle [BoilKettle Model](./images/BoilKettle_Model.jpg)
      - BoilKettle Measurements Part 1 [BoilKettle Measurements Part 1](./images/BoilKettle_Model_Measurements_Part_1.jpg)
      - BoilKettle Measurements Part 2 [BoilKettle Measurements Part 2](./images/BoilKettle_Model_Measurements_Part_2.jpg)
    - Fermenter [Fermenter Model](./images/Fermenter_Model.jpg)
      - Fermenter Measurements Part 1 [Fermenter Measurements Part 1](./images/Fermenter_Model_Measurements_Part_1.jpg)
      - Fermenter Measurements Part 2 [Fermenter Measurements Part 2](./images/Fermenter_Model_Measurements_Part_2.jpg)
    - BrightTank [BrightTank Model](./images/BrightTank_Model.jpg)
      - BrightTank Measurements Part 1 [BrightTank Measurements Part 1](./images/BrightTank_Model_Measurements_Part_1.jpg)
      - BrightTank Measurements Part 2 [BrightTank Measurements Part 2](./images/BrightTank_Model_Measurements_Part_2.jpg)
    - BottleLine [BottleLine Model](./images/BottleLine_Model.jpg)
      - BottleLine Measurements Part 1 [BottleLine Measurements Part 1](./images/BottleLine_Model_Measurements_Part_1.jpg)
      - BottleLine Measurements Part 2 [BottleLine Measurements Part 2](./images/BottleLine_Model_Measurements_Part_2.jpg)
      
9. In order to create a plant hierarchy (Enterprise->Site->Area->Production Unit), we have to edit the above Models to support "contained" Models. 
    - Select the <b>Enterprise</b> Model and click the <b>Edit</b> button, scroll down to the <b>Hierarchy definitions</b> section, then click <b>Add new hierarchy</b>. For the <b>Hierarchy name</b> use <b>Sites</b> and then in the drop down listbox choose the <b>Site</b> Model, then click the <b>Save</b> button at the bottom of the page.  
    - Next, select the <b>Site</b> Model and click the <b>Edit</b> button, scroll down to the <b>Hierarchy definitions</b> section, then click <b>Add new hierarchy</b>. For the <b>Hierarchy name</b> use <b>Areas</b> and then in the drop down listbox choose the <b>Area</b> Model, then click the <b>Save</b> button at the bottom of the page. 
    - Finally, select the <b>Area</b> Model and click the <b>Edit</b> button, scroll down to the <b>Hierarchy definitions</b> section, then click <b>Add new hierarchy</b>. For the <b>Hierarchy name</b> use <b>Roaster</b> and then in the drop down listbox choose the <b>Roaster</b> Model, repeat this for "MaltMill/MaltMill", "MashTun/MashTun", "BoilKettle/BoilKettle", "Fermenter/Fermenter", "BrightTank/BrightTank", and "BottleLine/BottleLine", then click the <b>Save</b> button at the bottom of the page              

10. After creating the Models, we can create Assets that will represent the physical assets (digital twins) that exist in the manufacuring facility, please see this URL for reference - https://docs.aws.amazon.com/iot-sitewise/latest/userguide/create-assets.html.  The plant hierarchy that you will create looks like this [Asset Plant Hierarchy](./images/Asset_Plant_Hierarchy.jpg
).  

11. To begin creating Assets, click the <b>Create asset</b> button and create each of the following:
    - In the <b>Model</b> drop-down list box, select <b>BottleLine</b> and name it <b>BottleLine401</b>, click the <b>Create asset</b> button.  Repeat this process for <b>BottleLine402</b> and <b>BottleLine403</b>.
    - In the <b>Model</b> drop-down list box, select <b>BrightTank</b> and name it <b>BrightTank301</b>, click the <b>Create asset</b> button.  Repeat this process for <b>BrightTank302</b>, <b>BrightTank303</b>, <b>BrightTank304</b>, <b>BrightTank305</b>.
    - In the <b>Model</b> drop-down list box, select <b>Fermenter</b> and name it <b>Fermenter100</b>, click the <b>Create asset</b> button.  Repeat this process for <b>Fermenter200</b>. 
    - In the <b>Model</b> drop-down list box, select <b>MashTun</b> and name it <b>MashTun100</b>, click the <b>Create asset</b> button.  Repeat this process for <b>MashTun200</b>.
    - In the <b>Model</b> drop-down list box, select <b>MaltMill</b> and name it <b>MaltMill100</b>, click the <b>Create asset</b> button.  Repeat this process for <b>MaltMill100</b>.
    - In the <b>Model</b> drop-down list box, select <b>Roaster</b> and name it <b>Roaster100</b>, click the <b>Create asset</b> button.  Repeat this process for <b>Roaster200</b>.
    - In the <b>Model</b> drop-down list box, select <b>Area</b> and name it <b>Bottling</b>, click the <b>Create asset</b> button.  Repeat this process for <b>BeerStorage</b>, <b>Fermentation</b>, <b>Brewing</b>, <b>Mashing</b>, and <b>Roasting</b>.
    - In the <b>Model</b> drop-down list box, select <b>Site</b> and name it <b>TampaPlant</b>, click the <b>Create asset</b> button.
    - In the <b>Model</b> drop-down list box, select <b>Enterprise</b> and name it <b>AmazonianBreweries</b>, click the <b>Create asset</b> button.               

12. Now we need to create the Asset hierarchy for the physical assets for more meaningful data context. 
    - In the Assets list, open the <b>Bottling</b> Asset, click the <b>Edit</b> button, scroll down to <b>Assets associated to this asset</b> section and click the <b>Add associated asset</b> button and for <b>Hierarchy</b> select <b>BottleLine</b> and for the <b>Asset</b> select <b>BottleLine401</b>. Repeat this for <b>Bottleline/BottleLine402</b> and <b>Bottleline/BottleLine403</b>. 
    - In the Assets list, open the <b>BeerStorage</b> Asset, click the <b>Edit</b> button, scroll down to <b>Assets associated to this asset</b> section and click the <b>Add associated asset</b> button and for <b>Hierarchy</b> select <b>BrightTank</b> and for the <b>Asset</b> select <b>BrightTank301</b>. Repeat this for <b>BrightTank/BrightTank302</b>, <b>BrightTank/BrightTank303</b>, <b>BrightTank/BrightTank304</b>, and <b>BrightTank/BrightTank305</b>.    
    - In the Assets list, open the <b>Fermentation</b> Asset, click the <b>Edit</b> button, scroll down to <b>Assets associated to this asset</b> section and click the <b>Add associated asset</b> button and for <b>Hierarchy</b> select <b>Fermenter</b> and for the <b>Asset</b> select <b>Fermenter100</b>. Repeat this for <b>Fermenter/Fermenter200</b>. 
    - In the Assets list, open the <b>Brewing</b> Asset, click the <b>Edit</b> button, scroll down to <b>Assets associated to this asset</b> section and click the <b>Add associated asset</b> button and for <b>Hierarchy</b> select <b>BoilKettle</b> and for the <b>Asset</b> select <b>BoilKettle100</b>. Repeat this for <b>BoilKettle/BoilKettle200</b>.
    - In the Assets list, open the <b>Mashing</b> Asset, click the <b>Edit</b> button, scroll down to <b>Assets associated to this asset</b> section and click the <b>Add associated asset</b> button and for <b>Hierarchy</b> select <b>MaltMill</b> and for the <b>Asset</b> select <b>MaltMill100</b>. Repeat this for <b>MaltMill/MaltMill200</b> as well <b>MashTun/MashTun100</b> and <b>MashTun/MashTun200</b>. 
    - In the Assets list, open the <b>Roasting</b> Asset, click the <b>Edit</b> button, scroll down to <b>Assets associated to this asset</b> section and click the <b>Add associated asset</b> button and for <b>Hierarchy</b> select <b>Roaster</b> and for the <b>Asset</b> select <b>Roaster100</b>. Repeat this for <b>Roaster/Roaster200</b>.
    - In the Assets list, open the <b>TampaPlant</b> Asset, click the <b>Edit</b> button, scroll down to <b>Assets associated to this asset</b> section and click the <b>Add associated asset</b> button and for <b>Hierarchy</b> select <b>Areas</b> and for the <b>Asset</b> select <b>Bottling</b>. Repeat this for <b>Areas/BeerStorage</b>, <b>Areas/Fermentation</b>, <b>Areas/Brewing</b>, <b>Areas/Mashing</b>, and <b>Areas/Roasting</b>.
    - In the Assets list, open the <b>AmazonianBreweries</b> Asset, click the <b>Edit</b> button, scroll down to <b>Assets associated to this asset</b> section and click the <b>Add associated asset</b> button and for <b>Hierarchy</b> select <b>Sites</b> and for the <b>Asset</b> select <b>TampaPlant</b>. 

13. Refresh the browser to update the hierarchy.  


      
