import sublime
import sublime_plugin
import random, string
import json
import http.client

default_port = 443
default_provider = "openai"
default_model = "gpt-4o-mini"
default_system_role = "You are a helpful assistant. Provide very short answers with one or two lines. Always provide code blocks as raw text without surrounding them with backtricks. Please answer without backtricks"
default_color = "cyanish"
default_color_code = "#2AA198"

class Provider:
	def __init__(self, name, host, url, port=default_port):
		self.name = name
		self.api_key = ""
		self.url = url
		self.model_name = ""
		self.conn = http.client.HTTPSConnection(host, port)
		self.system_role = None
		self.set_system_role(default_system_role)

	def set_system_role(self, system_role):
		if self.system_role != system_role:
			self.system_role = system_role
			self.init_messages()

	def send_request(self):
		headers = {
			"Content-Type": "application/json"
		}
		headers.update(self.get_headers())

		data = self.get_data()

		json_data = json.dumps(data)
		
		self.conn.request("POST", self.url, body=json_data, headers=headers)
		
		response = self.conn.getresponse()
		response_data = response.read()

		self.conn.close()
		
		response_json = json.loads(response_data.decode("utf-8"))
		return self.get_answer(response_json)

	def chat(self, message):
		# print(self.messages)
		self.append_user_message(message)
		answer = self.send_request()
		self.append_assistant_message(answer)
		return answer

class OpenAIChatAPI(Provider):
	def init_messages(self):
		self.messages = [
			{"role": "system", "content": self.system_role}
		]

	def get_headers(self):
		return {
			"Authorization": "Bearer {}".format(self.api_key),
		}

	def get_data(self):
		return {
			"model": self.model_name,
			"messages": self.messages
		}

	def append_user_message(self, message):
		self.messages.append({ "role": "user", "content": message })

	def append_assistant_message(self, message):
		self.messages.append({ "role": "assistant", "content": message })

	def get_answer(self, response_json):
		return response_json["choices"][0]["message"]["content"]

class AnthropicAPI(Provider):
	def init_messages(self):
		self.messages = []

	def get_headers(self):
		return {
			"anthropic-version": "2023-06-01",
			"x-api-key": self.api_key,
		}

	def get_data(self):
		return {
			"model": self.model_name,
			"max_tokens": 1024,
			"messages": self.messages,
			"system": self.system_role
		}

	def append_user_message(self, message):
		self.messages.append({ "role": "user", "content": message })

	def append_assistant_message(self, message):
		self.messages.append({ "role": "assistant", "content": message })

	def get_answer(self, response_json):
		return response_json["content"][0]["text"]

class GeminiAPI(Provider):
	def init_messages(self):
		self.messages = []

	def get_headers(self):
		self.url = "/v1beta/models/{}:generateContent?key={}".format(self.model_name, self.api_key)
		return {}

	def get_data(self):
		return {
			"system_instruction": {
				"parts": { "text": self.system_role }
			},
			"contents": self.messages
		}

	def append_user_message(self, message):
		self.messages.append({"role":"user", "parts":[{"text": message}]})

	def append_assistant_message(self, message):
		self.messages.append({"role":"model", "parts":[{"text": message}]})

	def get_answer(self, response_json):
		return response_json["candidates"][0]["content"]["parts"][0]["text"].rstrip('\n')

openai_api = OpenAIChatAPI("openai", "api.openai.com", "/v1/chat/completions")
anthropic_api = AnthropicAPI("anthropic", "api.anthropic.com", "/v1/messages")
gemini_api = GeminiAPI("gemini", "generativelanguage.googleapis.com", "/v1/messages")

class StLlmCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		settings = sublime.load_settings("st-llm.sublime-settings")

		active_provider = settings.get("active_provider", default_provider)

		provider_settings = settings.get(active_provider, {})

		api_key = provider_settings.get("key", default_model)
		model_name = provider_settings.get("model", default_model)
		system_role = provider_settings.get("system_role", default_system_role)
		color = provider_settings.get("color", default_color)
		color_code = provider_settings.get("color_code", default_color_code)

		if active_provider == "openai":
			provider = openai_api
		elif active_provider == "anthropic":
			provider = anthropic_api
		elif active_provider == "gemini":
			provider = gemini_api

		provider.api_key = api_key
		provider.model_name = model_name
		provider.set_system_role(system_role)

		cursor_position = self.view.sel()[0].begin()
		line_region = self.view.line(cursor_position)

		current_line_text = self.view.substr(line_region)
		if current_line_text.strip():
			answer = provider.chat(current_line_text)
			key = "key_" + str(random.randint(1000, 9999))
			self.view.add_regions(key, [line_region], "region." + color, "circle", 
				sublime.DRAW_NO_OUTLINE, [model_name], color_code) # | sublime.DRAW_SQUIGGLY_UNDERLINE
			self.view.insert(edit, cursor_position, "\n\n{}\n\n".format(answer))
			self.view.show_at_center(line_region)
		else:
			print("The current line is empty.")