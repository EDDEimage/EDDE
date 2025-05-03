# Makefile for building and installing multi-directory Go project

# Binary output directory
BINDIR ?= $(PWD)/bin
# Default GOBIN
GOBIN ?= $(BINDIR)

# List of module directories containing Go packages or main programs
MODULES = \
	client \
	cmd \
	fs \
	graphdriver \
	manage \
	monitor \
	pkg \
	push \
	type \

# Derive binary names from directory names
BINS = $(foreach dir,$(MODULES),$(notdir $(dir)))

# Default target
all: build

.PHONY: all build install clean test

# Build all modules
build:
	@echo "🚀 Building all components..."
	@mkdir -p $(BINDIR)
	$(foreach dir,$(MODULES), \
		echo "🔧 Building module: $(dir)"; \
		cd $(dir) && go build -o ../$(BINDIR)/$(notdir $(dir)) && cd ..; \
	)

# Install binaries to system path (e.g., /usr/local/bin)
install: build
	@echo "📦 Installing binaries to /usr/local/bin"
	sudo cp $(BINDIR)/* /usr/local/bin/

# Run tests
test:
	@echo "🧪 Running tests..."
	$(foreach dir,$(MODULES), \
		echo "🧪 Testing module: $(dir)"; \
		cd $(dir) && go test ./... && cd ..; \
	)

# Clean up build artifacts
clean:
	@echo "🧹 Cleaning up..."
	rm -rf $(BINDIR)/*