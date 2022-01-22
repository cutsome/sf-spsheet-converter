.PHONY: init
init:
	@python -m venv ./.venv
	@source ./.venv/bin/activate
	@pip install --upgrade pip
	@pip install -r ./requirements.txt


.PHONY: deploy
deploy:
	@./deploy.sh
