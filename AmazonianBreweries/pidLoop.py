#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#----------------------------------------------------------------------------
# Created By  : Nick Santucci @nictooch
# Created Date: February 14 2022 
# version ='1.0.0'
# ---------------------------------------------------------------------------

class pidLoop:  

    """

    Class Overview
    ----------

    A class used to represent a "PID Loop" which is a control loop mechanism employing feedback that is widely used in 
    industrial control systems and a variety of other applications requiring continuously modulated control. 
    A PID controller continuously calculates an error value e(t) as the difference between a desired setpoint (SP) 
    and a measured process variable (PV) and applies a correction based on proportional, integral, and derivative terms 
    (denoted P, I, and D respectively).           

    Attributes
    ----------    

    Name (Name provided by calling Class)
    Bias (Provides a steady offset to the correction value of the PID loop)
    PV (Actual measured value)
    SP (Setpoint desired)
    K (Process Gain)
    Ti (Reset Time)
    MassOffset
    PVincreaseMultiplier 

    Methods
    -------

    __init__(self, EquipmentName) - Class Constructor
    Run(self) - method to simulate equipment data

    """  

    # Class Constructor
    def __init__(self, Name, Bias, K, MassOffset, Ti, PVincreaseMultiplier):
        self.Name = Name
        self.Out = 0.0
        self.SP = 0.0
        self.PV = 80.0
        self.K = K
        self.Bias = Bias
        self.MassOffset = MassOffset
        self.PVincreaseMultiplier = PVincreaseMultiplier
        self.Ti = Ti
        self.Enabled = False

    # Run method to execute pidLoop functionality 
    def Run(self, SP, PV):

        self.SP = SP
        self.PV = PV

        if self.Enabled:

            self.Out = ((self.SP - self.PV) / self.SP * self.K + self.Bias) * (((self.MassOffset * 25.0) / 100.0) + 0.75)

            # Clamp Bias when output is out of range
            if (self.Out > 0.0) and (self.Out < 1.0):
                self.Bias = self.Bias + ( self.SP - self.PV) / self.SP * self.K / self.Ti

            if (self.Out >= 1.0):
                self.Out = 1.0

            if (self.Out <= 0.0):
                self.Out = 0.0

            if (self.Bias >= 1.0):
                self.Bias = 1.0

            if (self.Bias <= 0.0):
                self.Bias = 0.0

            # Set PV
            self.PV = self.PV + (self.PV * (self.Out - 0.1) / self.SP) * self.PVincreaseMultiplier

        return self.PV

            