import os
import json
import importlib.util
from typing import Callable, Dict
import streamlit as st
import traceback
from openai import OpenAI

openai_client = OpenAI(api_key = os.environ.get('OPENAI_API_KEY'))

def load_functions_from_folder(folder_path: str) -> Dict[str, Callable]:
    functions_dict = {}

    # Iterate over each file in the folder
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.py'):  # Only process Python files
            file_path = os.path.join(folder_path, file_name)
            module_name = file_name[:-3]  # Strip the .py extension

            # Dynamically load the module
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Extract function from the module (assuming there's only one function per file)
            functions = [getattr(module, attr) for attr in dir(module) 
                         if callable(getattr(module, attr)) and not attr.startswith("__")]
            
            # If there's exactly one function, add it to the dictionary
            if len(functions) == 1:
                functions_dict[module_name] = functions[0]
            else:
                raise ValueError(f"File {file_name} contains more than one function or no function.")
    
    return functions_dict

def run_conversation(messages):
    with open('function.json') as f:
        tools = json.load(f)
    current_messages = [m for m in messages]
    last_message = current_messages[-1]['content']

    # First API call to get the response
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=current_messages,
        tools=tools, 
        stream = True,
        temperature=.1
    )

    tool_resp = ''
    function_name = ''
    tool_call_id = None
    is_tool_resp = False
    for chunk in response:
        delta = chunk.choices[0].delta
        tool_calls = delta.tool_calls
        if tool_calls and tool_calls[0].function.name is not None:
            if not is_tool_resp:
                current_messages.append(delta)
            function_name = tool_calls[0].function.name
            tool_call_id = tool_calls[0].id
            is_tool_resp = True

        chunk_content = delta.content
        if chunk_content is not None and not is_tool_resp:
            yield chunk_content

        else:
            if tool_calls is not None:
                tool_resp += tool_calls[0].function.arguments

    # Check if the model wants to call a function
    if is_tool_resp:
        available_functions = load_functions_from_folder('./src')

        function_to_call = available_functions[function_name]
        function_response = function_to_call()

        print(f'calling {function_to_call}')
        current_messages.append(
            {
                "tool_call_id": tool_call_id,
                "role": "tool",
                "name": function_name,
                "content": function_response,
            }
        )

        second_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=current_messages,
            stream = True,
            temperature=.1
        )

        for chunk in second_response:
            delta = chunk.choices[0].delta

            chunk_content = delta.content
            if chunk_content is not None:
                yield chunk_content

def main_app():
    st.title("Chat with MeeganAI")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
            "role": "system",
            "name": "WebBot",
            "content": f"""
                        Your are an event ai, you are to answer questions about a fake event called the Meegan Internationals.
                        """.strip().replace('\n', '')
            },
        ]

    # Accept user input
    if prompt := st.chat_input("What is up?"):
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        response = run_conversation(st.session_state.messages)

        # Display assistant message in chat message container
        with st.chat_message("assistant"):
            try:
                response_output = st.write_stream(response)
            except Exception as e:
                print(traceback.format_exc())
                response_output = st.write('Oops, I encountered an internal error, can you ask your question again?')
                response_output = 'Oops, I encountered an internal error, please refresh and ask your question again.'

            st.session_state.messages.append({"role": "assistant", "content": response_output})
            
main_app()