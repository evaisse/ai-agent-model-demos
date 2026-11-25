.PHONY: add-prompt wizard test index check docker-build serve models

wizard:
	python3 demo.py wizard

test:
	python3 -m unittest discover -s tests

index:
	python3 demo.py index

check:
	python3 demo.py check-export

docker-build:
	python3 demo.py docker-build

serve:
	python3 demo.py serve

models:
	python3 demo.py models

add-prompt:
	python3 demo.py add-prompt
