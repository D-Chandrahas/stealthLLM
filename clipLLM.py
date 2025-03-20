from os import environ as env
from time import sleep
from pyperclip import paste, copy
import requests as req

def handle_prompt(prompt):
    return req.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
                    json={
                        "contents": [{
                            "parts":[{"text": prompt}]
                        }]
                    },
                    params={"key": env["GEMINI_API_KEY"]}
        ).json()["candidates"][0]["content"]["parts"][0]["text"]

def dummy_handle_prompt(prompt):
    return "Dummy response for prompt: " + prompt

def clipllm():
    while True:
        cmd = paste()
        if cmd == "Kill-ClipLLM":
            break
        elif cmd == "Invoke-ClipLLM":
            copy("ClipLLM: Waiting for prompt...")
            while True:
                cmd = paste()
                if cmd == "Exit-ClipLLM":
                    break
                elif cmd == "ClipLLM: Waiting for prompt...":
                    sleep(1)
                else:
                    copy(handle_prompt(cmd))
                    break
        sleep(3)

if __name__ == "__main__":
    clipllm()