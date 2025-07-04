import os
import fitz  # PyMuPDF for PDF handling
import docx
import pandas as pd

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

def extract_text(file, filetype):
    if filetype == "pdf":
        doc = fitz.open(stream=file.read(), filetype="pdf")
        text = "".join([page.get_text() for page in doc])
        return text
    elif filetype == "docx":
        doc = docx.Document(file)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    elif filetype == "csv":
        df = pd.read_csv(file)
        return df.to_string(index=False)
    else:
        return file.read().decode("utf-8")

def get_qa_chain(text):
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise ValueError("Missing OPENAI_API_KEY")

    embeddings = OpenAIEmbeddings(openai_api_key=openai_key)
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", openai_api_key=openai_key)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    chunks = text_splitter.split_text(text)
    documents = [Document(page_content=chunk, metadata={"source": "uploaded_file"}) for chunk in chunks]

    vectorstore = FAISS.from_documents(documents, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

    prompt_template = PromptTemplate.from_template("""
You are a docuemnt analyzer , answer the question asked in detailed and in context,
if the contextis not related to the document , reply I dont know

Context:
{context}

Question: {question}
Answer:""")

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        chain_type_kwargs={"prompt": prompt_template},
        return_source_documents=True
    )

    return qa_chain
