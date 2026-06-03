import os
from pathlib import Path
from langchain_anthropic import ChatAnthropic
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage, convert_to_messages
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv(override=True)

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
COMPANY_NAME = os.getenv("COMPANY_NAME", "our company")
DB_NAME = str(Path(__file__).parent.parent / "vector_db")
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "10"))

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

SYSTEM_PROMPT = """
You are a knowledgeable, friendly assistant representing {company}.
You are chatting with a user about {company}.
If relevant, use the given context to answer any question.
If you don't know the answer, say so.
Context:
{{context}}
""".format(company=COMPANY_NAME)

vectorstore = Chroma(persist_directory=DB_NAME, embedding_function=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": RETRIEVAL_K})
llm = ChatAnthropic(temperature=0, model_name=MODEL)


def fetch_context(question: str) -> list[Document]:
    return retriever.invoke(question)


def combined_question(question: str, history: list[dict] = []) -> str:
    prior = "\n".join(m["content"] for m in history if m["role"] == "user")
    return prior + "\n" + question


def answer_question(question: str, history: list[dict] = []) -> tuple[str, list[Document]]:
    combined = combined_question(question, history)
    docs = fetch_context(combined)
    context = "\n\n".join(doc.page_content for doc in docs)
    system_prompt = SYSTEM_PROMPT.format(context=context)
    messages = [SystemMessage(content=system_prompt)]
    messages.extend(convert_to_messages(history))
    messages.append(HumanMessage(content=question))
    response = llm.invoke(messages)
    return response.content, docs
