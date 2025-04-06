import chainlit as cl
from ollama import AsyncClient
import re

def process_thoughts(response: str):
    """Extract and format thinking patterns"""
    thoughts = re.findall(r'<think>(.*?)</think>', response, re.DOTALL | re.IGNORECASE)
    cleaned_response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE)
    return cleaned_response.strip(), thoughts

@cl.on_chat_start
async def start_chat():
    app_user = cl.user_session.get("user")
    await cl.Message(f"Hello {app_user.identifier}").send()
    print(f"User {app_user.identifier} has started a chat session.")
    cl.user_session.set("show_thoughts", False)  # Toggle for thought visibility

@cl.on_message
async def main(message: cl.Message):
    # Create response message
    response = cl.Message(content="")
    await response.send()

    # Prepare messages with history
    messages = [{"role": "system", "content": "Think step-by-step using <think></think> tags"}]
    messages.extend(cl.user_session.get("history", []))
    messages.append({"role": "user", "content": message.content})

    # Initialize variables
    full_response = ""
    current_thought = ""
    in_thought = False

    client = AsyncClient(host='http://localhost:11434')
    async for chunk in await client.chat(
        model='deepseek-r1:8b',
        messages=messages,
        stream=True,
        options={
            "temperature": 0.7,
            "num_predict": 1024
        }
    ):
        content = chunk['message']['content']
        full_response += content
        
        # Handle thought tags in stream
        for char in content:
            if char == "<":
                in_thought = True
                current_thought = ""
            elif char == ">" and in_thought:
                in_thought = False
                if current_thought.lower().startswith("think"):
                    # Start thought processing
                    await cl.Message(
                        content="Thinking ...🤔",
                        author="Thinking",
                        parent_id=response.id
                    ).send()
                elif current_thought.lower().startswith("/think"):
                    # End thought processing
                    await cl.Message(
                        content="",
                        author="Thinking",
                        parent_id=response.id
                    ).remove()
            elif in_thought:
                current_thought += char
            else:
                await response.stream_token(char)

    # Final processing
    cleaned_response, thoughts = process_thoughts(full_response)
    
    # Update final response
    response.content = cleaned_response
    await response.update()

    # Add thoughts as expandable sections
    if thoughts and cl.user_session.get("show_thoughts"):
        with cl.Sidebar(title="Internal Thoughts"):
            for i, thought in enumerate(thoughts, 1):
                with cl.Accordion(f"Thought Process #{i}", collapsed=True):
                    cl.Text(content=thought.strip(), display="inline")

    # Update history
    cl.user_session.set("history", messages + [
        {"role": "assistant", "content": full_response}
    ])

@cl.password_auth_callback
def auth():
    return cl.User(identifier="admin")