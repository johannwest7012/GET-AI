# %%
from langchain_anthropic import ChatAnthropic
from typing import Literal, Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
import json

# %%
load_dotenv()

# %%
from e2b_code_interpreter import CodeInterpreter
code_interpreter = CodeInterpreter()

# %%
# %%
# Load mock API definitions from file path
def load_api_definitions(json_path: str) -> Dict[str, Any]:
    with open(json_path, 'r') as file:
        return json.load(file)

# %%
# %%
@tool
def mock_api_call(api_name: str, endpoint: str, method: str, params: Dict[str, Any] = None, body: Dict[str, Any] = None):
    """
    Simulate an API call by dynamically loading mock_apis.json within the function.
    """
    # Load the mock API definitions within the function to avoid global dependencies
    mock_apis = load_api_definitions("mock_apis.json")

    # Find the API
    api = next((api for api in mock_apis.get("apis", []) if api["name"].lower() == api_name.lower()), None)
    if not api:
        return {"error": f"API '{api_name}' not found."}

    # Find the endpoint
    endpoint_def = next((ep for ep in api.get("endpoints", []) if ep["path"] == endpoint and ep["method"].lower() == method.lower()), None)
    if not endpoint_def:
        return {"error": f"Endpoint '{method} {endpoint}' not found in API '{api_name}'."}

    # Determine the response based on the method and parameters
    responses = endpoint_def.get("responses", {})
    success_response = None
    for status_code in sorted(responses.keys()):
        if status_code.startswith('2'):
            success_response = responses[status_code]
            break

    if success_response:
        return success_response.get("body", {"message": success_response.get("description", "No description provided.")})
    else:
        first_error_response = next(iter(responses.values()), {})
        return first_error_response.get("body", {"error": first_error_response.get("description", "An error occurred.")})

# %%
# %%
@tool
def get_weather(city: Literal["nyc", "sf"]):
    """Use this to get weather information."""
    if city.lower() == "nyc":
        return "It might be cloudy in NYC."
    elif city.lower() == "sf":
        return "It's always sunny in SF."
    else:
        raise AssertionError("Unknown city")

# %%
tool
def list_apis():
    """List all available APIs by dynamically loading the mock_apis.json."""
    mock_apis = load_api_definitions("mock_apis.json")
    apis = [api['name'] for api in mock_apis.get('apis', [])]
    return json.dumps({"available_apis": apis}, indent=2)


def code_interpret(code_interpreter: CodeInterpreter, code: str):
    """
    Execute the code block dynamically, ensuring the mock APIs are loaded within the context.
    """
    json_dic = load_api_definitions('mock_apis.json')
    
    complete_code = f"""
import json

def load_api_definitions(json_path: str = "mock_apis.json"):
    with open(json_path, 'r') as file:
        return json.load(file)

mock_apis = {json_dic}

def mock_api_call(api_name, endpoint, method, params=None, body=None):
    api = next((api for api in mock_apis.get("apis", []) if api["name"].lower() == api_name.lower()), None)
    if not api:
        return {{"error": f"API '{{api_name}}' not found."}}
    endpoint_def = next((ep for ep in api.get("endpoints", []) if ep["path"] == endpoint and ep["method"].lower() == method.lower()), None)
    if not endpoint_def:
        return {{"error": f"Endpoint '{{method}} {{endpoint}}' not found in API '{{api_name}}'."}}
    responses = endpoint_def.get("responses", {{}},)
    success_response = next((resp for code, resp in responses.items() if code.startswith('2')), None)
    return success_response.get("body", {{"message": success_response.get("description", "No description provided.")}}) if success_response else {{"error": "No successful responses found."}}

{code}
"""
    print("CODE:", code)
    # Execute the constructed code snippet in e2b environment
    exec_result = code_interpreter.notebook.exec_cell(
        complete_code,
        on_stderr=lambda stderr: print("\n[Code Interpreter stderr]", stderr),
        on_stdout=lambda stdout: print("\n[Code Interpreter stdout]\n", stdout),
    )
  
    if exec_result.error:
        print("[Code Interpreter error]", exec_result.error)  # Runtime error
        return None, exec_result.error
    else:
        # Use the correct attribute to capture stdout (results, output, or other available properties)
        return exec_result.results, exec_result.logs



last_exectued_code = None 

# %%
@tool
def execute_code_with_apis(code: str):
    """Use this to execute Python code that requires mock APIs and return the result along with an analysis of the output."""
    try:
        # Capture the correct execution output and logs

        global last_exectued_code
        last_exectued_code = code 
        exec_results, exec_logs = code_interpret(code_interpreter, code)
        
        # Create a structured response including the executed code, output, and logs
        response = {
            "executed_code": code,
            "execution_output": exec_results,  # Adjusted to capture the correct output
            "logs": exec_logs,
        }
        return response
    except Exception as e:
        return {"error": str(e)}




