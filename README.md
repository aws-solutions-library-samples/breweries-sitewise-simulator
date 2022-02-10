# Amazonian Breweries OPC UA Server Getting Started

## Summary

Amazonian Breweries is a Python based program to exercise the capabilities of IoT SiteWise (Monitor), IoT Greengrass, IoT TwinMaker, and other IoT based AWS services that constantly runs and produces factory like data exposed via an OPC UA Server (a cross-platform, open-source, IEC62541 standard for data exchange from sensors to cloud applications developed by the OPC Foundation) for consumption by an OPC UA Client (like the IoT SiteWise OPC UA Collector). 

## Prerequisites

1. [Python3](https://www.python.org/downloads/)
   - Verify your python3 path and version (3.10.0+). 
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

3. Open the AmazonianBreweries\awsBrewOPCUAServer.py file, go to line 70, and update the IP address to your servers IP address

4. Create environment (Linux, Windows, or macOS) to host the Amazonian Breweries OPC UA Server Python program. 

5. Create an Edge Device (Ubuntu 20.04 or 18.04, Red Hat Enterprise Linux (RHEL) 8, or Amazon Linux 2) to host AWS IoT SiteWise Edge  gateway.  

6. Create and deploy the AWS IoT SiteWise Edge gateway to the Edge Device (see step 5 above), please use this URL for reference - https://docs.aws.amazon.com/iot-sitewise/latest/userguide/configure-gateway-ggv2.html. The Data processing pack is not required.     
