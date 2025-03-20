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
    return "Dummy response for prompt: " + prompt


def canonical_wrapper(fn):
    global listener
    return lambda key: fn(listener.canonical(key))


def copy_hotkey_handler():
    global clipboard
    clipboard.append(paste())


def key_press_handler(key):
    global key_events
    key_events.append(key)


def type(controller: Controller, string, duration=0.0, delay=0.0):
    for i, character in enumerate(string):
        key = _CONTROL_CODES.get(character, character)
        try:
            controller.press(key)
            if duration > 0.0:
                sleep(duration)
            controller.release(key)
            if delay > 0.0:
                sleep(delay)

        except (ValueError, controller.InvalidKeyException):
            raise controller.InvalidCharacterException(i, character)


def process_key_events_and_clipboard():
    global key_events, clipboard
    print("Key events: ", key_events)
    print("Clipboard: ", clipboard)
    printable_keys = {Key.space: " ", Key.enter: "\n", Key.tab: "\t"}
    chars = []
    clip_iter = iter(clipboard)
    for event in key_events:
        if type(event) is KeyCode:
            if event.char == "\x11":
                chars.append(next(clip_iter, ""))
            else:
                chars.append(event.char)
        elif event in printable_keys:
            chars.append(printable_keys[event])
        elif event is Key.backspace:
            if chars: chars.pop()
    prompt = "".join(chars)
    type(Keyboard, dummy_handle_prompt(prompt), duration=0.1, delay=0.5)



def invoke_hotkey_handler():
    global invoke_state, clipboard, key_events, press_callback_dispatcher, release_callback_dispatcher, \
        wrapped_copy_hotkey_press_callback, wrapped_copy_hotkey_release_callback, key_press_handler

    if not invoke_state:
        clipboard = []; key_events = []

        press_callback_dispatcher.add_callback(wrapped_copy_hotkey_press_callback)
        release_callback_dispatcher.add_callback(wrapped_copy_hotkey_release_callback)
        press_callback_dispatcher.add_callback(key_press_handler)
        invoke_state = True
    else:
        press_callback_dispatcher.remove_callback(key_press_handler)
        press_callback_dispatcher.remove_callback(wrapped_copy_hotkey_press_callback)
        release_callback_dispatcher.remove_callback(wrapped_copy_hotkey_release_callback)
        process_key_events_and_clipboard()
        invoke_state = False


def exit_hotkey_handler():
    global listener
    listener.stop()


def stealthllm():
    global Keyboard
    Keyboard = Controller()

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