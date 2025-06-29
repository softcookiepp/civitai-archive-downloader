"""Main"""

# imports: library
from argparse import ArgumentParser
from .testing import run_tests

from . import version
from . civitai_archive import CivitaiArchiveDownloader

def main() -> None:
	"""Main"""
	parser = ArgumentParser(prog=version.PROGRAM_NAME)

	parser.add_argument('--version',
						help='Display version',
						action='store_true',
						dest='version')
	parser.add_argument("--query", "-q", help = "Search query to download everything from")
	parser.add_argument("--url", help = "URLs to get model data from, separated by commas (,)")
	parser.add_argument("--output", "-o", help = "Output directory to save model files in, defaults to civitai_archive_downloads in local dir")
	parser.add_argument("--test", help="Run tests", action = "store_true", dest = "test")

	args = parser.parse_args()
	
	
	downloader = CivitaiArchiveDownloader(args.output)

	if args.version:
		print(f'{version.PROGRAM_NAME} {version.__version__}')
		return
	if args.test:
		run_tests()
	elif not args.query is None:
		downloader.download_from_search_query(args.query)
	elif not args.url is None:
		downloader.download_model(args.url)

if __name__ == '__main__':
	main()
