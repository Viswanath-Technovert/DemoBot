# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
from langchain_openai.llms.azure import AzureOpenAI
# from langchain.embeddings import OpenAIEmbeddings
# from langchain.chat_models.azure_openai import AzureChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter
from llm_backend_updated import pdf_query
import os
from datetime import datetime
from sql_querying import sql_query

os.environ['OPENAI_API_VERSION'] = '2023-12-01-preview'
os.environ['AZURE_OPENAI_API_KEY'] = 'e63ed695495543d58595fab4e27e4ff1'

from botbuilder.core import ActivityHandler, MessageFactory, TurnContext,CardFactory, ConversationState
from botbuilder.schema import ChannelAccount, CardAction, ActionTypes, SuggestedActions,HeroCard,  CardAction
from botbuilder.dialogs import DialogSet, WaterfallDialog, WaterfallStepContext
from botbuilder.dialogs.prompts import TextPrompt, NumberPrompt, PromptOptions

from azure.core.credentials import AzureKeyCredential
from azure.ai.language.questionanswering import QuestionAnsweringClient
from azure.ai.language.conversations import ConversationAnalysisClient
import pyodbc
import pandas as pd
from botbuilder.core import CardFactory

import urllib
from langchain.sql_database import SQLDatabase

# Azure QnA Maker configuration
endpoint = "https://clu-gmbot.cognitiveservices.azure.com/"
credential = AzureKeyCredential("df8262daa6714cf4bb6e1ca71c191a5a")
knowledge_base_project = "GM-QandA"
# knowledge_base_project = "test-qanda"
deployment = "production"

# CLU configuration
clu_endpoint = "https://clu-gmbot.cognitiveservices.azure.com/"
clu_key = "df8262daa6714cf4bb6e1ca71c191a5a"
clu_project_name = "GM_CLU"
clu_deployment_name = "Guardsman_deployment"

def separate_outputs_from_db(results):
          
    ex_date = results[0][1]
    ex_day = results[0][2]
    start_time = format_time(results[0][3])
    end_time = format_time(results[0][4])
    return [ex_date,ex_day,start_time,end_time]

def format_time(time_string):
    # Define the input time format with an optional fractional part
    input_formats = ["%H:%M:%S.%f", "%H:%M:%S"]

    for format_string in input_formats:
        try:
            # Try to convert the string to datetime using the current format
            time_datetime = datetime.strptime(time_string, format_string)

            # If successful, format and return the result
            formatted_time = time_datetime.strftime("%I:%M %p")
            return formatted_time

        except ValueError:
            pass  # Ignore errors and try the next format

    # If none of the formats work, raise an error
    raise ValueError("Invalid time string format: {}".format(time_string))

def convert_dates(results):
    converted_results = []

    for result in results:
        name, date_datetime, day, start_time_str, end_time_str = result
        converted_results.append((name, date_datetime, day, start_time_str, end_time_str))

    return converted_results

# Function to get answers from QnA Maker
def custom_QandA(question_from_user):
    client = QuestionAnsweringClient(endpoint, credential)
    with client:
        # Use the provided question_from_user parameter
        question = question_from_user
        # Get answers from QnA Maker
        output = client.get_answers(
            question=question,
            project_name=knowledge_base_project,
            deployment_name=deployment
        )
        # Return the first answer
        return output.answers[0]

client = ConversationAnalysisClient(clu_endpoint, AzureKeyCredential(clu_key))

def answers_from_clu(question_from_user):
    client = ConversationAnalysisClient(clu_endpoint, AzureKeyCredential(clu_key))
    with client:
        result = client.analyze_conversation(
            task={
                "kind": "Conversation",
                "analysisInput": {
                    "conversationItem": {
                        "participantId": "1",
                        "id": "1",
                        "modality": "text",
                        "language": "en",
                        "text": question_from_user
                    },
                    "isLoggingEnabled": False
                },
                "parameters": {
                    "projectName": clu_project_name,
                    "deploymentName": clu_deployment_name,
                    "verbose": True
                }
            }
        )
    return result    


def get_sql_connection_string():
          
    # conn_string = ("Driver={SQL Server};"
    #                "Server=TL166;"
    #                "Database=GMBOT;"
    #                "Trusted_Connection=yes;")
    
    conn_string = ('Driver={ODBC Driver 17 for SQL Server};'
                  'Server=tcp:mysqlserver16666.database.windows.net,1433;'
                  'Database=GMBOT;'
                  'Uid=Azureuser;'
                  'Pwd={Azure@23498};')
    
    sql_connection = pyodbc.connect(conn_string)
    sql_cursor = sql_connection.cursor()

    return sql_cursor

def get_llm_connection_string():
    server = 'mysqlserver16666.database.windows.net'
    database = 'GMBOT'
    username = 'Azureuser'
    password = 'Azure@23498'   
    driver= '{ODBC Driver 17 for SQL Server}'

    conn = f"""Driver={driver};Server=tcp:{server},1433;Database={database};
    Uid={username};Pwd={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"""

    params = urllib.parse.quote_plus(conn)
    conn_str = 'mssql+pyodbc:///?autocommit=true&odbc_connect={}'.format(params)

    db = SQLDatabase.from_uri(conn_str)


    return db

def clu_get_intent(result_from_clu):
    top_intent = result_from_clu["result"]["prediction"]["topIntent"]
    intents_df = pd.DataFrame(result_from_clu["result"]["prediction"]["intents"])
    confidence_top_intent = intents_df[intents_df.category == top_intent].confidenceScore
    return top_intent, confidence_top_intent

