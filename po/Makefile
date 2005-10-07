
PO_FILES := $(wildcard *.po)

update-po: language-selector.pot $(patsubst %.po,%.mo,$(wildcard *.po))
	# update the po files 
	for f in $(PO_FILES); do \
		intltool-update -r $${f%.po}  -g language-selector ; \
	done

language-selector.pot:
	intltool-update -p -g language-selector

%.mo : %.po
	mkdir -p mo/$(subst .po,,$<)/LC_MESSAGES/ 
	msgfmt $< -o mo/$(subst .po,,$<)/LC_MESSAGES/language-selector.mo 
