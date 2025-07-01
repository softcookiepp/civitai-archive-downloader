import requests
from selectolax.parser import HTMLParser
import os
from . import parsing
import json
import hashlib

def _mkdir(d):
	if not os.path.exists(d):
		os.mkdir(d)

class CivitaiArchiveDownloader:
	def __init__(self, root_dir = None, api_key = None):
		self._root_dir = root_dir
		if root_dir is None:
			"just default to ./civitai_archive_downloads"
			self._root_dir = os.path.join(os.getcwd(), "civitai_archive_downloads")
			_mkdir(self._root_dir)
		self._api_key = api_key
		if api_key is None:
			if "CIVITAI_API_KEY" in os.environ.keys():
				self._api_key = os.environ["CIVITAI_API_KEY"]
		self._last_rsp = None
	
	def _get(self, url : str, headers = {}, data = {}, params = {}, full_url = False):	
		if "civitai.com" in url:
			params["token"] = self._api_key
		self._last_rsp = requests.get(url, headers = headers, data = data,
			params = params)
		return self._last_rsp

	def _get_file_metadata(self, files):
		mirrors = {}
		for file_hash, _ in files.items():
			rsp = self._get(f"https://civitaiarchive.com/api/sha256/{file_hash}")
			mirrors[file_hash] = json.loads(rsp.text)
		return mirrors
		
	def _get_large_file(self, file_path : str, url : str,
			headers = {}, data = {}, params = {}, full_url = False):
		
		# make temporary file path for downloading
		final_path = file_path
		if file_path[-1] == "/" or file_path[-1] == "\\":
			file_path = file_path[0:len(file_path) - 1]
		file_path = file_path + ".tmp"
		
		if os.path.exists(final_path):
			if os.path.exists(file_path):
				# remove temp file
				os.remove(file_path)
			return final_path
		
		# initialize file
		offset = 0
		if os.path.exists(file_path):
			offset = os.path.getsize(file_path)
			print(f"{offset} bytes downloaded so far, resuming download")
			f = open(file_path, "ab")
		else:
			f = open(file_path, "wb")
		
		while True:
			# NOTE the stream=True parameter below
			encountered_error = False
			headers.update( {"Range": f"bytes={offset}-"} )
			with self._get(url, stream=True, headers = headers,
					data = {}, params = {}) as r:
				try:
					if r.status_code == 404:
						return None
					r.raise_for_status()
					for chunk in r.iter_content(chunk_size=8192): 
						# If you have chunk encoded response uncomment if
						# and set chunk_size parameter to None.
						if chunk:
							f.write(chunk)
						else:
							# Connection got interrupted, try again
							assert False
				except:
					# Connection got interrupted, try again
					print("Connection interrupted, trying again")
					encountered_error = True
					break
			offset = os.path.getsize(file_path)
				
			if not encountered_error:
				break

		# close temp file, rename
		f.close()
		os.rename(file_path, final_path)
		
		# all done!
		return final_path
	
	def download_from_search_query(self, query, is_nsfw = True, is_deleted = False):
		rsp = self._get("https://civitaiarchive.com/api/search",
			params = {"q": query, "is_nsfw": is_nsfw, "is_deleted": is_deleted})
		rsp_json = json.loads(rsp.text)
		for item in rsp_json["results"]:
			if "/models/" in item["url"]:
				self.download_model(f"https://civitaiarchive.com{item['url']}")

	def download_model(self, url: str, version = "all"):
		"""
		Directory heirarchy should really be...
		- Content category (model, lora, etc.)
			- Model folder
				- version folders
					- images folder
						- images
					- model files
					- webpage archive
					- metadata file derived from archive
		"""
		rsp = self._get(url)
		top_level_metadata = parsing.get_model_page_metadata(rsp.text)
		
		# create directory for content category and model base
		cat_path = os.path.join(self._root_dir, top_level_metadata["content_type"])
		_mkdir(cat_path)
		base_path = os.path.join(cat_path, top_level_metadata["base_model"])
		_mkdir(base_path)
		
		# totally forgot about the model name path itself
		model_path = os.path.join(base_path, top_level_metadata["model_name"])
		_mkdir(model_path)
		
		# now iterate over each version
		versions = parsing.get_model_versions(rsp.text)
		for version_name, version_url in versions.items():
			# make directory for the version
			version_path = os.path.join(model_path, version_name)
			_mkdir(version_path)
			
			# get remaining version metadata if needed
			rsp = self._get(version_url)
			version_metadata = parsing.get_version_metadata(rsp.text)
			version_metadata.update(top_level_metadata)
			
			# now to dump it?
			version_meta_path = os.path.join(version_path, "metadata.json")
			with open(version_meta_path, "w") as f:
				json.dump(version_metadata, f, indent = 3)
			
			# thats easy. Now we actually save it!
			files = parsing.get_file_hashes(rsp.text)
			meta = self._get_file_metadata(files)
			for (file_hash, file_name), (_, metadata) in zip(files.items(), meta.items() ):
				file_path = os.path.join(version_path, metadata["files"][0]["filename"])
				print("downloading to:", file_path)
				success = False
				for mirror in metadata["files"]:
					# try each mirror to see if it works
					rsp = self._get(mirror["url"] )
					
					if rsp.status_code == 200:
						with open(file_path, "wb") as f:
							f.write(rsp.content)
						
						# gotta handle error implementing at some point
						success = True
						break
					else:
						print(f"Download failed with error {rsp.status_code}, trying a different mirror...")
				if success:
					print("Download successful!")
					json_path = os.path.join(version_path, f"{file_name}.json")
					with open(json_path, "w") as f:
						json.dump(metadata, f, indent = 3)
				else:
					print(f"None of the mirrors worked for {file_name}")
		