username = 'Peter Jones'
date = "2023-11-13"

class MyBot(ActivityHandler):
    
    
    def __init__(self,conversation: ConversationState):
        self.con_state = conversation
        self.state_prop = self.con_state.create_property("dialog_set")
        self.dialog_set = DialogSet(self.state_prop)
        self.dialog_set.add(TextPrompt("text_prompt"))
        self.dialog_set.add(WaterfallDialog("main_dialog", [self.GetLeaveType,self.GetStartDate,self.GetEndDate,self.completed]))
        self.sql_cursor = None
        self.llm_cursor = None
   
    async def GetLeaveType(self, waterfall_step: WaterfallStepContext):
        self.leave_info = []
        leave_options = SuggestedActions(
            actions=[
                CardAction(title="Vacation Leave", type=ActionTypes.im_back, value="Vacation Leave"),
                CardAction(title="Sick Leave", type=ActionTypes.im_back, value="Sick Leave"),
                CardAction(title="Service Incentive Leave", type=ActionTypes.im_back, value="Service Incentive Leave"),
                CardAction(title="Paternity Leave", type=ActionTypes.im_back, value="Paternity Leave"),
            ]
        )

        # Follow-up text with suggested actions
        leave_response = MessageFactory.text("Please enter the type of leave:")
        leave_response.suggested_actions = leave_options

        # Sending the follow-up message
        return await waterfall_step.context.send_activity(leave_response)
        # return await waterfall_step.prompt("text_prompt",PromptOptions(prompt=MessageFactory.text("Please enter the type of leave:")))
    
    async def GetStartDate(self, waterfall_step: WaterfallStepContext):
        self.leave_info.append(waterfall_step._turn_context.activity.text)
        return await waterfall_step.prompt("text_prompt",PromptOptions(prompt=MessageFactory.text("Please enter leave start date: (dd-mm-yyyy)")))

    async def GetEndDate(self, waterfall_step: WaterfallStepContext):
        self.leave_info.append(waterfall_step._turn_context.activity.text)
        return await waterfall_step.prompt("text_prompt",PromptOptions(prompt=MessageFactory.text("Please enter leave end date: (dd-mm-yyyy)")))

    async def completed(self, waterfall_step: WaterfallStepContext): 
        self.leave_info.append(waterfall_step._turn_context.activity.text)
        #self.leave_info)
        updated_leave_text = f'Below are your leave application details: \n\nLeave type: {self.leave_info[0]} \n\n Start date: {self.leave_info[1]} \n\n End date: {self.leave_info[2]} \n\n Thank you for the update. Approval for leave requests is subject to manager authorization. Kindly monitor your email for the status of your leave request.'
        await waterfall_step.context.send_activity(MessageFactory.text(updated_leave_text))
        follow_up_actions = SuggestedActions(
                            actions=[
                                CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
                                CardAction(title="No", type=ActionTypes.im_back, value="No"),
                                # Add more follow-up actions as needed
                            ]
                        )
        follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
        follow_up_response.suggested_actions = follow_up_actions
        await waterfall_step.end_dialog()
        return await waterfall_step.context.send_activity(follow_up_response)
    
    async def on_message_activity(self, turn_context: TurnContext):
        if self.sql_cursor == None:
            self.sql_cursor = get_sql_connection_string()
        else: 
            pass
        
        if self.llm_cursor == None: 
            self.llm_cursor = get_llm_connection_string()
        else: 
            pass

        current_state = turn_context.turn_state.get('current_state')
        dialog_context = await self.dialog_set.create_context(turn_context)
        if (dialog_context.active_dialog is not None):
            await dialog_context.continue_dialog()
        else:
            #"Debug: First Else after dialog_context")
            question = turn_context.activity.text
            answer = custom_QandA(question)
            custom_QandA_Confidence = answer.confidence
            print('custom qna conf:',custom_QandA_Confidence)
            lower_question = question.lower()
            if custom_QandA_Confidence > 0.7:
                #"Debug: custom_qna entered")
                # Check for specific user input to provide suggested actions
                if  lower_question == "about organization":
                    #"Go")
                    #"1")
                    turn_context.turn_state['current_state'] = "about_organization"
                    self.current_state = turn_context.turn_state['current_state']
                    current_state = turn_context.turn_state['current_state']
                    #self.current_state)
                    org_available_actions = SuggestedActions(
                        actions=[
                            CardAction(title="Services", type=ActionTypes.im_back, value="Services"),
                            CardAction(title="Contact us", type=ActionTypes.im_back, value="Contact us"),
                            CardAction(title="Locations", type=ActionTypes.im_back, value="Locations"),
                            CardAction(title="Clients", type=ActionTypes.im_back, value="Clients"),
                            CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu")
                        ]
                    )
                    
                    aboutorganization_response_activity = MessageFactory.text("What else would you like to know about Guardsman?")
                    aboutorganization_response_activity.suggested_actions = org_available_actions
                    await turn_context.send_activity(answer.answer)
                    await turn_context.send_activity(aboutorganization_response_activity)

                    
                elif lower_question == "leave policies":
                    #"2")

                    turn_context.turn_state['current_state'] = "leave management"
                    self.current_state = turn_context.turn_state['current_state']
                    #self.current_state)
                    LP_actions = SuggestedActions(
                        actions=[                    
                            CardAction(title="Vacation Leave", type=ActionTypes.im_back, value="Vacation Leave"),
                            CardAction(title="Sick Leave", type=ActionTypes.im_back, value="Sick Leave"),
                            CardAction(title="Service Incentive Leave", type=ActionTypes.im_back,
                                        value="Service Incentive Leave"),
                            CardAction(title="Paternity Leave", type=ActionTypes.im_back, value="Paternity Leave"),
                            CardAction(title="Go back to previous menu", type=ActionTypes.im_back, value="Go back to previous menu"),
                            CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu"),
                        ]
                    )
                    Lp_response_activity = MessageFactory.text('Kindly choose the category of leave policy information you are seeking:')
                    Lp_response_activity.suggested_actions = LP_actions
                    await turn_context.send_activity(Lp_response_activity)
                
                elif lower_question == "profile details":
                    turn_context.turn_state['current_state'] = "profile details"
                    self.current_state = turn_context.turn_state['current_state']     
                    LM_actions = SuggestedActions(
                    actions=[
                        CardAction(title="View My Info", type=ActionTypes.im_back, value="View My Info"),
                        CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu"),
                    ]
                    )
                    LM_response_activity = MessageFactory.text("How may I assist you with your profile details?")
                    LM_response_activity.suggested_actions = LM_actions
                    await turn_context.send_activity(LM_response_activity)                
                    
                elif  lower_question == "leave management" :
                    #"3")
                    turn_context.turn_state['current_state'] = "leave management"
                    self.current_state = turn_context.turn_state['current_state']     
                    LM_actions = SuggestedActions(
                    actions=[
                        CardAction(title="Check My Leave Balances", type=ActionTypes.im_back, value="Check My Leave Balances"),
                        CardAction(title="Apply Leave", type=ActionTypes.im_back, value="Apply Leave"),
                        CardAction(title="Leave Policies", type=ActionTypes.im_back, value="Leave Policies"),
                        CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu"),
                    ]
                    )
                    LM_response_activity = MessageFactory.text("How may I assist you with your leave management needs?")
                    LM_response_activity.suggested_actions = LM_actions
                    await turn_context.send_activity(LM_response_activity)

                elif lower_question == "payroll details":
                    #"4")
                    turn_context.turn_state['current_state'] = "payroll details"
                    self.current_state = turn_context.turn_state['current_state']
                    payroll_available_actions = SuggestedActions(
                        actions=[
                            CardAction(title="View My Pay Slip", type=ActionTypes.im_back, value="View My Pay Slip"),
                            CardAction(title="Payroll Policies", type=ActionTypes.im_back, value="Payroll Policies"),
                            CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu"),
                            
                        ]
                    )
                    payroll_response_activity = MessageFactory.text("Would you prefer to inquire about  payroll details or access your recent payslips?")
                    payroll_response_activity.suggested_actions = payroll_available_actions
                    await turn_context.send_activity(payroll_response_activity)

                elif lower_question == 'yes':
                    #"5")
                    #'--------------------------------------------------')
                    if self.outer_state == 'unknown_int':
                        yes_suggested_actions = SuggestedActions(
                            actions=[
                                CardAction(title="Go back to previous menu", type=ActionTypes.im_back, value="Go back to previous menu"),
                                # CardAction(title="Enter your query", type=ActionTypes.im_back, value = "Enter your query"),
                                CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu")
                            ]
                        )
                        yes_response_activity = MessageFactory.text("Kindly input your query, or choose from the provided options below:")
                        #'#'*75)
                        #'What else statement is done')
                        yes_response_activity.suggested_actions = yes_suggested_actions
                        await turn_context.send_activity(yes_response_activity)
                    
                    elif self.outer_state == "profile details" : 
                        yes_suggested_actions = SuggestedActions(
                            actions=[
                            
                                CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu")
                            ]
                        )
                        yes_response_activity = MessageFactory.text("Please type your query or select from the options below")
                        #'#'*75)
                        #'What else statement is done')
                        yes_response_activity.suggested_actions = yes_suggested_actions
                        await turn_context.send_activity(yes_response_activity)                    

                        
                    else:
                        yes_suggested_actions = SuggestedActions(
                            actions=[
                                CardAction(title="Go back to previous menu", type=ActionTypes.im_back, value="Go back to previous menu"),
                                # CardAction(title="I have another query", type=ActionTypes.im_back, value="I have another query"),
                                CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu")
                            ]
                        )
                        # yes_response_activity = MessageFactory.text("What else can I assist you with?")
                        yes_response_activity = MessageFactory.text("Please type your query or select from the options below")
                        #'#'*75)
                        #'What else statement is done')
                        yes_response_activity.suggested_actions = yes_suggested_actions
                        await turn_context.send_activity(yes_response_activity)

                
                elif lower_question == 'no':
                    await turn_context.send_activity(answer.answer)
                    #"in payroll plicies")

                elif lower_question == 'thankyou':
                    #"6")
                    await turn_context.send_activity(answer.answer)

                elif lower_question == "go back to previous menu":
                    #self.current_state,"in this go back")
                
                    if self.current_state == "about_organization":
                            #current_state, 'none state of current')
                            org_available_actions = SuggestedActions(
                                actions=[
                                    CardAction(title="Services", type=ActionTypes.im_back, value="Services"),
                                    CardAction(title="Contact us", type=ActionTypes.im_back, value="Contact us"),
                                    CardAction(title="Locations", type=ActionTypes.im_back, value="Locations"),
                                    CardAction(title="Clients", type=ActionTypes.im_back, value="Clients"),
                                    CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu"),
                                    
                                    
                                ]
                            )
                            aboutorganization_response_activity = MessageFactory.text("What else would you like to know about Guardsman?")
                            aboutorganization_response_activity.suggested_actions = org_available_actions
                            await turn_context.send_activity(aboutorganization_response_activity)

                    elif self.current_state == "profile details":
                            LP_actions = SuggestedActions(
                                actions=[                    
                                    CardAction(title="View My Info", type=ActionTypes.im_back, value="View My Info"),
                                    CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu"),
                                    
                                ]
                            )
                            Lp_response_activity = MessageFactory.text('How may I assist you with your profile details?')
                            Lp_response_activity.suggested_actions = LP_actions
                            await turn_context.send_activity(Lp_response_activity)

                    elif self.current_state == "leave policies":
                            LP_actions = SuggestedActions(
                                actions=[                    
                                    CardAction(title="Vacation Leave", type=ActionTypes.im_back, value="Vacation Leave"),
                                    CardAction(title="Sick Leave", type=ActionTypes.im_back, value="Sick Leave"),
                                    CardAction(title="Service Incentive Leave", type=ActionTypes.im_back,
                                                value="Service Incentive Leave"),
                                    CardAction(title="Paternity Leave", type=ActionTypes.im_back, value="Paternity Leave"),
                                    CardAction(title="Go back to previous menu", type=ActionTypes.im_back, value="Go back to previous menu"),
                                    CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu"),
                                    
                                ]
                            )
                            Lp_response_activity = MessageFactory.text('What else would you like to know about Leave Policies?')
                            Lp_response_activity.suggested_actions = LP_actions
                            await turn_context.send_activity(Lp_response_activity)

                    elif self.current_state == "leave management":
                        LM_actions = SuggestedActions(
                                actions=[
                                    CardAction(title="Check My Leave Balances", type=ActionTypes.im_back, value="Check My Leave Balances"),
                                    CardAction(title="Apply Leave", type=ActionTypes.im_back, value="Apply Leave"),
                                    CardAction(title="Leave Policies", type=ActionTypes.im_back, value="Leave Policies"),
                                    CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu"),
                                    
                                ]
                            )
                        LM_response_activity = MessageFactory.text("How may I assist you with your leave management needs?")
                        LM_response_activity.suggested_actions = LM_actions
                        await turn_context.send_activity(LM_response_activity)

                    elif self.current_state == "payroll details":
                        payroll_available_actions = SuggestedActions(
                            actions=[
                                CardAction(title="View My Pay Slip", type=ActionTypes.im_back, value="View My Pay Slip"),
                                CardAction(title="Payroll Policies", type=ActionTypes.im_back, value="Payroll Policies"),
                                CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu"),
                                
                            ]
                        )
                        payroll_response_activity = MessageFactory.text("Would you prefer to inquire about  payroll details or access your recent payslips?")
                        payroll_response_activity.suggested_actions = payroll_available_actions
                        await turn_context.send_activity(payroll_response_activity)
                    
                    elif self.current_state == "UpcomingWeek":
                        GWH_available_actions = SuggestedActions(
                        actions=[
                            CardAction(title="Last Week Working  Hours", type=ActionTypes.im_back, value="Last Week Working  Hours"),
                            CardAction(title="Next Week Working Hours", type=ActionTypes.im_back, value="Next Week Working Hours"),
                            CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu"),
                        ]
                    )
                        GWH_response_activity = MessageFactory.text("Please choose from available options")
                        GWH_response_activity.suggested_actions = GWH_available_actions
                        await turn_context.send_activity(GWH_response_activity)

                    elif self.current_state == "PreviousWeek":
                        GWH_available_actions = SuggestedActions(
                        actions=[
                            CardAction(title="Last Week Working  Hours", type=ActionTypes.im_back, value="Last Week Working  Hours"),
                            CardAction(title="Next Week Working Hours", type=ActionTypes.im_back, value="Next Week Working Hours"),
                            CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu"),
                        ]
                    )
                        GWH_response_activity = MessageFactory.text("Please choose from available options")
                        GWH_response_activity.suggested_actions = GWH_available_actions
                        await turn_context.send_activity(GWH_response_activity)

                elif lower_question == "i have another query":
                    if self.current_state == "about_organization":
                            #"about_organization")
                            org_available_actions = SuggestedActions(
                                actions=[
                                    CardAction(title="Services", type=ActionTypes.im_back, value="Services"),
                                    CardAction(title="Contact us", type=ActionTypes.im_back, value="Contact us"),
                                    CardAction(title="Locations", type=ActionTypes.im_back, value="Locations"),
                                    CardAction(title="Clients", type=ActionTypes.im_back, value="Clients"),
                                    CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu"),
                                    
                                    
                                ]
                            )
                            aboutorganization_response_activity = MessageFactory.text("What else would you like to know about Guardsman?")
                            aboutorganization_response_activity.suggested_actions = org_available_actions
                            await turn_context.send_activity(aboutorganization_response_activity)

                    elif self.current_state == "leave policies":
                            #"leave policies")
                            LP_actions = SuggestedActions(
                                actions=[                    
                                    CardAction(title="Vacation Leave", type=ActionTypes.im_back, value="Vacation Leave"),
                                    CardAction(title="Sick Leave", type=ActionTypes.im_back, value="Sick Leave"),
                                    CardAction(title="Service Incentive Leave", type=ActionTypes.im_back,
                                                value="Service Incentive Leave"),
                                    CardAction(title="Paternity Leave", type=ActionTypes.im_back, value="Paternity Leave"),
                                    CardAction(title="Go back to previous menu", type=ActionTypes.im_back, value="Go back to previous menu"),
                                    CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu"),
                                    
                                ]
                            )
                            Lp_response_activity = MessageFactory.text('What else would you like to know about Leave Policies?')
                            Lp_response_activity.suggested_actions = LP_actions
                            await turn_context.send_activity(Lp_response_activity)

                    elif self.current_state == "leave management":
                        #"leave management")
                        LM_actions = SuggestedActions(
                                actions=[
                                    CardAction(title="Check My Leave Balances", type=ActionTypes.im_back, value="Check My Leave Balances"),
                                    CardAction(title="Apply Leave", type=ActionTypes.im_back, value="Apply Leave"),
                                    CardAction(title="Leave Policies", type=ActionTypes.im_back, value="Leave Policies"),
                                    CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu"),
                                    
                                ]
                            )
                        LM_response_activity = MessageFactory.text("How may I assist you with your leave management needs?")
                        LM_response_activity.suggested_actions = LM_actions
                        await turn_context.send_activity(LM_response_activity)

                    elif self.current_state == "payroll details":
                        #"payroll details")
                        payroll_available_actions = SuggestedActions(
                            actions=[
                                CardAction(title="View My Pay Slip", type=ActionTypes.im_back, value="View My Pay Slip"),
                                CardAction(title="Payroll Policies", type=ActionTypes.im_back, value="Payroll Policies"),
                                CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu"),
                                
                            ]
                        )
                        payroll_response_activity = MessageFactory.text("Would you prefer to inquire about  payroll details or access your recent payslips?")
                        payroll_response_activity.suggested_actions = payroll_available_actions
                        await turn_context.send_activity(payroll_response_activity)
                    
                    elif self.current_state == "UpcomingWeek":
                        #"UpcomingWeek")
                        GWH_available_actions = SuggestedActions(
                        actions=[
                            CardAction(title="Last Week Working  Hours", type=ActionTypes.im_back, value="Last Week Working  Hours"),
                            CardAction(title="Next Week Working Hours", type=ActionTypes.im_back, value="Next Week Working Hours"),
                            CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu"),
                        ]
                    )
                        GWH_response_activity = MessageFactory.text("Please choose from available options")
                        GWH_response_activity.suggested_actions = GWH_available_actions
                        await turn_context.send_activity(GWH_response_activity)

                    elif self.current_state == "PreviousWeek":
                        #"PreviousWeek")
                        GWH_available_actions = SuggestedActions(
                        actions=[
                            CardAction(title="Last Week Working  Hours", type=ActionTypes.im_back, value="Last Week Working  Hours"),
                            CardAction(title="Next Week Working Hours", type=ActionTypes.im_back, value="Next Week Working Hours"),
                            CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu"),
                        ]
                    )
                        GWH_response_activity = MessageFactory.text("Please choose from available options")
                        GWH_response_activity.suggested_actions = GWH_available_actions
                        await turn_context.send_activity(GWH_response_activity)
                    

                

                
                elif lower_question == 'hi':
                    #"9")

                    hi_suggested_actions = SuggestedActions(
                        actions=[
                            CardAction(title="Profile Details", type=ActionTypes.im_back, value="Profile Details"),
                            CardAction(title="Leave Management", type=ActionTypes.im_back, value="Leave Management"),
                            CardAction(title="Get Working Hours", type=ActionTypes.im_back, value="Get Working Hours"),
                            CardAction(title="Payroll Details", type=ActionTypes.im_back, value="Payroll Details"),
                            CardAction(title="About Organization", type=ActionTypes.im_back, value="About Organization")
                        ]
                    )
                    hi_response_activity = MessageFactory.text("What can I assist you with?")
                    hi_response_activity.suggested_actions = hi_suggested_actions
                    await turn_context.send_activity(hi_response_activity)

                elif  lower_question == "return to the main menu":
                    #"10")
                    print("in leave management")
                    # print(confidence_best_intent)
                    main_menu_actions = SuggestedActions(
                        actions=[
                            CardAction(title="Profile Details", type=ActionTypes.im_back, value="Profile Details"),
                            CardAction(title="Leave Management", type=ActionTypes.im_back, value="Leave Management"),
                            CardAction(title="Get Working Hours", type=ActionTypes.im_back, value="Get Working Hours"),
                            CardAction(title="Payroll Details", type=ActionTypes.im_back, value="Payroll Details"),
                            CardAction(title="About Organization", type=ActionTypes.im_back, value="About Organization")
                        ]
                    )
                    main_menu_response_activity = MessageFactory.text("Choose an option from the  Main Menu:")
                    main_menu_response_activity.suggested_actions = main_menu_actions
                    await turn_context.send_activity(main_menu_response_activity)


        
                else:
                    #"11")
                    # print(lower_question)
                    # print(self.current_state)
                    if answer.answer == "Thanks for interacting! If you need anything else, just type 'Hi' Have a great day!":
                        await turn_context.send_activity(answer.answer)
                        #"inthis particular")
                    else:
                        #"in else payroll policies")

                        await turn_context.send_activity(answer.answer)
                        #"in this else")

                        # Provide follow-up suggested actions
                        follow_up_actions = SuggestedActions(
                            actions=[
                                CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
                                CardAction(title="No", type=ActionTypes.im_back, value="No"),
                                # Add more follow-up actions as needed
                            ]
                        )
                        follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                        follow_up_response.suggested_actions = follow_up_actions
                        await turn_context.send_activity(follow_up_response)
                self.outer_state = 'customqna'
            

            else:
                #'-'*75)
                #"Debug: CLU else statement")
                # Handling intents from CLU
                output_from_clu = answers_from_clu(question)
                best_intent, confidence_best_intent = clu_get_intent(output_from_clu)

                print(f'**************** \n\n Debug: \n\n Best Intent - {best_intent} \n\n Confidence - {confidence_best_intent[0]} \n\n****************')
                if lower_question == 'enter your query':
                    follow_up_response = MessageFactory.text("Please enter your query below:")
                    await turn_context.send_activity(follow_up_response)

                elif confidence_best_intent.values[0] > 0.7:

                    if best_intent == "GetPaySlip":
                        # conn_string = get_connection_string()
                        # sql_connection = pyodbc.connect(conn_string)
                        # sql_cursor = sql_connection.cursor()
    
                        pay_slips_query = 'SELECT * FROM payslips WHERE EmployeeName = ?;'
                        self.sql_cursor.execute(pay_slips_query, username)
                        payslip_data = self.sql_cursor.fetchone()
                        response_activity = MessageFactory.text(f'Your current payslip is:')
                        # await turn_context.send_activity(response_activity)
                        if payslip_data:
                            # Assuming the columns in payslips table are in the order of: EmployeeName, Salary, Deductions, NetPay
                            employeename,employeeid ,salary, deductions, net_pay = payslip_data

                            # Create a Hero Card to display payslip information
                            payslip_hero_card = HeroCard(
                                                        title="Payslip",
                                                        text=(
                                                            f"**Employee:** {employeename}\n\n "
                                                            f"**EmployeeID:** {employeeid}\n\n "
                                                            f"**Salary:** {salary}\n\n"
                                                            f"**Deductions:** {deductions}\n\n"
                                                            f"**Net Pay:** {net_pay}"
                                                        ))


                            # Send the Hero Card as an attachment
                            response_activity = MessageFactory.attachment(CardFactory.hero_card(payslip_hero_card))
                            await turn_context.send_activity(response_activity)
                            follow_up_actions = SuggestedActions(
                                actions=[
                                    CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
                                    CardAction(title="No", type=ActionTypes.im_back, value="No"),
                                    # Add more follow-up actions as needed
                                ]
                            )
                            follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                            follow_up_response.suggested_actions = follow_up_actions
                            await turn_context.send_activity(follow_up_response)
                        else:
                            response_activity = MessageFactory.text("No payslip found for the specified user.")
                            await turn_context.send_activity(response_activity)
                            follow_up_actions = SuggestedActions(
                                actions=[
                                    CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
                                    CardAction(title="No", type=ActionTypes.im_back, value="No"),
                                    # Add more follow-up actions as needed
                                ]
                            )
                            follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                            follow_up_response.suggested_actions = follow_up_actions
                            await turn_context.send_activity(follow_up_response)

                    
                    elif best_intent == "GetEmployeeInfo":
                        turn_context.turn_state['current_state'] = "profile details"
                        self.current_state = turn_context.turn_state['current_state']
                        # print(self.current_state)
                        # self.outer_state = "profile details"
                        sql_cursor = get_sql_connection_string()
                        # sql_connection = pyodbc.connect(conn_string)
                        # sql_cursor = sql_connection.cursor()
    
                        EL_info_query = 'SELECT * FROM EmployeeInformation WHERE EmployeeName = ?;'
                        sql_cursor.execute(EL_info_query, username)
                        EL_info = sql_cursor.fetchone()
                        if EL_info:
                            # Assuming the columns in employee table are in the order of: EmployeeID, EmployeeName, Age, Gender, Contact, Email, Address, Designation, EmploymentType
                            employee_id, employee_name, age, gender, contact, email, address, department, employment_type = EL_info

                            # Create a Hero Card to display employee information
                            EL_info_hero_card = HeroCard(
                                title="Employee Information",
                                text=(
                                    f"**Employee ID:** {employee_id}\n\n"
                                    f"**Employee Name:** {employee_name}\n\n"
                                    f"**Age:** {age}\n\n"
                                    f"**Gender:** {gender}\n\n"
                                    f"**Contact:** {contact}\n\n"
                                    f"**Email:** {email}\n\n"
                                    f"**Address:** {address}\n\n"
                                    f"**Department:** {department}\n\n"
                                    f"**Employment Type:** {employment_type}"
                                )
                            )

                            # Send the Hero Card as an attachment
                            response_activity = MessageFactory.attachment(CardFactory.hero_card(EL_info_hero_card))
                            await turn_context.send_activity(response_activity)

                            follow_up_actions = SuggestedActions(
                                actions=[
                                    CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
                                    CardAction(title="No", type=ActionTypes.im_back, value="No"),
                                    # Add more follow-up actions as needed
                                ]
                            )

                            follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                            follow_up_response.suggested_actions = follow_up_actions
                            await turn_context.send_activity(follow_up_response)

                    
                    elif best_intent == "CheckLeaveBalances":
                        #"Debug: Check Leave Balances")

                        turn_context.turn_state['current_state'] = "leave management"
                        self.current_state = turn_context.turn_state['current_state']
                        # conn_string = get_connection_string()
                        # sql_connection = pyodbc.connect(conn_string)
                        # sql_cursor = sql_connection.cursor()
    
                        EL_query = 'SELECT * FROM EmployeeLeave WHERE EmployeeName = ?;'
                        self.sql_cursor.execute(EL_query, username)
                        EL_data = self.sql_cursor.fetchone()
                        response_activity = MessageFactory.text(f'Your current Leave balanaces and upcoming leaves are:')
                        # await turn_context.send_activity(response_activity)
                        if EL_data:
                            # Assuming the columns in payslips table are in the order of: EmployeeName, Salary, Deductions, NetPay
                            employeename,employeeid ,SickLeave, PrivilegeLeave,  PaternityLeave,UpcomingThreeLeaves,  Year = EL_data

                            # Create a Hero Card to display payslip information
                            EL_hero_card = HeroCard(
                                            title="Leave Balances and Upcoming Leaves",
                                            text=(
                                                f"**Employee:** {employeename}\n\n"
                                                f"**EmployeeID:** {employeeid}\n\n"
                                                f"**SickLeave:** {SickLeave}\n\n"
                                                f"**PrivilegeLeave:** {PrivilegeLeave}\n\n"
                                                f"**PaternityLeave:** {PaternityLeave}\n\n"
                                                f"**UpcomingThreeLeaves:** {UpcomingThreeLeaves}\n\n"
                                                f"**Year:** {Year}"
                                            )
                                        )


                            # Send the Hero Card as an attachment
                            response_activity = MessageFactory.attachment(CardFactory.hero_card(EL_hero_card))
                            await turn_context.send_activity(response_activity)
                            follow_up_actions = SuggestedActions(
                                actions=[
                                    CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
                                    CardAction(title="No", type=ActionTypes.im_back, value="No"),
                                    # Add more follow-up actions as needed
                                ]
                            )
                            follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                            follow_up_response.suggested_actions = follow_up_actions
                            await turn_context.send_activity(follow_up_response)

                    elif best_intent == 'ApplyLeave':
                        turn_context.turn_state['current_state'] = "leave management"
                        self.current_state = turn_context.turn_state['current_state']
                        
                        if (dialog_context.active_dialog is not None):
                            await dialog_context.continue_dialog()
                        else:
                            await dialog_context.begin_dialog("main_dialog")
                        
                    elif best_intent == "GetWorkingHours":
                        response = output_from_clu["result"]["prediction"]  

                        entity = response['entities']
                        if len(entity) == 0: 
                            GWH_available_actions = SuggestedActions(
                            actions=[
                                CardAction(title="Last Week Working  Hours", type=ActionTypes.im_back, value="Last Week Working  Hours"),
                                CardAction(title="Next Week Working Hours", type=ActionTypes.im_back, value="Next Week Working Hours"),
                                CardAction(title="Return to the main menu", type=ActionTypes.im_back, value="Return to the main menu"),
                            ]
                        )
                            GWH_response_activity = MessageFactory.text("Please choose from available options")
                            GWH_response_activity.suggested_actions = GWH_available_actions
                            await turn_context.send_activity(GWH_response_activity)
                        

                        
                        else: 
                                
                            response = output_from_clu["result"]["prediction"]  
                           
                            entity = response['entities'][0]['category']
                            # conn_string = get_connection_string()
                            # sql_connection = pyodbc.connect(conn_string)
                            # sql_cursor = sql_connection.cursor()

                            if entity == 'PreviousWeek':
                                turn_context.turn_state['current_state'] = "PreviousWeek"
                                self.current_state = turn_context.turn_state['current_state']
                                prev_week_query = "SELECT EmployeeName, Date, Day, ActualStartTime, ActualEndTime FROM EmployeeSchedule WHERE ActualStartTime IS NOT NULL AND EmployeeName = ?;"
                                self.sql_cursor.execute(prev_week_query, username)
                                prev_week_data = self.sql_cursor.fetchall()

                                response_activity = MessageFactory.text(f'Your Last Week working Hours info:')
                                #'^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^', list(prev_week_data))

                                output_prev_week = convert_dates(prev_week_data)
                        
                                data_for_adaptive_card = [
                                    {
                                        # "EmployeeName": row[0],
                                        "Date": str(row[1]),
                                        "Day": row[2],
                                        "ActualStartTime": row[3],
                                        "ActualEndTime": row[4],
                                    }
                                    for row in output_prev_week
                                ]

                                # Creating Adaptive Card
                                adaptive_card = {
                                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                                    "type": "AdaptiveCard",
                                    "version": "1.0",
                                    "body": [
                                        {
                                            "type": "TextBlock",
                                            "text": "Previous Week Actual Working Hours"+ f"\n\nEmployeeName : {username}",
                                            "weight": "bolder",
                                            "size": "medium"
                                        },
                                        {
                                            "type": "ColumnSet",
                                            "columns": [
                                                # {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": "EmployeeName"}] + [{"type": "TextBlock", "text": data["EmployeeName"]} for data in data_for_adaptive_card]},
                                                {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": "Date"}] + [{"type": "TextBlock", "text": data["Date"]} for data in data_for_adaptive_card]},
                                                {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": "Day"}] + [{"type": "TextBlock", "text": data["Day"]} for data in data_for_adaptive_card]},
                                                {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": "ActualStartTime"}] + [{"type": "TextBlock", "text": data["ActualStartTime"]} for data in data_for_adaptive_card]},
                                                {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": "ActualEndTime"}] + [{"type": "TextBlock", "text": data["ActualEndTime"]} for data in data_for_adaptive_card]},
                                            ]
                                        }
                                    ]
                                }

                                # Sending the Adaptive Card
                                response_activity = MessageFactory.attachment(CardFactory.adaptive_card(adaptive_card))
                                await turn_context.send_activity(response_activity)

                                # Suggested Actions
                                follow_up_actions = SuggestedActions(
                                    actions=[
                                        CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
                                        CardAction(title="No", type=ActionTypes.im_back, value="No"),
                                        # Add more follow-up actions as needed
                                    ]
                                )

                                # Follow-up text with suggested actions
                                follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                                follow_up_response.suggested_actions = follow_up_actions

                                # Sending the follow-up message
                                await turn_context.send_activity(follow_up_response)

                            elif entity == 'UpcomingWeek':
                                turn_context.turn_state['current_state'] = "UpcomingWeek"
                                self.current_state = turn_context.turn_state['current_state']
                                next_week_query = "SELECT EmployeeName,Date, Day, ScheduledStartTime, ScheduledEndTime FROM EmployeeSchedule WHERE ActualStartTime IS NULL AND EmployeeName = ?;"
                                self.sql_cursor.execute(next_week_query, username)
                                next_week_data = self.sql_cursor.fetchall()
                                response_activity = MessageFactory.text(f'Your Next Week working Hours info:')
                                #'^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^', list(next_week_data))

                                output_next_week = convert_dates(next_week_data)
                                #output_next_week)
                                data_for_adaptive_card = [
                                    {
                                        # "EmployeeName": row[0],
                                        "Date": str(row[1]),
                                        "Day": row[2],
                                        "ScheduledStartTime": row[3],
                                        "ScheduledEndTime": row[4],
                                    }
                                    for row in output_next_week
                                ]

                                # Creating Adaptive Card
                                adaptive_card = {
                                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                                    "type": "AdaptiveCard",
                                    "version": "1.0",
                                    "body": [
                                        {
                                            "type": "TextBlock",
                                            "text": "Next Week Scheduled Working Hours " + f"\n\nEmployeeName : {username}",
                                        
                                            "weight": "bolder",
                                            "size": "medium"
                                        },
                                        {
                                            "type": "ColumnSet",
                                            "columns": [
                                                # {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": data["EmployeeName"]} for data in data_for_adaptive_card]},
                                                {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": "Date"}] +[{"type": "TextBlock", "text": data["Date"]} for data in data_for_adaptive_card]},
                                                {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": "Day"}] + [{"type": "TextBlock", "text": data["Day"]} for data in data_for_adaptive_card]},
                                                {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": "ScheduledStartTime"}] + [{"type": "TextBlock", "text": data["ScheduledStartTime"]} for data in data_for_adaptive_card]},
                                                {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": "ScheduledEndTime"}] + [{"type": "TextBlock", "text": data["ScheduledEndTime"]} for data in data_for_adaptive_card]},
                                            ]
                                        }
                                    ]
                                }

                                # Sending the Adaptive Card
                                response_activity = MessageFactory.attachment(CardFactory.adaptive_card(adaptive_card))
                                await turn_context.send_activity(response_activity)

                                # Suggested Actions
                                follow_up_actions = SuggestedActions(
                                    actions=[
                                        CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
                                        CardAction(title="No", type=ActionTypes.im_back, value="No"),
                                        # Add more follow-up actions as needed
                                    ]
                                )

                                # Follow-up text with suggested actions
                                follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                                follow_up_response.suggested_actions = follow_up_actions

                                # Sending the follow-up message
                                await turn_context.send_activity(follow_up_response)

                
                else:
                    
                    #'Debug: Unkown Intent')
                    # file_path = r"Guardsman Group FAQ.docx"
                    # query_options = [file_path]
                    human_query = question
                    text_splitter=RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
                    # llm = AzureChatOpenAI(deployment_name='gpt-0301', temperature = 0)
                    llm = AzureOpenAI(azure_deployment="gpt-instruct",
                    azure_endpoint='https://tv-llm-applications.openai.azure.com/'
                    )
                    memory = ConversationBufferMemory(memory_key="chat_history", input_key = 'human_input')
                    employee = "Peter Jones"
                    response = pdf_query(query = human_query, text_splitter = text_splitter, llm = llm, query_options = ["Guardsman Group FAQ.docx"], memory = memory, llm_db = self.llm_cursor, employee = employee)
    
                    response_activity = MessageFactory.text(response)
        
                    await turn_context.send_activity(response_activity)   
                    follow_up_actions = SuggestedActions(
                        actions=[
                            CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
                            CardAction(title="No", type=ActionTypes.im_back, value="No"),
                            # Add more follow-up actions as needed
                        ]
                    )
                    follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                    follow_up_response.suggested_actions = follow_up_actions
                    self.outer_state='unknown_int'
                    await turn_context.send_activity(follow_up_response)
                              
        await self.con_state.save_changes(turn_context)
                           



    async def on_members_added_activity(
        self,
        members_added: ChannelAccount,
        turn_context: TurnContext
    ):
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id:
                welcome_message = "Hi, Welcome to Guardsman!\n\n What can I help you with today?"

                suggested_actions = SuggestedActions(
                    actions=[
                        CardAction(title="Profile Details", type=ActionTypes.im_back, value="Profile Details"),
                        CardAction(title="Leave Management", type=ActionTypes.im_back, value="Leave Management"),
                        CardAction(title="Get Working Hours", type=ActionTypes.im_back, value="Get Working Hours"),
                        CardAction(title="Payroll Details", type=ActionTypes.im_back, value="Payroll Details"),
                        CardAction(title="About Organization", type=ActionTypes.im_back, value="About Organization")
                    ]
                )
                # Greet new members
                response_activity = MessageFactory.text(welcome_message)
                response_activity.suggested_actions = suggested_actions
                await turn_context.send_activity(response_activity)


