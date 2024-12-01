import sublime
import sublime_plugin
import random, string
import json
import http.client

default_provider = "openai"
default_model = "gpt-4o-mini"
default_system_role = "You are a helpful assistant. Provide very short answers with one or two lines. Always provide code blocks as raw text without surrounding them with backtricks. Please answer without backtricks"
default_color = "cyanish"
default_color_code = "#2AA198"

class OpenAIChatAPI:
	def __init__(self, api_key):
		self.api_key = api_key
		self.conn = http.client.HTTPSConnection("api.openai.com")
		self.system_role = None
		self.set_system_role(default_system_role)

	def set_system_role(self, system_role):
		if self.system_role != system_role:
			self.system_role = system_role
			self.messages = [
				{"role": "system", "content": system_role}
			]

	def send_request(self, model=model_name, messages=None):
		if messages is None:
			messages = [
				{"role": "system", "content": default_system_role}
			]
		
		headers = {
			"Authorization": "Bearer {}".format(self.api_key),
			"Content-Type": "application/json"
		}
		
		data = {
			"model": model,
			"messages": messages
		}
		
		json_data = json.dumps(data)
		
		self.conn.request("POST", "/v1/chat/completions", body=json_data, headers=headers)
		
		response = self.conn.getresponse()
		response_data = response.read()

		self.conn.close()
		
		response_json = json.loads(response_data.decode("utf-8"))
		return response_json["choices"][0]["message"]["content"]

	def chat(self, message):
		# print(self.messages)
		self.messages.append({ "role": "user", "content": message })
		answer = self.send_request(model_name, self.messages)
		self.messages.append({ "role": "assistant", "content": answer })
		return answer

class AnthropicAPI:
	def __init__(self, api_key):
		self.api_key = api_key
		self.conn = http.client.HTTPSConnection("api.anthropic.com")
		self.system_role = None
		self.set_system_role(default_system_role)

	def set_system_role(self, system_role):
		if self.system_role != system_role:
			self.system_role = system_role
			self.messages = []

	def send_request(self, model=model_name, messages=None):
		if messages is None:
			messages = []
		
		headers = {
			"Authorization": "Bearer {}".format(self.api_key),
			"anthropic-version": "2023-06-01",
			"Content-Type": "application/json",
			"x-api-key": self.api_key,
		}
		
		data = {
			"model": model,
			"max_tokens": 1024,
			"messages": messages,
			"system": self.system_role
		}
		
		json_data = json.dumps(data)
		
		self.conn.request("POST", "/v1/messages", body=json_data, headers=headers)
		
		response = self.conn.getresponse()
		response_data = response.read()

		self.conn.close()
		
		response_json = json.loads(response_data.decode("utf-8"))
		print(response_json)
		return response_json["content"][0]["text"]

	def chat(self, message):
		# print(self.messages)
		self.messages.append({ "role": "user", "content": message })
		answer = self.send_request(self.model_name, self.messages)
		self.messages.append({ "role": "assistant", "content": answer })
		return answer

openai_api = OpenAIChatAPI("")
anthropic_api = AnthropicAPI("")

class StLlmCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		settings = sublime.load_settings("st-llm.sublime-settings")

		active_provider = settings.get("active_provider", default_provider)

		provider_settings = settings.get(active_provider, {})

		api_key = provider_settings.get("key", default_model)
		model_name = provider_settings.get("model", default_model)
		system_role = provider_settings.get("system_role", default_system_role)
		color = provider_settings.get("color", default_color)
		color_code = provider_settings.get("color", default_color)

		if active_provider == "openai":
			provider = openai_api
		elif active_provider == "anthropic":
			provider = anthropic_api

		provider.api_key = api_key
		provider.set_system_role(system_role)
		provider.model_name = model_name

		cursor_position = self.view.sel()[0].begin()
		line_region = self.view.line(cursor_position)

		current_line_text = self.view.substr(line_region)
		if current_line_text.strip():
			answer = provider.chat(current_line_text)
			key = "key_" + str(random.randint(1000, 9999))
			self.view.add_regions(key, [line_region], "region." + color, "circle", 
				sublime.DRAW_NO_OUTLINE, [model_name], "#2AA198") # | sublime.DRAW_SQUIGGLY_UNDERLINE
			self.view.insert(edit, cursor_position, "\n\n{}\n\n".format(answer))
			self.view.show_at_center(line_region)
		else:
			print("The current line is empty.")