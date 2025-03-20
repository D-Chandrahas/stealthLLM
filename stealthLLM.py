from os import environ as env
from time import sleep
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


def dummy_handle_prompt(prompt):
    sleep(2)
    return "Dummy: " + prompt


def canonical_wrapper(fn):
    global listener
    return lambda key: fn(listener.canonical(key))


def copy_hotkey_handler():
    global clipboard_events
    sleep(0.1)
    clipboard_events.append(paste())


def key_press_handler(key):
    global key_events
    key_events.append(key)


def write(string, duration=0.0, delay=0.0):
    global keyboard
    for i, character in enumerate(string):
        key = _CONTROL_CODES.get(character, character)
        try:
            keyboard.press(key)
            if duration > 0.0:
                sleep(duration)
            keyboard.release(key)
            if delay > 0.0:
                sleep(delay)

        except (ValueError, keyboard.InvalidKeyException):
            raise keyboard.InvalidCharacterException(i, character)


def process_key_events_and_clipboard():
    global key_events, clipboard_events
    
    printable_keys = {Key.space: " ", Key.enter: "\n", Key.tab: "\t"}
    chars = []
    clip_iter = iter(clipboard_events)
    for event in key_events:
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
    write(handle_prompt(prompt), duration=0.05, delay=0.2)



def invoke_hotkey_handler():
    global invoke_state, clipboard_events, key_events, press_callback_dispatcher, release_callback_dispatcher, \
        wrapped_copy_hotkey_press_callback, wrapped_copy_hotkey_release_callback, key_press_handler

    if not invoke_state:
        invoke_state = True
        clipboard_events = []; key_events = []

        press_callback_dispatcher.add_callback(wrapped_copy_hotkey_press_callback)
        release_callback_dispatcher.add_callback(wrapped_copy_hotkey_release_callback)
        press_callback_dispatcher.add_callback(key_press_handler)
    else:
        invoke_state = False
        press_callback_dispatcher.remove_callback(key_press_handler)
        press_callback_dispatcher.remove_callback(wrapped_copy_hotkey_press_callback)
        release_callback_dispatcher.remove_callback(wrapped_copy_hotkey_release_callback)
        process_key_events_and_clipboard()


def exit_hotkey_handler():
    global listener
    listener.stop()


def stealthllm():
    global keyboard
    keyboard = Controller()

    global invoke_state
    invoke_state = False

    global wrapped_copy_hotkey_press_callback, wrapped_copy_hotkey_release_callback
    copy_hotkey = HotKey(HotKey.parse("<ctrl>+c"), copy_hotkey_handler)
    wrapped_copy_hotkey_press_callback = canonical_wrapper(copy_hotkey.press)
    wrapped_copy_hotkey_release_callback = canonical_wrapper(copy_hotkey.release)

    global press_callback_dispatcher, release_callback_dispatcher
    invoke_hotkey = HotKey(HotKey.parse("<ctrl>+<shift>+q"), invoke_hotkey_handler)
    exit_hotkey = HotKey(HotKey.parse("<ctrl>+<alt>+q"), exit_hotkey_handler)
    press_callback_dispatcher = CallbackDispatcher((canonical_wrapper(invoke_hotkey.press), canonical_wrapper(exit_hotkey.press)))
    release_callback_dispatcher = CallbackDispatcher((canonical_wrapper(invoke_hotkey.release), canonical_wrapper(exit_hotkey.release)))

    global listener
    listener = Listener(on_press=press_callback_dispatcher, on_release=release_callback_dispatcher)
    listener.start()
    listener.join()


class CallbackDispatcher:
    def __init__(self, callbacks):
        self.callbacks = list(callbacks)
    
    def add_callback(self, callback):
        self.callbacks.append(callback)

    def remove_callback(self, callback):
        self.callbacks.remove(callback)

    def __call__(self, key):
        for callback in self.callbacks:
            callback(key)


if __name__ == "__main__":
    stealthllm()