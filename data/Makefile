
DESKTOP_FILES := $(patsubst %.desktop.in,%.desktop,$(wildcard *.desktop.in))

all: $(DESKTOP_FILES)


%.desktop: %.desktop.in 
	intltool-merge -d ../po $< $@

