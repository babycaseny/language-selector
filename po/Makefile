
top_srcdir = ..

PO_FILES := $(wildcard *.po)

default: language-selector.pot $(patsubst %.po,%.mo,$(wildcard *.po))

update-po: language-selector.pot
	# update the po files 
	#for f in $(PO_FILES); do \
	#	intltool-update -r $${f%.po}  -g language-selector ; \
	#done
	intltool-update -r $${f%.po}  -g language-selector ; \

language-selector.pot:
	intltool-extract --type=gettext/rfc822deb  ../data/incomplete-language-support-gnome.note.in
	intltool-extract --type=gettext/rfc822deb  ../data/incomplete-language-support-qt.note.in
	intltool-extract --type=gettext/rfc822deb  ../data/restart_session_required.note.in
	intltool-update -p -g language-selector
	

%.mo : %.po
	mkdir -p mo/$(subst .po,,$<)/LC_MESSAGES/ 
	msgfmt $< -o mo/$(subst .po,,$<)/LC_MESSAGES/language-selector.mo 
