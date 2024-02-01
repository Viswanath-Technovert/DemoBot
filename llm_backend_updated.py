from langchain.chains.llm import LLMChain
from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain_community.document_loaders.word_document import Docx2txtLoader
from langchain_community.document_loaders.text import TextLoader
from langchain_community.vectorstores.faiss import FAISS
from langchain.prompts import PromptTemplate
from langchain_openai.embeddings.azure import AzureOpenAIEmbeddings
import os
from sql_querying import sql_query

os.environ['OPENAI_API_VERSION'] = '2023-12-01-preview'
os.environ['AZURE_OPENAI_API_KEY'] = 'e63ed695495543d58595fab4e27e4ff1'

def llm_query(query, document_search, chain,llm_db, employee):
    
    docs = document_search.similarity_search(query)
    # chain_res = chain.predict(human_input = query, context = docs).split('Human:')[0]
    print('*'*10,'searching in sql','*'*10)
    chain_res = chain.predict(human_input = query, context = docs)
    print('1'+chain_res+'1')

    if chain_res == " No Answer Found!":
        query_empl = query + f'Employee Name: {employee}'
        response = sql_query(query,llm_db)
        return response['output']
    else:
        return chain_res + '\n\n'



def pdf_query(query, text_splitter, llm, query_options, memory, llm_db, employee):  

    documents_query = []
    for file in query_options:
        if file.endswith('.pdf'):
            pdf_path = './documents/' + file
            loader = PyPDFLoader(pdf_path)
            documents_query.extend(loader.load())
        elif file.endswith('.docx') or file.endswith('.doc'):
            doc_path = './documents/' + file
            loader = Docx2txtLoader(doc_path)
            documents_query.extend(loader.load())
        elif file.endswith('.txt'):
            text_path = './documents/' + file
            loader = TextLoader(text_path)
            documents_query.extend(loader.load())


    docs=text_splitter.split_documents(documents_query)
    embeddings = AzureOpenAIEmbeddings(azure_deployment="ada-embed",
                                        azure_endpoint = 'https://tv-llm-applications.openai.azure.com/',
                                        chunk_size=16)

    document_search = FAISS.from_texts([t.page_content for t in docs], embeddings)

    template = """You are an AI having a conversation with a human.
    Given the following extracted parts of a long document and a question, create a final answer.
    And if you can't find the answer, strictly mention "No Answer Found!"

    {context}

    {chat_history}
    Human: {human_input}
    AI:"""

    prompt = PromptTemplate(input_variables=["chat_history", "human_input", "context"], template=template)
    chain = LLMChain(llm = llm, prompt = prompt,memory = memory)

    result = llm_query(query, document_search, chain,llm_db, employee)

    return result



# # Testing the functionality of this file.

# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_openai.llms.azure import AzureOpenAI
# from langchain.memory import ConversationBufferMemory

# llm = AzureOpenAI(azure_deployment="gpt-instruct",
#                   azure_endpoint='https://tv-llm-applications.openai.azure.com/'
#                   )
# text_splitter=RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
# options = ['TESLAInc.pdf']
# query = 'What are the different battery pack options of Tesla Model S?'
# memory = ConversationBufferMemory(memory_key="chat_history", input_key = 'human_input')

# result, cont_docs = pdf_query(query = query, text_splitter = text_splitter, llm = llm, query_options = options, memory = memory)

# print(result)