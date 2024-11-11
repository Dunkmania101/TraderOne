deps:
	./scripts/deps.sh

init:
	test -d .venv || python3 -m venv .venv
	make deps

