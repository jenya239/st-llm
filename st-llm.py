import sublime
import sublime_plugin
import random, string
import json
import http.client

default_port = 443
default_protocol = "https"
default_provider = "openai"
default_model = "gpt-4o-mini"
default_system_role = "You are a helpful assistant. Provide very short answers with one or two lines. Answer without code blocks formatting"
default_color = "cyanish"
default_color_code = "#2AA198"

brainstorm_role = "You are a participant in a brainstorming session with other models. Your task is to give short answers and quickly reach a consensus. The answers of other participants will be transmitted in one message in the format 'name: message'. a simpler, less enthusiastic tone and mention the names of the interlocutors, sometimes ask them who they are, keep the smalltalk going. you can joke"
brainstorm_rounds = 10

class Provider:
	def __init__(self, name, settings, key):
		self.name = name
		self.settings = settings
		self.api_key = key
		self.url = settings.get("url", "")
		self.model_name = settings.get("model", default_model)
		self.protocol = settings.get("protocol", default_protocol)
		self.host = settings.get("host", "")
		self.port = settings.get("port", default_port)
		self.conn = http.client.HTTPSConnection(self.host, self.port) if self.protocol == "https" else http.client.HTTPConnection(self.host, self.port)
		self.system_role = None
		self.restore_role()
		self.color = settings.get("color", default_color)
		self.color_code = settings.get("color_code", default_color_code)

	def set_system_role(self, system_role):
		if self.system_role != system_role:
			self.system_role = system_role
			self.init_messages()

	def restore_role(self):
		self.set_system_role(self.settings.get("system_role", default_system_role))

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
		print(response_json)
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


class OllamaAPI(Provider):
	def init_messages(self):
		self.messages = [
			{"role": "assistant", "content": self.system_role}
		]

	def get_headers(self):
		return {}

	def get_data(self):
		return {
			"model": self.model_name,
			"messages": self.messages,
			"stream": False
		}

	def append_user_message(self, message):
		self.messages.append({ "role": "user", "content": message })

	def append_assistant_message(self, message):
		self.messages.append({ "role": "assistant", "content": message })

	def get_answer(self, response_json):
		return response_json["message"]["content"]


class XAIChatAPI(Provider):
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
			"messages": self.messages,
			"stream": False,
			"temperature": 0
		}

	def append_user_message(self, message):
		self.messages.append({ "role": "user", "content": message })

	def append_assistant_message(self, message):
		self.messages.append({ "role": "assistant", "content": message })

	def get_answer(self, response_json):
		return response_json["choices"][0]["message"]["content"]


class Brainstorm:
	def __init__(self, providers):
		self.providers = providers

	def chat(self, message):
		print('brainstorm')
		return "brainstorm {}".format(message)

	def start(self):
		for provider in self.providers:
			provider.set_system_role(brainstorm_role)



providers = {}
provider = None
brainstorm = None

def plugin_loaded():
	global provider, providers, brainstorm
	settings = sublime.load_settings("st-llm.sublime-settings")
	active_provider = settings.get("active_provider", default_provider)
	keys = settings.get("keys", {})

	provider_settings = settings.get(active_provider, {})

	providers['openai'] = OpenAIChatAPI("openai", settings.get("openai", {}), keys.get("openai", ""))
	providers['anthropic'] = AnthropicAPI("anthropic", settings.get("anthropic", {}), keys.get("anthropic", ""))
	providers['gemini'] = GeminiAPI("gemini", settings.get("gemini", {}), keys.get("gemini", ""))
	providers['ollama'] = OllamaAPI("ollama", settings.get("ollama", {}), "")
	providers['xai'] = XAIChatAPI("xai", settings.get("xai", {}), keys.get("xai", ""))

	provider = providers[active_provider]

	brainstorm_providers = [providers['openai'], providers['anthropic'], providers['gemini']]
	brainstorm = Brainstorm(brainstorm_providers)
	print("Plugin loaded successfully! active_provider = "+provider.name)

class StLlmCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		for p in providers.values():
			p.restore_role()

		cursor_position = self.view.sel()[0].begin()
		line_region = self.view.line(cursor_position)

		current_line_text = self.view.substr(line_region)
		if current_line_text.strip():
			answer = provider.chat(current_line_text)
			key = "key_" + str(random.randint(1000, 9999))
			self.view.add_regions(key, [line_region], "region." + provider.color, "circle", 
				sublime.DRAW_NO_OUTLINE, [provider.model_name], provider.color_code) # | sublime.DRAW_SQUIGGLY_UNDERLINE
			self.view.insert(edit, cursor_position, "\n\n{}\n\n".format(answer))
			self.view.show_at_center(line_region)
		else:
			print("The current line is empty.")

class StLlmBrainstormCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		brainstorm.start()

		cursor_position = self.view.sel()[0].begin()
		line_region = self.view.line(cursor_position)

		current_line_text = self.view.substr(line_region)
		if current_line_text.strip():
			answer = brainstorm.chat(current_line_text)
			key = "key_" + str(random.randint(1000, 9999))
			self.view.add_regions(key, [line_region], "region.cyanish", "circle", 
				sublime.DRAW_NO_OUTLINE, ['brainstorm'], '#2AA198') # | sublime.DRAW_SQUIGGLY_UNDERLINE

			messages = [{"role": "user", "content": current_line_text}]
			for r in range(brainstorm_rounds):
				for i, provider in enumerate(brainstorm.providers):
					msg = ""
					for m in messages:
						msg += "{}: {}\n\n".format(m["role"], m["content"])
					print(msg)
					answer = provider.chat(msg)
					messages.append({"role": provider.name, "content": answer})
					cursor_position = self.view.sel()[0].begin()
					self.view.insert(edit, cursor_position, "\n\n{}: {}".format(provider.name, answer))
				# messages = []

			self.view.show_at_center(line_region)
		else:
			print("The current line is empty.")