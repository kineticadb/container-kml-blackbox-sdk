import os
from os import path
import sys
import json
import argparse

# TODO: What is the right thing to do here -- raise exceptions or just print nicely and exit?

# TODO: Implement this later
def is_valid_spec(in_file_path):
	return True

# TODO: Implement this later
def is_valid_featuremem(in_file_path):
	return True

def fuse_featmem(specin, specout):

	with open(specin) as json_file_in:
		spec = json.load(json_file_in)
		for findex, afunc in enumerate(spec['functions']):
			print(f"Found function {afunc['bb_module']}:{afunc['bb_function']}")
			if "feature_memory_file" in afunc:
				print(f"\tFunction {afunc['bb_function']} has feature memory on file {afunc['feature_memory_file']}")

				if not path.exists(afunc['feature_memory_file']):
					print(f"Fatal Error: Referenced Feature Memory File {afunc['feature_memory_file']} does not exist")
					sys.exit(1)
				if not path.isfile(afunc['feature_memory_file']):
					print(f"Fatal Error: Referenced Feature Memory File {afunc['feature_memory_file']} is not a file")
					sys.exit(1)

				if not is_valid_featuremem(in_file_path = afunc['feature_memory_file']):
					print(f"Fatal Error: Referenced Feature Memory File {afunc['feature_memory_file']} is not a valid feature memory file")
					sys.exit(1)

				# OK, we have a valid feature memory file, lets fuse it into the mainline
				with open(afunc['feature_memory_file']) as featmem_json_file:
					spec["functions"][findex]["feature_memory"] = json.load(featmem_json_file)

		print(f"Writing enriched output file {specout}")
		with open(specout, "w") as json_file_out:
		    json.dump(spec, json_file_out, sort_keys=False, indent=4)

	return True

def main():

	parser = argparse.ArgumentParser()
	parser.add_argument('--spec-in', type=str, help='Introspectable file path, original (input)')
	parser.add_argument('--spec-out', type=str, help='Introspectable file path, enriched (output)')
	parser.add_argument('--validate-only', action='store_true', required=False)
	args = parser.parse_args()

	# Input file checks

	if not path.exists(args.spec_in):
		raise Exception(f"Specificed input specification [{args.spec_in}] does not exist")
		sys.exit(1)

	if not path.isfile(args.spec_in):
		raise Exception(f"Specificed input specification [{args.spec_in}] is not a file")
		sys.exit(1)

	if not is_valid_spec(args.spec_in):
		raise Exception(f"Specificed input specification [{args.spec_in}] is not a valid spec file")
		sys.exit(1)

	# Output file checks

	if args.spec_out:
		if path.exists(args.spec_out) and not path.isfile(args.spec_out):
			raise Exception(f"Specificed out specification [{args.spec_out}] is a directory, not a valid output filename")
			sys.exit(1)

	# TODO: Figure out why this always returns "not writeable"
	#if not os.access(args.spec_out, os.W_OK):
	#	raise Exception(f"Specificed out specification [{args.spec_out}] is not writeable")
	#	sys.exit(1)

	# if we are not validating, we will always need an output file
	if not args.validate_only and not args.spec_out:
		raise Exception("When processing files (not just validating), an output file must be specified")
		sys.exit(1)

	# if we are [only] validating, the output file is irrelevant
	if args.validate_only and args.spec_out:
		raise Exception("Validating files does not required an output file")
		sys.exit(1)

	########################################################################
	# Validate only function
	if args.validate_only:
		print("We will only be validating")
		if is_valid_spec(in_file_path=args.spec_in):
			print("Input specification is valid")
		else:
			print("Input specification is NOT valid")
		sys.exit(0)
	########################################################################
	# Fuse Spec file with Feature Memory

	fuse_featmem(specin=args.spec_in, specout=args.spec_out)

	sys.exit(0)


if __name__== "__main__":
	print("")
	print(r" __                        ___           ")
	print(r"/ _\_ __   ___  ___       / _ \___ _ __  ")
	print(r"\ \| '_ \ / _ \/ __|____ / /_\/ _ \ '_ \ ")
	print(r"_\ \ |_) |  __/ (_|_____/ /_\\  __/ | | |")
	print(r"\__/ .__/ \___|\___|    \____/\___|_| |_|")
	print(r"   |_|                                   ")
	print("")
	print("Introspectable Spec Validator")
	print("(c) 2020 Kinetica DB, Inc.")
	print("For support, reach support@kinetica.com")
	print("")
	main()
	print("")