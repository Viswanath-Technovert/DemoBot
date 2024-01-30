#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os

class DefaultConfig:
    """ Bot Configuration """

    PORT = 3978
    APP_ID = os.environ.get("MicrosoftAppId", "b684497f-2ff5-4b6b-a098-43e67a30d53e")
    APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "j558Q~qKOViS.DgZNL8XxX9CjbC.yYW5iFfN3cM2")
    # APP_ID = os.environ.get("MicrosoftAppId", "")
    # APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")
