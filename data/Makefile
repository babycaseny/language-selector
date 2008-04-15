
DESKTOP_FILES := $(patsubst %.desktop.in,%.desktop,$(wildcard *.desktop.in))
NOTE_FILES := $(patsubst %.note.in,%.note,$(wildcard *.note.in))

all: $(DESKTOP_FILES) $(NOTE_FILES)

%.desktop: %.desktop.in 
	intltool-merge -d ../po $< $@

%.note: %.note.in
	intltool-merge --rfc822deb-style ../po $< $@
