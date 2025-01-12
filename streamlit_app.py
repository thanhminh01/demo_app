# @title Search papers on arxiv and process resulting pdf documents
import requests, fitz, io, xml.etree.ElementTree as ET
import tiktoken
import streamlit as st

class Document:
    def __init__(self, DOI, text, pdf_link):
        self.DOI = DOI
        self.text = text
        self.token_count = None
        self.codes = None
        self.pdf_link = pdf_link  # Store the PDF link

# Define a variable for the number of documents to collect
NUM_DOCUMENTS_TO_COLLECT = 3

def fetch_arxiv_papers(query, start_index=0, batch_size=10):
    response = requests.get("http://export.arxiv.org/api/query", params={
        "search_query": query,
        "start": start_index,
        "max_results": batch_size
    })
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        return [{"title": e.find("atom:title", namespace).text.strip(),
                 "pdf_link": e.find("atom:link[@type='application/pdf']", namespace).attrib["href"]}
                for e in root.findall("atom:entry", namespace)]
    st.write(f"Error fetching data: {response.status_code}")
    return []

def extract_text_from_pdf(pdf_url):
    try:
        pdf_data = requests.get(pdf_url).content
        doc = fitz.open(stream=io.BytesIO(pdf_data), filetype="pdf")
        return "".join(doc.load_page(i).get_text("text") for i in range(len(doc)))
    except Exception as e:
        st.write(f"Error processing PDF: {e}")
        return None

def count_tokens(text, tokenizer):
    # Allow special tokens during tokenization
    tokens = tokenizer.encode(text, disallowed_special=())
    return len(tokens)

import asyncio

async def codes_from_text(document_list):
    # Create list of text data from the document list for input to the chain
    text_list = [doc.text for doc in document_list]

    # Run the codes chain asynchronously using abatch
    codes_list = await codes_chain.abatch(text_list)

    # Assign the results to each document and output using st.write
    for i in range(len(document_list)):
        # Save the coded data to the documents in the list
        document_list[i].codes = codes_list[i]
        
# Initialize tokenizer
tokenizer = tiktoken.get_encoding("cl100k_base")

# @title Create document coding chain

code_template = ("""
Consider the research topic:
{topic}

And the text input from a publication:
Text inputs:
{docs}

Please perform the following tasks of the coding step for a thematic analysis of the research topic:

Identify and Assign Codes:
For each segment of text that is relevant to the research topic, identify and assign a code.
Provide Code Details:
For each code, output the following information:

Code Name: A concise, descriptive name for the code.
Code Definition: A brief explanation of what the code represents.
Example: A quote or excerpt that exemplifies the code name and definition.

Example Output 1:
**Code Name**: Product Quality
**Code Definition**: Describes the perceived value and performance of a product.
**Example**: Many reviews highlighted the excellent build quality and durability of the product.

Example Output 2:
**Code Name**: User Feedback
**Code Definition**: "Encompasses comments and suggestions provided by users to improve the product or service.
**Example**: "Users suggested adding more customization options to enhance their experience.
""")

#@title Prompt to synthesize results from coded outputs
themes_template = ("""
You will receive input of all coded data from a list of scholarly articles, which contains coded
segments of text, and a research topic. For the process of a thematic analysis of the research topic,
identify overarching themes that encapsulate common patterns present across the coded segments related to
the research topic, properly describe the theme as a synthesis of the data that formed the theme and
keep track of the source of the theme.

Refer to the examples to form your answers.
Example research topic: How do customers feel about various aspects of our restaurant chain?

Example output 1:
**Theme 1**: Customer has mixed feelings about the quality of the product
**Description**: Product quality is unclear, people seem to have mixed opinion which is something we really
should prioritize improving
**Source**: Article 1,5,6,12,15,30....

Example output 2:
**Theme 2**: Price is good, service is bad
**Description**: Customers appreciate the price but complain about the service quality.
**Source**: Article 2,5,10,25,30...

** Example ends here **
You will now receive the research topic and the coded data input:
Consider the research topic: {topic}
Coded data input:
{docs}
""")
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os

os.environ["OPENAI_API_KEY"] = "GPT_KEY_HERE"

