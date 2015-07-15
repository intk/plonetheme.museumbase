from ..views import ContentView
from plone.dexterity.browser.view import DefaultView
from plone.app.textfield.value import RichTextValue

class FullView(DefaultView, ContentView):


	def transform_value(self, value):
		if value == "selected":
			value = "Ja"
		return value

	def append_value(self, _list, value):
		if value != "" and value != None:
			_list.append(value)

	def generate_value_from_item(self, item, line):
		if type(item) is str:
			self.append_value(line, self.transform_value(item))
		else:
			for key in item.keys():
				self.append_value(line, self.transform_value(item[key]))

	def get_field_value(self, value, widget): 
		_type = type(value)
		if _type is list:
			try:
				result = []
				for item in value:
					line = []
					self.generate_value_from_item(item, line)
					line = ', '.join(line)
					
					result.append(line)
				result = '<p>'.join(result)
				final_result = RichTextValue(result, 'text/html', 'text/html')

				return final_result.output_relative_to(self.context)
			except:
				raise
				return value
		return value
