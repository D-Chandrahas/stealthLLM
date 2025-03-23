from os import environ as env
from time import sleep
from threading import Thread
from pyperclip import paste
from pynput.keyboard import Listener, HotKey, Key, KeyCode, Controller, _CONTROL_CODES
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


def canonical_wrapper(fn):
    global LISTENER
    return lambda key: fn(LISTENER.canonical(key))


def copy_hotkey_handler():
    global CLIPBOARD_EVENTS
    sleep(0.1)
    CLIPBOARD_EVENTS.append(paste())


def key_press_handler(key):
    global KEY_EVENTS
    KEY_EVENTS.append(key)


def write(string, duration=0.0, delay=0.0):
    global STATE, KEYBOARD

    for i, character in enumerate(string):
        if INTERRUPT: break
        key = _CONTROL_CODES.get(character, character)
        try:
            KEYBOARD.press(key)
            if duration > 0.0:
                sleep(duration)
            KEYBOARD.release(key)
            if delay > 0.0:
                sleep(delay)

        except (ValueError, KEYBOARD.InvalidKeyException):
            raise KEYBOARD.InvalidCharacterException(i, character)


def process_key_events_and_clipboard():
    global KEY_EVENTS, CLIPBOARD_EVENTS, STATE, INTERRUPT
    try:
        printable_keys = {Key.space: " ", Key.enter: "\n", Key.tab: "\t"}
        chars = []
        clip_iter = iter(CLIPBOARD_EVENTS)
        for event in KEY_EVENTS:
            if type(event) is KeyCode:
                ascii_code = ord(event.char)
                if ascii_code == 3:
                    chars.append(next(clip_iter, ""))
                elif ascii_code >= 32 and ascii_code <= 126:
                    chars.append(event.char)
            elif event in printable_keys:
                chars.append(printable_keys[event])
            elif event is Key.backspace:
                if chars: chars.pop()
        prompt = "".join(chars)
        if prompt:
            llm_output = handle_prompt(prompt)
            llm_output = llm_output.replace("\t", "    ")
            write(llm_output, duration=0.05, delay=0.2)
    except Exception:
        pass
    finally:
        STATE = "inactive"
        INTERRUPT = False


def invoke_hotkey_handler():
    global STATE, CLIPBOARD_EVENTS, KEY_EVENTS, PRESS_CALLBACK_DISPATCHER, RELEASE_CALLBACK_DISPATCHER, \
        WRAPPED_COPY_HOTKEY_PRESS_CALLBACK, WRAPPED_COPY_HOTKEY_RELEASE_CALLBACK, key_press_handler

    if STATE == "inactive":
        CLIPBOARD_EVENTS = []; KEY_EVENTS = []

        PRESS_CALLBACK_DISPATCHER.add_callback(WRAPPED_COPY_HOTKEY_PRESS_CALLBACK)
        RELEASE_CALLBACK_DISPATCHER.add_callback(WRAPPED_COPY_HOTKEY_RELEASE_CALLBACK)
        PRESS_CALLBACK_DISPATCHER.add_callback(key_press_handler)
        STATE = "listening"
    elif STATE == "listening":
        PRESS_CALLBACK_DISPATCHER.remove_callback(key_press_handler)
        PRESS_CALLBACK_DISPATCHER.remove_callback(WRAPPED_COPY_HOTKEY_PRESS_CALLBACK)
        RELEASE_CALLBACK_DISPATCHER.remove_callback(WRAPPED_COPY_HOTKEY_RELEASE_CALLBACK)
        STATE = "processing"
        Thread(target=process_key_events_and_clipboard).start()


def interrupt_hotkey_handler():
    global STATE, INTERRUPT, LISTENER
    if STATE == "inactive":
        LISTENER.stop()
    elif STATE == "listening":
        PRESS_CALLBACK_DISPATCHER.remove_callback(key_press_handler)
        PRESS_CALLBACK_DISPATCHER.remove_callback(WRAPPED_COPY_HOTKEY_PRESS_CALLBACK)
        RELEASE_CALLBACK_DISPATCHER.remove_callback(WRAPPED_COPY_HOTKEY_RELEASE_CALLBACK)
        STATE = "inactive"
    else:
        INTERRUPT = True


def stealthllm():
    global KEYBOARD
    KEYBOARD = Controller()

    global STATE, INTERRUPT
    STATE = "inactive"
    INTERRUPT = False

    global WRAPPED_COPY_HOTKEY_PRESS_CALLBACK, WRAPPED_COPY_HOTKEY_RELEASE_CALLBACK
    copy_hotkey = HotKey(HotKey.parse("<ctrl>+c"), copy_hotkey_handler)
    WRAPPED_COPY_HOTKEY_PRESS_CALLBACK = canonical_wrapper(copy_hotkey.press)
    WRAPPED_COPY_HOTKEY_RELEASE_CALLBACK = canonical_wrapper(copy_hotkey.release)

    global PRESS_CALLBACK_DISPATCHER, RELEASE_CALLBACK_DISPATCHER
    interrupt_hotkey = HotKey(HotKey.parse("<ctrl>+<alt>+q"), interrupt_hotkey_handler)
    invoke_hotkey = HotKey(HotKey.parse("<ctrl>+<shift>+q"), invoke_hotkey_handler)
    PRESS_CALLBACK_DISPATCHER = CallbackDispatcher((canonical_wrapper(interrupt_hotkey.press),
                                                    canonical_wrapper(invoke_hotkey.press)))
    RELEASE_CALLBACK_DISPATCHER = CallbackDispatcher((canonical_wrapper(interrupt_hotkey.release),
                                                      canonical_wrapper(invoke_hotkey.release)))

    global LISTENER
    LISTENER = Listener(on_press=PRESS_CALLBACK_DISPATCHER, on_release=RELEASE_CALLBACK_DISPATCHER)
    LISTENER.start()
    LISTENER.join()


class CallbackDispatcher:
    def __init__(self, callbacks):
        self.callbacks = list(callbacks)
    
    def add_callback(self, callback):
        self.callbacks.append(callback)

    def remove_callback(self, callback):
        try:
            self.callbacks.remove(callback)
        except ValueError:
            pass

    def __call__(self, key):
        for callback in self.callbacks:
            callback(key)


if __name__ == "__main__":
    stealthllm()