model = ChatOpenAI(model="gpt-4o-mini")
st.write(
    """
    # Research Paper Search and Thematic Analysis App

    Welcome to the **Research Paper Thematic Analysis App**!
    This tool is designed to help you explore key themes across multiple scholarly articles. 
    ### How it works:

    1. **Enter a research topic or query** (e.g., a specific field or question of interest).

    2. The app retrieves **scholarly articles** from ArXiv that match your query. 
        - To limit usage cost, the search is limited to three articles with text content under 10,000 tokens each .
    3. Thematic analysis is conducted by prompting the **GPT-4o-mini** language model to:  
        - Extract **key thematic elements** from each individual article.  
        - Synthesize **overarching themes** that unify insights across all three articles.
    4. Want to suggest custom feature? Contact me at thanhminh01798@gmail.com  
    """)
# Script Execution
if 'query' not in st.session_state:
    st.session_state.query = ""  # Initialize query in session state
if 'documents' not in st.session_state:
    st.session_state.documents = []  # Initialize query in session state
if 'result' not in st.session_state:
    st.session_state.result = ""
if 'submitted' not in st.session_state:
    st.session_state.submitted = False
if 'coding_finished' not in st.session_state:
    st.session_state.coding_finished = False
if 'show_analysis_1' not in st.session_state:
    st.session_state.show_analysis_1 = False
if 'show_analysis_2' not in st.session_state:
    st.session_state.show_analysis_2 = False
if 'show_analysis_3' not in st.session_state:
    st.session_state.show_analysis_3 = False
if 'show_analysis_4' not in st.session_state:
    st.session_state.show_analysis_4 = False    
if not st.session_state.submitted:
    st.write(f"**Enter a search query** or choose from one of the preselected searches")
default = "Imitation Learning"
col1, col2 = st.columns([3,1]) 

# Put the text input in the first column

with col1:
    query_input = st.text_input(label = "Enter search query", label_visibility = "collapsed")

# Put the button in the second column
with col2:
    submit_button_placeholder = st.empty()
    if not st.session_state.submitted:
        if submit_button_placeholder.button("Submit "):
            if query_input.strip() == "":
                st.session_state.warning_message = "Please enter a search term."
            else:
            # Perform the submit action when there's a valid input
                st.session_state.submitted = True
                st.success(f"Submitted with query: {query_input}")
                st.session_state.submitted = True
                st.session_state.query = query_input   # Store query
                submit_button_placeholder.empty()
if 'warning_message' in st.session_state:
    st.warning(st.session_state.warning_message)
    del st.session_state.warning_message  # Clear the warning after it's shown
if not st.session_state.submitted:
    st.write(f"**Search samples**:")
    sample1_button_placeholder = st.empty()
    sample2_button_placeholder = st.empty()
    sample3_button_placeholder = st.empty()
    if sample1_button_placeholder.button("Immitation Learning Robotics"):
        default = "Immitation Learning Robotics"
        st.session_state.submitted = True
        st.session_state.query = default
        submit_button_placeholder.empty()
        sample1_button_placeholder.empty()
        sample2_button_placeholder.empty()
        sample3_button_placeholder.empty()
    elif sample2_button_placeholder.button("Retrieval Augmented Generation"):
        default = "Retrieval Augmented Generation"
        st.session_state.submitted = True
        st.session_state.query = default
        submit_button_placeholder.empty()
        sample1_button_placeholder.empty()
        sample2_button_placeholder.empty()
        sample3_button_placeholder.empty()
    elif sample3_button_placeholder.button("Prompt Engineering"):
        default = "Prompt Engineering"
        st.session_state.submitted = True
        st.session_state.query = default
        submit_button_placeholder.empty()
        sample1_button_placeholder.empty()
        sample2_button_placeholder.empty()
        sample3_button_placeholder.empty()
