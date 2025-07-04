import os
import fitz  # PyMuPDF
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
        raise EnvironmentError("Missing OPENAI_API_KEY. Set it in your environment variables.")

    try:
        # Initialize embeddings and LLM
        embeddings = OpenAIEmbeddings(openai_api_key=openai_key)
        llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0,
            openai_api_key=openai_key
        )

        # Smart text splitting
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        chunks = text_splitter.split_text(text)
        documents = [Document(page_content=chunk, metadata={"source": "uploaded_file"}) for chunk in chunks]

        # FAISS vector store
        vectorstore = FAISS.from_documents(documents, embeddings)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

        # Prompt
        prompt_template = PromptTemplate.from_template("""
You are a document analyzer. Answer the question asked based on the context in a clear and detailed way.
If the context is not related to the document, reply: "I don't know".

Context:
{context}

Question: {question}
Answer:
""")

        # QA Chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            chain_type="stuff",
            chain_type_kwargs={"prompt": prompt_template},
            return_source_documents=True
        )

        return qa_chain

    except Exception as e:
        print(f"[ERROR] Failed to initialize QA chain: {e}")
        raise RuntimeError("An error occurred while setting up the QA chain. Please check the logs for details.")
