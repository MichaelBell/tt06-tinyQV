.PHONY: all

%-results.xml:
	make -f test_$*.mk clean
	make -f test_$*.mk
	mv results.xml $@

all: clean basic-results.xml prog-results.xml
	cat *results.xml > results.xml

clean:
	rm *results.xml || true