if st.session_state.submitted and not st.session_state.coding_finished:
    st.write(f"Your search query is: {st.session_state.query}")
    start_index = 0
    batch_size = 10
    MAX_TOKENS = 10000
    st.write("\n\n")
    st.write("\nFetching and processing papers...\n")

    while len(st.session_state.documents) < NUM_DOCUMENTS_TO_COLLECT:
        papers = fetch_arxiv_papers(st.session_state.query, start_index=start_index, batch_size=batch_size)
        if not papers:
            st.write("No more papers available.")
            break

        for p in papers:
            if len(st.session_state.documents) >= NUM_DOCUMENTS_TO_COLLECT:
                break
            pdf_text = extract_text_from_pdf(p['pdf_link'])
            if pdf_text:
                DOI = p['pdf_link'].split("/")[-1]
                try:
                    token_count = count_tokens(pdf_text, tokenizer)
                    st.write(f"Checked DOI: {DOI}, Token Count: {token_count}")
                    if token_count <= MAX_TOKENS:
                        st.session_state.documents.append(Document(DOI=DOI, text=pdf_text, pdf_link=p['pdf_link']))
                        st.session_state.documents[-1].token_count = token_count
                        st.write(f"Article {DOI} added. Total collected: {len(st.session_state.documents)}\n")
                except Exception as e:
                    st.write(f"Error counting tokens for {DOI}: {e}")
            else:
                st.write(f"Failed to extract text for {p['pdf_link']}.")

        start_index += batch_size

    # Output the links to the fetched documents
    st.write("\nEligible Documents Collected:", len(st.session_state.documents))
    for doc in st.session_state.documents:
        st.write(f"DOI: {doc.DOI}, Token Count: {doc.token_count}")
        st.write(f"PDF Link: {doc.pdf_link}\n")
    # Format the template with the specific research topic and placeholder string for document text
    code_template_formatted = code_template.format(topic=st.session_state.query, docs="{docs}")
    # Create a Prompt Template using the formatted code template
    codes_prompt = ChatPromptTemplate.from_template(code_template_formatted)

    str_output_parser = StrOutputParser()

    codes_chain = codes_prompt | model | str_output_parser
    # @title Prompt LLM for documents coding
    st.write("""
    ### Article Coding 

    We begin by analyzing each article to extract its key thematic elements, referred to as "coding segments." These represent the significant themes or concepts identified in each article based on your search query.

    Generating key points for each articles . . .
    """)
    asyncio.run(codes_from_text(st.session_state.documents))
    #codes_from_text(st.session_state.documents)
    themes_template_formatted = themes_template.format(topic=st.session_state.query, docs="{docs}")

    # Create a Prompt Template using the formatted template
    themes_prompt = ChatPromptTemplate.from_template(themes_template_formatted)

    # Final chain for identifying themes of the documents
    themes_chain = themes_prompt | model | str_output_parser

    #@title Prepare input, invoke with prompt for final result

    # Prepare a string variable to be used as input to determine themes
    full_codes_output = ""

    # Iterate over each eligible document to append its codes to the output variable
    for i in range(len(st.session_state.documents)):
        full_codes_output += f"Article {i+1}:\n"
        full_codes_output += f"Codes: {st.session_state.documents[i].codes}\n"
        full_codes_output += "-" * 30 + "\n"  # Add a separator for better readability
    st.write("""
    ### Synthesizing Overarching Themes

    After analyzing the individual articles, we combine the key themes across all three to generate a list of overarching themes. These themes provide a unified view of the topic across the selected articles.

    Here is the final thematic analysis synthesizing insights from all three articles:
    """)
    st.session_state.result = themes_chain.invoke(full_codes_output)
    st.write(st.session_state.result)
    st.session_state.coding_finished = True

if st.session_state.coding_finished:
    if st.button("Show/Hide coding result for article 1"):
        st.session_state.show_analysis_1 = not st.session_state.show_analysis_1
        st.session_state.show_analysis_2 = False
        st.session_state.show_analysis_3 = False
        st.session_state.show_analysis_4 = False
    if st.button("Show/Hide coding result for article 2"):
        st.session_state.show_analysis_2 = not st.session_state.show_analysis_2
        st.session_state.show_analysis_1 = False
        st.session_state.show_analysis_3 = False
        st.session_state.show_analysis_4 = False
    
    if st.button("Show/Hide coding result for article 3"):
        st.session_state.show_analysis_3 = not st.session_state.show_analysis_3
        st.session_state.show_analysis_1 = False
        st.session_state.show_analysis_2 = False
        st.session_state.show_analysis_4 = False
    if st.button("Show/Hide Overarching themes accross all three articles"):
        st.session_state.show_analysis_4 = not st.session_state.show_analysis_4
        st.session_state.show_analysis_1 = False
        st.session_state.show_analysis_2 = False
        st.session_state.show_analysis_3 = False
    # Conditional display for Document 1 analysis
    if st.session_state.show_analysis_1:
        st.write(f"Link to article: {st.session_state.documents[0].pdf_link}")
        st.write(f"{st.session_state.documents[0].codes}")
    # Conditional display for Document 2 analysis
    if st.session_state.show_analysis_2:
        st.write(f"Link to article: {st.session_state.documents[1].pdf_link}")
        st.write(f"{st.session_state.documents[1].codes}")
    # Conditional display for Document 3 analysis
    if st.session_state.show_analysis_3:
        st.write(f"Link to article: {st.session_state.documents[2].pdf_link}")
        st.write(f"{st.session_state.documents[2].codes}")
    if st.session_state.show_analysis_4:
        st.write(f"{st.session_state.result}")
        