import sublime
import sublime_plugin
import random, string
import json
import http.client

default_model = "gpt-4o-mini"
default_system_role = "You are a helpful assistant. Provide very short answers with one or two lines. Always provide code blocks as raw text without surrounding them with backtricks. Please answer without backtricks"

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
				{"role": "system", "content": "You are a helpful assistant. Provide very short answers with one or two lines. Always provide code blocks as raw text without surrounding them with ```."}
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

openai_api = OpenAIChatAPI("")

class StLlmCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		settings = sublime.load_settings("st-llm.sublime-settings")

		api_key = settings.get("api_key", "")
		model_name = settings.get("model_name", default_model)
		system_role = settings.get("system_role", default_system_role)

		openai_api.api_key = api_key
		openai_api.set_system_role(system_role)

		cursor_position = self.view.sel()[0].begin()
		line_region = self.view.line(cursor_position)

		current_line_text = self.view.substr(line_region)
		if current_line_text.strip():
			answer = openai_api.chat(current_line_text)
			key = "key_" + str(random.randint(1000, 9999))
			self.view.add_regions(key, [line_region], "region.cyanish", "circle", 
				sublime.DRAW_NO_OUTLINE, [model_name], "#2AA198") # | sublime.DRAW_SQUIGGLY_UNDERLINE
			self.view.insert(edit, cursor_position, "\n\n{}\n\n".format(answer))
			self.view.show_at_center(line_region)
		else:
			print("The current line is empty.")