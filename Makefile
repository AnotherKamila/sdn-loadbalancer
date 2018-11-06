# sdn-nat64 makefile
# type `make help` to see available targets

OUT = ./out/

.PHONY: default help clean clean-gitignore live

default: help

# -- USER RELEVANT -- #

#TODO stuff

# -- THE TARGETS THAT ACTUALLY DO STUFF -- #

#TODO stuff

# -- HELPERS -- #

#TODO stuff

help:  # stolen from marmelab.com/blog/2016/02/29/auto-documented-makefile.html
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "%-10s %s\n", $$1, $$2}'

clean:  ## Cleans generated files
	rm -rf $(OUT)

clean-all:  ## Removes all files listed in ./.gitignore
	rm -rf $$(cat ./.gitignore | grep -v '^#')
