
DESKTOP_FILES := $(patsubst %.desktop.in,%.desktop,$(wildcard *.desktop.in))

all: countries.h languages.h $(DESKTOP_FILES)

countries.h: countries
	awk '{FS=":"; if ($$1 != "#" && $$4 != "") print "const char *s=_(\""$$4"\");"; }' $<  > $@


languages.h: languages
	awk '{FS=":"; if ($$1 != "#" && $$2 != "") print "const char *s=_(\""$$2"\");"; }' $< > $@

%.desktop: %.desktop.in 
	intltool-merge -d ../po $< $@

