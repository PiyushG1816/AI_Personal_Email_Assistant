from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)


class EmailKeyInfo(BaseModel):
    needs_reply: bool = Field(description="Whether this email warrants a drafted reply")
    action_required: str | None = Field(
        default=None,
        description="Concrete action the recipient needs to take, or null if no action is required",
    )
    meeting_title: str | None = Field(default=None)
    meeting_date: str | None = Field(default=None, description="YYYY-MM-DD")
    meeting_time: str | None = Field(default=None, description="HH:MM")
    meeting_duration_minutes: int | None = Field(default=None)


structured_model = model.with_structured_output(EmailKeyInfo)

_email_block = "From: {sender}\nSubject: {subject}\nBody: {body}"

summarizer_chain = (
    ChatPromptTemplate.from_template(
        "Summarize this email in 1-2 sentences. Reply with the summary only.\n\n"
        + _email_block
    )
    | model
    | StrOutputParser()
)

classifier_chain = (
    ChatPromptTemplate.from_template(
        "Classify this email into exactly one of: "
        "Finance, Travel, Meetings, Support, Personal, Spam, General. "
        "Reply with the category word only.\n\n"
        + _email_block
    )
    | model
    | StrOutputParser()
)

priority_chain = (
    ChatPromptTemplate.from_template(
        "Rate this email's priority as exactly one of: low, medium, high. "
        "Reply with the priority word only.\n\n"
        + _email_block
    )
    | model
    | StrOutputParser()
)

key_info_chain = (
    ChatPromptTemplate.from_template(
        "Extract structured info from this email. "
        "If no meeting is mentioned, leave the meeting fields null. "
        "If no action is required of the recipient, leave action_required null.\n\n"
        + _email_block
    )
    | structured_model
)

enrichment_chain = RunnableParallel(
    summarizer=summarizer_chain,
    classifier=classifier_chain,
    key_info=key_info_chain,
    priority=priority_chain,
)
