
all: countries.h languages.h language-selector.desktop

countries.h: countries
	awk '{FS=":"; if ($$1 != "#" && $$4 != "") print "const char *s=_(\""$$4"\");"; }' $<  > $@


languages.h: languages
	awk '{FS=":"; if ($$1 != "#" && $$2 != "") print "const char *s=_(\""$$2"\");"; }' $< > $@

language-selector.desktop: language-selector.desktop.in ../po/language-selector.pot
	intltool-merge -d ../po $< $@

