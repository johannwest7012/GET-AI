import chainlit as cl
import requests
import json
from chainlit.input_widget import Select, Slider, TextInput
from agent import graph, use_agent, last_exectued_code, print_stream  # Import the react agent graph and print_stream from agent.py



# Global variable to store the previous user's message
previous_message = None
last_executed_code = None 



# def user_chagnes_api(settings):


# This function receives updates in settings
@cl.on_settings_update
async def settings_update(settings):
    global last_executed_code
    last_exectued_code = last_exectued_code()

    prompt =f"Give me the data based on these parameters {settings}"
    
    response, last_executed_code = await use_agent(prompt)

    await cl.Message(response).send()



@cl.on_chat_start
async def main():
    # Display initial message to the user
    await cl.Message(content="Welcome to the GET AI! What api do you want to query?").send()

    # Present settings to the user using Chainlit UI
    settings = await cl.ChatSettings(
        [
            TextInput(id="api_name", label="API Name", initial=""),
            TextInput(id="endpoint", label="Endpoint URL", initial=""),
            TextInput(id="params", label="Parameters", initial=""),

        ]
    ).send()


import re

def parse_api_call(function_str):
    # Create an empty dictionary to store extracted values
    parsed_data = {
        'api_name': '',
        'endpoint': '',
        'params': ''
    }

    # Regular expressions to capture api_name, endpoint, and params
    api_name_pattern = r'api_name\s*=\s*"([^"]+)"'
    endpoint_pattern = r'endpoint\s*=\s*"([^"]+)"'
    params_pattern = r'params\s*=\s*({.*?})'

    # Extract values using regex
    api_name_match = re.search(api_name_pattern, function_str)
    endpoint_match = re.search(endpoint_pattern, function_str)
    params_match = re.search(params_pattern, function_str)

    # Store values in the dictionary if found
    if api_name_match:
        parsed_data['api_name'] = api_name_match.group(1)
    if endpoint_match:
        parsed_data['endpoint'] = endpoint_match.group(1)
    if params_match:
        parsed_data['params'] = params_match.group(1)

    return parsed_data

import asyncio


@cl.on_message
async def on_message(message: cl.Message):
    global previous_message

    response = use_agent(message.content)

    previous_message = message
    await cl.Message(response).send()


async def stream_agent_responses(inputs):
    """
    Stream the agent's response step by step and display them in Chainlit's UI.
    """
    for stream_output in graph.stream(inputs, stream_mode="values"):
        message = stream_output["messages"][-1]
        
        if isinstance(message, tuple):
            # Send the agent's output to the UI
            await cl.Message(content=message[1]).send()
        else:
            # Pretty print the message and send it to the UI
            await cl.Message(content=message.pretty()).send()
