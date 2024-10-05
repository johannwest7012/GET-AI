import chainlit as cl
import requests
import json
from chainlit.input_widget import Select, Slider, TextInput



# This receives updates in settings
@cl.on_settings_update
async def settings_update(settings):
    print("Settings updated ", settings)
     

@cl.on_chat_start
async def main():
    # Collect API URL using an input box
    welcome_message = await cl.AskUserMessage(content="What's your GET request?", timeout=10).send()
    
    # response_message = await cl.AskUserMessage(content="Here is your api", timeout=10).send()
    await cl.Message(content="Here is your API, adjust the settings as necessary.").send()


    settings = await cl.ChatSettings(
        [
            TextInput(id="url", label="GET API URL", initial="urlgeneratedbyLLM.com"),
            Slider(
                id="userID",
                label="User ID",
                initial=1,
                min=0,
                max=10,
                step=1,
            ),
            Select(
                id="type",
                label="Type",
                values=["car", "truck", "boat"],
                initial_index=0,
            ),
           
        ],
    ).send()
    