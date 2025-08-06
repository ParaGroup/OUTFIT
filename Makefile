SCRIPT = src/collect_data_gui.py
EXECUTABLE = OUTFIT
ICON_NAME = outfit_rounded

# Detect OS
UNAME_S := $(shell uname -s)


ifeq ($(OS),Windows_NT)
    OS_TYPE = Windows
    EXEC_EXT = .exe
    ICON = icons\$(ICON_NAME).ico
    RM = del /Q /F
    RMDIR = rmdir /S /Q
	MV = move /Y
else ifeq ($(UNAME_S),Darwin)
    OS_TYPE = macOS
    EXEC_EXT = .app
    ICON = icons/$(ICON_NAME).icns
    RM = rm -f
    RMDIR = rm -rf
	MV = mv -f
else
    OS_TYPE = Linux
    EXEC_EXT =
    ICON = icons\$(ICON_NAME).ico
    RM = rm -f
    RMDIR = rm -rf
	MV = mv -f
endif

PYINSTALLER_FLAGS = --onefile --name $(EXECUTABLE) --icon $(ICON) --noconsole

# === Targets ===
all: build

build:
	pyinstaller $(PYINSTALLER_FLAGS) $(SCRIPT)
	$(MV) dist/$(EXECUTABLE)$(EXEC_EXT) .
	$(MAKE) clean

run: build
	./dist/$(EXECUTABLE)$(EXEC_EXT)

clean:
	-$(RM) *.spec
	-$(RMDIR) build dist __pycache__
