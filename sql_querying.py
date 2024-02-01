# Import Statements


from langchain.agents import create_sql_agent
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_openai.chat_models.azure import AzureChatOpenAI
from langchain.agents.agent_types import AgentType

import os

os.environ['OPENAI_API_VERSION'] = '2023-12-01-preview'
os.environ['AZURE_OPENAI_API_KEY'] = 'e63ed695495543d58595fab4e27e4ff1'

def sql_query(question,db):

    sql_llm = AzureChatOpenAI(azure_deployment='gpt-16k',
                              azure_endpoint='https://tv-llm-applications.openai.azure.com/')

    toolkit = SQLDatabaseToolkit(db=db, llm=sql_llm)
    agent_executor = create_sql_agent(
        llm=sql_llm,
        toolkit=toolkit,
        verbose=True,
        agent_type=AgentType.OPENAI_FUNCTIONS
    )
    
    response = agent_executor.invoke(question)

    return response