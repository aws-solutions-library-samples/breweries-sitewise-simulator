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
from dataclasses import dataclass

UtilizationList = ['No Orders','Starved Supply','Running (Slow)','Unknown','EStop','Sticking Valve','Pump Overload','Faulty Wiring','Tripped Breaker','Planned Maintenance','Unplanned Maintenance']

UtilizationStateList = ['Demand','Downtime','Maintenance'] 

ScanRates = [.97,.98,.99,.100]

@dataclass
class NewStatusEnum:
    Allocated: str = "Allocated"
    Filling: str = "Filling"
    Idle: str = "Idle"
    RampingUp: str = "Ramping Up"
    RampingDown: str = "Ramping Down"
    RampingUp1: str = "RampingUp1"
    RampingUp2: str = "RampingUp2"
    Holding: str = "Holding"
    Holding1: str = "Holding1"
    Holding2: str = "Holding2"
    Draining: str = "Draining"
    WaitingForOperator: str = "WaitingForOperator " 

@dataclass
class NewStateEnum:
    Done: str = "Done"
    Ready: str = "Ready"
    Running: str = "Running"
    Paused: str = "Paused"
    Aborted: str = "Aborted"