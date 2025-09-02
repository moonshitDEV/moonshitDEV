# Root Makefile delegating to projects/dashboard

.DEFAULT_GOAL := help

SUBDIR := projects/dashboard

help:
	@$(MAKE) -C $(SUBDIR) help

%:
	@$(MAKE) -C $(SUBDIR) $@
