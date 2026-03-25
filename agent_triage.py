import os
from dotenv import load_dotenv

# Add references
# Add references
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import ConnectedAgentTool, MessageRole, ListSortOrder, ToolSet, FunctionTool
from azure.identity import DefaultAzureCredential



# Clear the console
os.system('cls' if os.name=='nt' else 'clear')

# Load environment variables from .env file
load_dotenv()
project_endpoint = os.getenv("PROJECT_ENDPOINT")
model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")


# Connect to the agents client
# Connect to the agents client
agents_client = AgentsClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True
    ),
)



# Create document ingestion agent
ingestion_agent_name = 'ingestion_agent'
ingestion_agent_instructions = '''
You are a legal document ingestion specialist.
When given the text of a legal document:
1. Summarize the type of document (contract, NDA, policy, etc.)
2. List the key parties involved
3. Identify the main subject matter and scope
Keep your response structured and concise.
'''
ingestion_agent = agents_client.create_agent(
    model=model_deployment,
    name=ingestion_agent_name,
    instructions=ingestion_agent_instructions
)

# Create clause extraction agent
clause_agent_name = 'clause_extraction_agent'
clause_agent_instructions = '''
You are a legal clause extraction specialist.
Given a legal document, identify and extract ALL of the following clause types
if they are present:
- Liability clauses
- Indemnification clauses
- Termination clauses
- Confidentiality/NDA clauses
- Intellectual property clauses
- Dispute resolution clauses
- Payment terms
For each clause found, provide: Clause Type, Location hint, and a brief summary.
If a clause type is not found, state 'Not present'.
'''
clause_agent = agents_client.create_agent(
    model=model_deployment,
    name=clause_agent_name,
    instructions=clause_agent_instructions
)

# Create compliance validation agent
compliance_agent_name = 'compliance_agent'
compliance_agent_instructions = '''
You are a legal compliance validation specialist.
Given extracted legal clauses, assess each one for compliance issues:
- Flag any clauses that appear one-sided or unusually favorable to one party
- Identify missing standard protections (e.g., no limitation of liability)
- Note any potentially unenforceable or vague language
- Check for GDPR/data protection issues if personal data is mentioned
Rate overall compliance risk as: LOW / MEDIUM / HIGH
Provide specific recommendations for each flagged issue.
'''
compliance_agent = agents_client.create_agent(
    model=model_deployment,
    name=compliance_agent_name,
    instructions=compliance_agent_instructions
)




    # Create connected agent tools for the support agents
# Create connected agent tools
ingestion_tool = ConnectedAgentTool(
    id=ingestion_agent.id,
    name=ingestion_agent_name,
    description='Ingests and summarizes the legal document structure and parties'
)
clause_tool = ConnectedAgentTool(
    id=clause_agent.id,
    name=clause_agent_name,
    description='Extracts key legal clauses from the document'
)
compliance_tool = ConnectedAgentTool(
    id=compliance_agent.id,
    name=compliance_agent_name,
    description='Validates clauses for compliance issues and flags risks'
)


# Create the legal review orchestrator agent
orchestrator_name = 'legal_review_orchestrator'
orchestrator_instructions = '''
You are a comprehensive legal document review assistant.
When given a legal document, use your connected tools in this order:
1. Use the ingestion_agent tool to summarize the document structure
2. Use the clause_extraction_agent tool to extract all key clauses
3. Use the compliance_agent tool to validate compliance and flag issues
4. Produce a final report with three sections:
   DOCUMENT SUMMARY, KEY CLAUSES FOUND, COMPLIANCE FLAGS & RECOMMENDATIONS
'''
orchestrator = agents_client.create_agent(
    model=model_deployment,
    name=orchestrator_name,
    instructions=orchestrator_instructions,
    tools=[
        ingestion_tool.definitions[0],
        clause_tool.definitions[0],
        compliance_tool.definitions[0]
    ]
)


    

# Use the agents to review a legal document
print("Creating legal review thread.")
thread = agents_client.threads.create()

# Create the legal document prompt
prompt = input("\nPaste the legal clause or document text you want to review: ")

# Send a prompt to the agent
message = agents_client.messages.create(
    thread_id=thread.id,
    role=MessageRole.USER,
    content=prompt,
)

# Run the thread using the primary agent
print("\nProcessing legal document review. Please wait...")
run = agents_client.runs.create_and_process(thread_id=thread.id, agent_id=orchestrator.id)

if run.status == "failed":
    print(f"Run failed: {run.last_error}")

# Fetch and display messages
messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
for message in messages:
    if message.text_messages:
        last_msg = message.text_messages[-1]
        print(f"{message.role}:\n{last_msg.text.value}\n")


# Clean up
print("Cleaning up agents:")
agents_client.delete_agent(orchestrator.id)
print("Deleted legal review orchestrator.")
agents_client.delete_agent(ingestion_agent.id)
print("Deleted document ingestion agent.")
agents_client.delete_agent(clause_agent.id)
print("Deleted clause extraction agent.")
agents_client.delete_agent(compliance_agent.id)
print("Deleted compliance validation agent.")
