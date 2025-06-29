from selectolax.parser import HTMLParser

def _make_file_name(inp):
	return inp.lower().strip("	 \n\t\r").replace(" ", "_").replace("\\", "-").replace("/", "-")

def get_file_hashes(html: str):
	parser = HTMLParser(html)
	
	# hash, filename
	files = {}
	for files_container in parser.select('[class="flex flex-col gap-2 p-6 rounded-xl border space-y-2"]').matches:
		file_elem = files_container.select("div").matches[0]
		while not file_elem is None:
			
			# now we get the filename and hash
			file_name = file_elem.select("p").matches[0].text()
			file_hash = file_elem.select("div").matches[0].select("a").matches[0].attributes["href"].strip("/").split("/")[1]
			files[file_hash] = file_name
			file_elem = file_elem.next
			
	return files
	
def _find_trigger_words(parser: HTMLParser):
	trigger_words = []
	for container_elem in parser.select('[class="space-y-4"]').matches:
		# Just look through all the spans
		for item in container_elem.select("span").matches:
			if "Trigger Words:" == item.text().strip("	 \n\t\r"):
				item = item.next
				while not item is None:
					trigger_words.append(item.text().strip("	 \n\t\r") )
					item = item.next
	return trigger_words
	
def get_model_versions(html: str):
	parser = HTMLParser(html)
	versions = {}
	for block in parser.select('[class="inline-block"]').matches:
		if "href" in block.attributes.keys() and "modelVersionId" in block.attributes["href"]:
			versions[_make_file_name(block.text() )] = f"https://civitaiarchive.com{block.attributes['href']}"
	return versions
			
		
def get_model_page_metadata(html: str):
	parser = HTMLParser(html)
	
	meta = {}
	
	type_container = parser.select('[class="flex items-center gap-3"]').matches[0]
	type_list = type_container.select("div").matches[1:]
	meta["content_type"] = _make_file_name(type_list[0].text() )
	meta["base_model"] = _make_file_name(type_list[1].text() )
	return meta
	
def get_version_metadata(html: str):
	parser = HTMLParser(html)
	meta = {}
	meta["images"] = []
	for img_elem in parser.select("img").matches:
		meta["images"].append(img_elem.attributes["src"])
	meta["trigger_words"] = _find_trigger_words(parser)
	return meta
