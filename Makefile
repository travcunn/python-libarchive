build:
	make -C libarchive

test:
	python tests.py

verify:
	pyflakes libarchive
	pep8 --exclude=migrations --ignore=E501,E225 libarchive

install:
	python setup.py install

publish:
	python setup.py register
	python setup.py sdist upload

clean:
	make -C libarchive clean