# %%
# Define a prompt that guides the agent on how to use these tools
prompt = """"You are Claude, an intelligent AI assistant integrated into API Genie—a platform that transforms natural language descriptions into executed API calls and code. Your primary objective is to assist developers by understanding their natural language requests, determining the appropriate actions, generating the necessary schemas, creating and executing Python code to fulfill those requests using the `execute_code` tool and the e2b code interpreter, and delivering real-time results within a Postman-like interface.

You have access to the following tools:
- `list_apis`: Retrieves a list of all available APIs defined in `mock_apis.json`.
- `mock_api_call`: Simulates API calls based on specified API names, endpoints, methods, parameters, and request bodies.
- `execute_code`: Runs Python code and returns the output using the e2b code interpreter.
- `get_weather`: Provides weather information for predefined cities such as "nyc" and "sf".

**Important:** When generating Python code to interact with APIs, **always use the `mock_api_call` tool** instead of making real HTTP requests using libraries like `requests`. This ensures that all API interactions are simulated based on the `mock_apis.json` definitions.

When a user submits a query, follow these steps in order:

1. **Identify the Intent:**
   - Determine what the user wants to achieve (e.g., retrieve data, create a resource, update information).

2. **Generate the Schema:**
   - Based on the user's request, formulate the necessary schema that defines the structure of the API call or the Python code to be executed. This includes identifying required parameters, request bodies, and endpoints from `mock_apis.json`.

3. **Generate and Execute Python Code:**
   - **Create the appropriate Python code snippet** that corresponds to the user's request using the generated schema.
   - **Use the `mock_api_call` tool within your code** to simulate the API interaction.
   - **Use the `execute_code` tool** to run the generated Python code via the e2b code interpreter.
   - Capture both the generated code and its execution output (including any error messages).

4. **Present the Results:**
   - **Include the Generated Code:** Display the Python code that was generated and executed to fulfill the user's request. Use proper formatting (e.g., code blocks) to enhance readability.
   - **Display the JSON Output:** Present the results from the `execute_code` tool (the code ran and its result) in a clear, structured JSON format.
   - **Example Formatting:**
     ```python
     ```python
     # Generated Python Code
     def get_user_details(user_id):
         user_details = mock_api_call(
             api_name="User Management API",
             endpoint=f"/users/{user_id}",
             method="GET"
         )
         return user_details

     user_id = "user-001"
     user_details = get_user_details(user_id)
     print(user_details)
     ```
     ```

     ```json
     {
       "id": "user-001",
       "name": "John Doe",
       "email": "john.doe@example.com",
       "role": "admin",
       "createdAt": "2024-01-15T08:30:00Z",
       "lastLogin": "2024-10-01T12:45:00Z"
     }
     ```

5. **Handle Ambiguities and Errors:**
   - If the user's request is unclear or lacks necessary details, ask clarifying questions to gather more information.
   - Manage errors gracefully by providing meaningful error messages and actionable feedback to help users resolve issues (e.g., invalid parameters, unsupported actions).

6. **Maintain Security and Best Practices:**
   - Never expose sensitive information such as API keys or personal data in responses.
   - Validate and sanitize all user inputs before processing to prevent security vulnerabilities.
   - Ensure that all interactions adhere to best practices for API usage and code execution.

7. **Iterative Improvement:**
   - Continuously learn from user interactions to improve response accuracy and relevance.
   - Update tool functionalities and schema generation processes as needed to accommodate new APIs or evolving user requirements.

Your goal is to streamline the development process for users by accurately translating their natural language instructions into effective API interactions and executable code, providing immediate and understandable results. If a user presents a question outside the scope of API Genie that you can answer correctly, respond appropriately. If you do not know how to answer a query, simply say, "I don't know."

"""""
# %%
# Initialize the model
model = ChatAnthropic(
    model="claude-3-5-sonnet-20240620",
    api_key="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",
    temperature=0
)

# Create the agent graph
graph = create_react_agent(model, tools=[execute_code_with_apis, mock_api_call, get_weather, list_apis], state_modifier=prompt)



# %%
def print_stream(stream):
    for s in stream:
        if "messages" in s:
            for message in s["messages"]:
                if isinstance(message, dict) and "type" in message and message["type"] == "tool_use":
                    print(f"Tool Use ID: {message.get('id')}")
                if isinstance(message, dict) and message.get("type") == "tool_result":
                    if "execution_output" in message:
                        print("\n=== Execution Output ===\n")
                        print(message["execution_output"])
                if isinstance(message, tuple):
                    print(message)
                else:
                    message.pretty_print()


##### Frontend Related Stuff

def stream_to_string(stream):
    output_string = ""
    for s in stream:
        message = s["messages"][-1]
        
        if isinstance(message, tuple):
            # If the message is a tuple, process it as before
            output_string += f"{message[1]}\n"
        elif hasattr(message, 'content'):
            # For HumanMessage or similar, use 'content' to extract the message text
            output_string += f"{message.content}\n"
        else:
            # Handle other message types if needed (optional)
            output_string += f"Unknown message type: {message}\n"

    return output_string


def last_exectued_code(): 
    return last_exectued_code


def use_agent(user_prompt): 


    print("USER PROMPT IN USE_AGENT:", user_prompt)
    inputs = {"messages": [("user", user_prompt)]}
    return stream_to_string(graph.stream(inputs, stream_mode="values"))


