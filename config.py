#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os

class DefaultConfig:
    """ Bot Configuration """

    PORT = 3979
    # APP_ID = os.environ.get("MicrosoftAppId", "8edc6723-1c38-4049-ac15-3c062185c092")
    # APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "cUY8Q~qk~cRySscMSXdcI8OCy56i8tAWun_mBat~")
    APP_ID = os.environ.get("MicrosoftAppId", "")
    APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")
