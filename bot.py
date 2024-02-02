# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# from langchain.embeddings import OpenAIEmbeddings
# from langchain.chat_models.azure_openai import AzureChatOpenAI
from botbuilder.core import ActivityHandler, MessageFactory, TurnContext,CardFactory, ConversationState
from botbuilder.dialogs import DialogSet, WaterfallDialog, WaterfallStepContext
from botbuilder.dialogs.prompts import TextPrompt, NumberPrompt, PromptOptions
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.memory import ConversationBufferMemory
from langchain_openai.llms.azure import AzureOpenAI
from botbuilder.schema import ChannelAccount
from llm_backend_updated import pdf_query
from botbuilder.core import CardFactory
from cb_utils import *   
from cb_cards import * 
import os


os.environ['OPENAI_API_VERSION'] = '2023-12-01-preview'
os.environ['AZURE_OPENAI_API_KEY'] = 'e63ed695495543d58595fab4e27e4ff1'

#have to make this a parameter
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
        leave_options = leave_type_SA()
        leave_response = MessageFactory.text("Please enter the type of leave:")
        leave_response.suggested_actions = leave_options
        return await waterfall_step.context.send_activity(leave_response)
    
    async def GetStartDate(self, waterfall_step: WaterfallStepContext):
        self.leave_info.append(waterfall_step._turn_context.activity.text)
        return await waterfall_step.prompt("text_prompt",PromptOptions(prompt=MessageFactory.text("Please enter leave start date: (dd-mm-yyyy)")))

    async def GetEndDate(self, waterfall_step: WaterfallStepContext):
        self.leave_info.append(waterfall_step._turn_context.activity.text)
        return await waterfall_step.prompt("text_prompt",PromptOptions(prompt=MessageFactory.text("Please enter leave end date: (dd-mm-yyyy)")))

    async def completed(self, waterfall_step: WaterfallStepContext): 
        self.leave_info.append(waterfall_step._turn_context.activity.text)
        updated_leave_text = f'Below are your leave application details: \n\nLeave type: {self.leave_info[0]} \n\n Start date: {self.leave_info[1]} \n\n End date: {self.leave_info[2]} \n\n Thank you for the update. Approval for leave requests is subject to manager authorization. Kindly monitor your email for the status of your leave request.'
        await waterfall_step.context.send_activity(MessageFactory.text(updated_leave_text))
        follow_up_actions = follow_up_action_card()
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
            question = turn_context.activity.text
            answer = custom_QandA(question)
            custom_QandA_Confidence = answer.confidence
            print('custom qna conf:',custom_QandA_Confidence)
            lower_question = question.lower()
            
            if custom_QandA_Confidence > 0.7:
            
                if  lower_question == "about organization":
                    turn_context.turn_state['current_state'] = "about_organization"
                    self.current_state = turn_context.turn_state['current_state']
                    current_state = turn_context.turn_state['current_state']
                    org_available_actions = org_available_action_card()
                    aboutorganization_response_activity = MessageFactory.text("What else would you like to know about Guardsman?")
                    aboutorganization_response_activity.suggested_actions = org_available_actions
                    await turn_context.send_activity(answer.answer)
                    await turn_context.send_activity(aboutorganization_response_activity)
                    
                elif lower_question == "leave policies":
                    turn_context.turn_state['current_state'] = "leave management"
                    self.current_state = turn_context.turn_state['current_state']
                    leave_policies_actions = leave_policies_action_card()
                    Lp_response_activity = MessageFactory.text('Kindly choose the category of leave policy information you are seeking:')
                    Lp_response_activity.suggested_actions = leave_policies_actions
                    await turn_context.send_activity(Lp_response_activity)
                
                elif lower_question == "profile details":
                    turn_context.turn_state['current_state'] = "profile details"
                    self.current_state = turn_context.turn_state['current_state']     
                    profile_details_actions = profile_details_action_card()
                    LM_response_activity = MessageFactory.text("How may I assist you with your profile details?")
                    LM_response_activity.suggested_actions = profile_details_actions
                    await turn_context.send_activity(LM_response_activity)                
                    
                elif  lower_question == "leave management" :
                    turn_context.turn_state['current_state'] = "leave management"
                    self.current_state = turn_context.turn_state['current_state']     
                    LM_actions = leave_management_action_card()
                    LM_response_activity = MessageFactory.text("How may I assist you with your leave management needs?")
                    LM_response_activity.suggested_actions = LM_actions
                    await turn_context.send_activity(LM_response_activity)

                elif lower_question == "payroll details":
                    turn_context.turn_state['current_state'] = "payroll details"
                    self.current_state = turn_context.turn_state['current_state']
                    payroll_available_actions = payroll_details_action_card()
                    payroll_response_activity = MessageFactory.text("Would you prefer to inquire about  payroll details or access your recent payslips?")
                    payroll_response_activity.suggested_actions = payroll_available_actions
                    await turn_context.send_activity(payroll_response_activity)

                elif lower_question == 'yes':
                    if self.outer_state == 'unknown_int':
                        yes_suggested_actions = prev_menu_main_menu_action_card()
                        yes_response_activity = MessageFactory.text("Kindly input your query, or choose from the provided options below:")
                        yes_response_activity.suggested_actions = yes_suggested_actions
                        await turn_context.send_activity(yes_response_activity)
                    
                    elif self.outer_state == "profile details" : 
                        yes_suggested_actions = return_to_main_menu_action_card()
                        yes_response_activity = MessageFactory.text("Please type your query or select from the options below")
                        yes_response_activity.suggested_actions = yes_suggested_actions
                        await turn_context.send_activity(yes_response_activity)                    

                    else:
                        yes_suggested_actions = prev_menu_main_menu_action_card()
                        yes_response_activity = MessageFactory.text("Please type your query or select from the options below")
                        yes_response_activity.suggested_actions = yes_suggested_actions
                        await turn_context.send_activity(yes_response_activity)
                
                elif lower_question == 'no':
                    await turn_context.send_activity(answer.answer)

                elif lower_question == 'thankyou':
                    await turn_context.send_activity(answer.answer)

                elif lower_question == "go back to previous menu":
                
                    if self.current_state == "about_organization":
                        org_available_actions = org_available_action_card()
                        aboutorganization_response_activity = MessageFactory.text("What else would you like to know about Guardsman?")
                        aboutorganization_response_activity.suggested_actions = org_available_actions
                        await turn_context.send_activity(aboutorganization_response_activity)

                    elif self.current_state == "profile details":
                        profile_details_actions = profile_details_action_card()
                        Lp_response_activity = MessageFactory.text('How may I assist you with your profile details?')
                        Lp_response_activity.suggested_actions = profile_details_actions
                        await turn_context.send_activity(Lp_response_activity)

                    elif self.current_state == "leave policies":
                        leave_policies_actions = leave_policies_action_card()
                        Lp_response_activity = MessageFactory.text('What else would you like to know about Leave Policies?')
                        Lp_response_activity.suggested_actions = leave_policies_actions
                        await turn_context.send_activity(Lp_response_activity)

                    elif self.current_state == "leave management":
                        LM_actions = leave_management_action_card()
                        LM_response_activity = MessageFactory.text("How may I assist you with your leave management needs?")
                        LM_response_activity.suggested_actions = LM_actions
                        await turn_context.send_activity(LM_response_activity)

                    elif self.current_state == "payroll details":
                        payroll_available_actions = payroll_details_action_card()
                        payroll_response_activity = MessageFactory.text("Would you prefer to inquire about  payroll details or access your recent payslips?")
                        payroll_response_activity.suggested_actions = payroll_available_actions
                        await turn_context.send_activity(payroll_response_activity)
                    
                    elif self.current_state == "UpcomingWeek":
                        GWH_available_actions = working_hours_action_card()
                        GWH_response_activity = MessageFactory.text("Please choose from available options")
                        GWH_response_activity.suggested_actions = GWH_available_actions
                        await turn_context.send_activity(GWH_response_activity)

                    elif self.current_state == "PreviousWeek":
                        GWH_available_actions = working_hours_action_card()
                        GWH_response_activity = MessageFactory.text("Please choose from available options")
                        GWH_response_activity.suggested_actions = GWH_available_actions
                        await turn_context.send_activity(GWH_response_activity)

                elif lower_question == "i have another query":
                    if self.current_state == "about_organization":
                        org_available_actions = org_available_action_card()
                        aboutorganization_response_activity = MessageFactory.text("What else would you like to know about Guardsman?")
                        aboutorganization_response_activity.suggested_actions = org_available_actions
                        await turn_context.send_activity(aboutorganization_response_activity)

                    elif self.current_state == "leave policies":
                        leave_policies_actions = leave_policies_action_card()
                        Lp_response_activity = MessageFactory.text('What else would you like to know about Leave Policies?')
                        Lp_response_activity.suggested_actions = leave_policies_actions
                        await turn_context.send_activity(Lp_response_activity)

                    elif self.current_state == "leave management":
                        LM_actions = leave_management_action_card()
                        LM_response_activity = MessageFactory.text("How may I assist you with your leave management needs?")
                        LM_response_activity.suggested_actions = LM_actions
                        await turn_context.send_activity(LM_response_activity)

                    elif self.current_state == "payroll details":
                        payroll_available_actions = payroll_details_action_card()
                        payroll_response_activity = MessageFactory.text("Would you prefer to inquire about  payroll details or access your recent payslips?")
                        payroll_response_activity.suggested_actions = payroll_available_actions
                        await turn_context.send_activity(payroll_response_activity)
                    
                    elif self.current_state == "UpcomingWeek":
                        GWH_available_actions = working_hours_action_card()
                        GWH_response_activity = MessageFactory.text("Please choose from available options")
                        GWH_response_activity.suggested_actions = GWH_available_actions
                        await turn_context.send_activity(GWH_response_activity)

                    elif self.current_state == "PreviousWeek":
                        GWH_available_actions = working_hours_action_card()
                        GWH_response_activity = MessageFactory.text("Please choose from available options")
                        GWH_response_activity.suggested_actions = GWH_available_actions
                        await turn_context.send_activity(GWH_response_activity)
                    
                elif lower_question == 'hi':

                    hi_suggested_actions = top_level_menu_action_card()
                    hi_response_activity = MessageFactory.text("What can I assist you with?")
                    hi_response_activity.suggested_actions = hi_suggested_actions
                    await turn_context.send_activity(hi_response_activity)

                elif  lower_question == "return to the main menu":
                    print("in leave management")
                    main_menu_actions = top_level_menu_action_card()
                    main_menu_response_activity = MessageFactory.text("Choose an option from the  Main Menu:")
                    main_menu_response_activity.suggested_actions = main_menu_actions
                    await turn_context.send_activity(main_menu_response_activity)

                else:
                    if answer.answer == "Thanks for interacting! If you need anything else, just type 'Hi' Have a great day!":
                        await turn_context.send_activity(answer.answer)
                    else:
                        await turn_context.send_activity(answer.answer)
                        follow_up_actions = follow_up_action_card()
                        follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                        follow_up_response.suggested_actions = follow_up_actions
                        await turn_context.send_activity(follow_up_response)
                self.outer_state = 'customqna'

            else:
                output_from_clu = answers_from_clu(question)
                best_intent, confidence_best_intent = clu_get_intent(output_from_clu)

                print(f'**************** \n\n Debug: \n\n Best Intent - {best_intent} \n\n Confidence - {confidence_best_intent[0]} \n\n****************')
                if lower_question == 'enter your query':
                    follow_up_response = MessageFactory.text("Please enter your query below:")
                    await turn_context.send_activity(follow_up_response)

                elif confidence_best_intent.values[0] > 0.7:

                    if best_intent == "GetPaySlip":
                        pay_slips_query = 'SELECT * FROM payslips WHERE EmployeeName = ?;'
                        self.sql_cursor.execute(pay_slips_query, username)
                        payslip_data = self.sql_cursor.fetchone()
                        response_activity = MessageFactory.text(f'Your current payslip is:')
                        if payslip_data:
                            payslip_hero_card = payslip_hero_card(payslip_data)
                            response_activity = MessageFactory.attachment(CardFactory.hero_card(payslip_hero_card))
                            await turn_context.send_activity(response_activity)
                            follow_up_actions = yes_no_action_card()
                            follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                            follow_up_response.suggested_actions = follow_up_actions
                            await turn_context.send_activity(follow_up_response)
                        else:
                            response_activity = MessageFactory.text("No payslip found for the specified user.")
                            await turn_context.send_activity(response_activity)
                            follow_up_actions = yes_no_action_card()
                            follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                            follow_up_response.suggested_actions = follow_up_actions
                            await turn_context.send_activity(follow_up_response)

                    elif best_intent == "GetEmployeeInfo":
                        turn_context.turn_state['current_state'] = "profile details"
                        self.current_state = turn_context.turn_state['current_state']
                        sql_cursor = get_sql_connection_string()
                        EL_info_query = 'SELECT * FROM EmployeeInformation WHERE EmployeeName = ?;'
                        sql_cursor.execute(EL_info_query, username)
                        EL_info = sql_cursor.fetchone()

                        if EL_info:
                            EL_info_hero_card = employee_info_her_card(EL_info)
                            response_activity = MessageFactory.attachment(CardFactory.hero_card(EL_info_hero_card))
                            await turn_context.send_activity(response_activity)
                            follow_up_actions = yes_no_action_card()
                            follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                            follow_up_response.suggested_actions = follow_up_actions
                            await turn_context.send_activity(follow_up_response)

                    
                    elif best_intent == "CheckLeaveBalances":
                        turn_context.turn_state['current_state'] = "leave management"
                        self.current_state = turn_context.turn_state['current_state']
                        EL_query = 'SELECT * FROM EmployeeLeave WHERE EmployeeName = ?;'
                        self.sql_cursor.execute(EL_query, username)
                        EL_data = self.sql_cursor.fetchone()
                        response_activity = MessageFactory.text(f'Your current Leave balanaces and upcoming leaves are:')

                        if EL_data:
                            EL_hero_card = leave_balance_hero_card(EL_data)
                            response_activity = MessageFactory.attachment(CardFactory.hero_card(EL_hero_card))
                            await turn_context.send_activity(response_activity)
                            follow_up_actions = yes_no_action_card()
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
                            GWH_available_actions = working_hours_action_card()
                            GWH_response_activity = MessageFactory.text("Please choose from available options")
                            GWH_response_activity.suggested_actions = GWH_available_actions
                            await turn_context.send_activity(GWH_response_activity)
                        
                        else: 
                            response = output_from_clu["result"]["prediction"]  
                            entity = response['entities'][0]['category']

                            if entity == 'PreviousWeek':
                                turn_context.turn_state['current_state'] = "PreviousWeek"
                                self.current_state = turn_context.turn_state['current_state']
                                prev_week_query = "SELECT EmployeeName, Date, Day, ActualStartTime, ActualEndTime FROM EmployeeSchedule WHERE ActualStartTime IS NOT NULL AND EmployeeName = ?;"
                                self.sql_cursor.execute(prev_week_query, username)
                                prev_week_data = self.sql_cursor.fetchall()
                                response_activity = MessageFactory.text(f'Your Last Week working Hours info:')
                                output_prev_week = convert_dates(prev_week_data)
                                adaptive_card = adaptive_card(username,output_prev_week, week="prev")
                                response_activity = MessageFactory.attachment(CardFactory.adaptive_card(adaptive_card))
                                await turn_context.send_activity(response_activity)

                                follow_up_actions = yes_no_action_card()
                                follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                                follow_up_response.suggested_actions = follow_up_actions
                                await turn_context.send_activity(follow_up_response)

                            elif entity == 'UpcomingWeek':
                                turn_context.turn_state['current_state'] = "UpcomingWeek"
                                self.current_state = turn_context.turn_state['current_state']
                                next_week_query = "SELECT EmployeeName,Date, Day, ScheduledStartTime, ScheduledEndTime FROM EmployeeSchedule WHERE ActualStartTime IS NULL AND EmployeeName = ?;"
                                self.sql_cursor.execute(next_week_query, username)
                                next_week_data = self.sql_cursor.fetchall()
                                response_activity = MessageFactory.text(f'Your Next Week working Hours info:')
                                output_next_week = convert_dates(next_week_data)
                                adaptive_card = adaptive_card(username, output_next_week, week="next")
                                response_activity = MessageFactory.attachment(CardFactory.adaptive_card(adaptive_card))
                                await turn_context.send_activity(response_activity)
                                follow_up_actions = yes_no_action_card()
                                follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                                follow_up_response.suggested_actions = follow_up_actions
                                await turn_context.send_activity(follow_up_response)


                else:
                    human_query = question
                    text_splitter=RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
                    llm = AzureOpenAI(azure_deployment="gpt-instruct",
                                      azure_endpoint='https://tv-llm-applications.openai.azure.com/'
                                      )   
                    memory = ConversationBufferMemory(memory_key="chat_history", input_key = 'human_input')
                    employee = "Peter Jones"
                    response = pdf_query(query = human_query, text_splitter = text_splitter, llm = llm, query_options = ["Guardsman Group FAQ.docx"], memory = memory, llm_db = self.llm_cursor, employee = employee)
                    response_activity = MessageFactory.text(response)
                    await turn_context.send_activity(response_activity)   
                    follow_up_actions = yes_no_action_card()
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

                suggested_actions = top_level_menu_action_card()
                # Greet new members
                response_activity = MessageFactory.text(welcome_message)
                response_activity.suggested_actions = suggested_actions
                await turn_context.send_activity(response_activity)


